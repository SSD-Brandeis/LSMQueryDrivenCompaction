// This file contain implementation for range query driven flush and compactions
// It would be quite similar to db_impl_compaction_flush.cc

#include <fstream>
#include <iomanip>
#include <iostream>

#include "db/builder.h"
#include "db/compaction/compaction_outputs.h"
#include "db/db_impl/db_impl.h"
#include "file/read_write_util.h"
#include "logging/logging.h"
#include "monitoring/iostats_context_imp.h"
#include "monitoring/thread_status_util.h"
#include "table/sst_file_dumper.h"

namespace ROCKSDB_NAMESPACE {

Status DBImpl::FlushPartialOrRangeFile(
    ColumnFamilyData* cfd, const MutableCFOptions& mutable_cf_options,
    bool* made_progress, JobContext* job_context, FlushReason flush_reason,
    SuperVersionContext* superversion_context,
    std::vector<SequenceNumber>& snapshot_seqs,
    SequenceNumber earliest_write_conflict_snapshot,
    SnapshotChecker* snapshot_checker, LogBuffer* log_buffer,
    Env::Priority thread_pri, MemTable* memtable, int level,
    FileMetaData* meta_data) {
  mutex_.AssertHeld();
  assert(cfd);
  assert(flush_reason == FlushReason::kRangeFlush ||
         flush_reason == FlushReason::kPartialFlush);
  assert(level > 0);

  // Only works for single column family
  uint64_t max_memtable_id = std::numeric_limits<uint64_t>::max();

  if (immutable_db_options().verbosity > 0) {
    std::cout << "\n[Verbosity]: creating partial_flush_job for job_id: "
              << job_context->job_id
              << " flush_reason: " << GetFlushReasonString(flush_reason)
              << " level: " << level << " " << __FILE__ ":" << __LINE__ << " "
              << __FUNCTION__ << std::endl;
    if (flush_reason == FlushReason::kPartialFlush) {
      std::cout << "file_number: " << meta_data->fd.GetNumber()
                << " smallest_key: " << meta_data->smallest.user_key().data()
                << " largest_key: " << meta_data->largest.user_key().data()
                << " " << __FILE__ ":" << __LINE__ << " " << __FUNCTION__
                << std::endl;
    } else {
      std::cout << "memtable_id: " << memtable->GetID()
                << " num_entries: " << memtable->num_entries() << " "
                << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
    }
  }

  PartialOrRangeFlushJob flush_job(
      dbname_, cfd, immutable_db_options_, mutable_cf_options, max_memtable_id,
      file_options_for_compaction_, versions_.get(), &mutex_, &shutting_down_,
      snapshot_seqs, earliest_write_conflict_snapshot, snapshot_checker,
      job_context, flush_reason, log_buffer, directories_.GetDbDir(),
      GetDataDir(cfd, 0U),
      GetCompressionFlush(*cfd->ioptions(), mutable_cf_options), stats_,
      &event_logger_, mutable_cf_options.report_bg_io_stats,
      true /* sync_output_directory */,
      false /* write_manifest */,  // TODO: (shubham) Think more on
                                   // write_manifest
      thread_pri, io_tracer_, seqno_time_mapping_, read_options_, db_id_,
      db_session_id_, cfd->GetFullHistoryTsLow(), &blob_callback_, memtable,
      level, meta_data);
  FileMetaData file_meta;

  Status s = Status::OK();

  flush_job.InitNewTable();

  NotifyOnFlushBegin(cfd, &file_meta, mutable_cf_options, job_context->job_id,
                     flush_reason);

  bool switched_to_mempurge = false;
  ++bg_partial_or_range_flush_running_;
  s = flush_job.Run(&logs_with_prep_tracker_, &file_meta,
                    &switched_to_mempurge);

  if (immutable_db_options().verbosity > 0) {
    std::cout << "\n[Verbosity]: ran partial_flush_job for job_id: "
              << job_context->job_id
              << " flush_reason: " << GetFlushReasonString(flush_reason)
              << " level: " << level << " status: " << s.ToString() << " "
              << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
  }

  if (s.ok()) {
    // TODO: (shubham) Instead collect all edits and install it once in end of
    // range query
    Status ios = versions_->LogAndApply(cfd, *cfd->GetLatestMutableCFOptions(),
                                        read_options_, flush_job.GetJobEdits(),
                                        &mutex_, directories_.GetDbDir());
    if (immutable_db_options().verbosity > 0) {
      std::cout
          << "\n[Verbosity]: logged and applied partial_flush_job for job_id: "
          << job_context->job_id
          << " flush_reason: " << GetFlushReasonString(flush_reason)
          << " level: " << level << " status: " << ios.ToString() << " "
          << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
      if (flush_reason == FlushReason::kPartialFlush) {
        std::cout << "file_number: " << meta_data->fd.GetNumber()
                  << " smallest_key: " << meta_data->smallest.user_key().data()
                  << " largest_key: " << meta_data->largest.user_key().data()
                  << " " << __FILE__ ":" << __LINE__ << " " << __FUNCTION__
                  << std::endl;
      } else {
        std::cout << "memtable_id: " << memtable->GetID()
                  << " num_entries: " << memtable->num_entries() << " "
                  << __FILE__ ":" << __LINE__ << " " << __FUNCTION__
                  << std::endl;
      }
    }
    InstallSuperVersionAndScheduleWork(cfd, superversion_context,
                                       mutable_cf_options);
    if (immutable_db_options().verbosity > 0) {
      std::cout << "\n[Verbosity]: installed super version for job_id: "
                << job_context->job_id
                << " flush_reason: " << GetFlushReasonString(flush_reason)
                << " level: " << level << " status: " << ios.ToString() << " "
                << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
    }
    if (made_progress) {
      *made_progress = true;
    }

    const std::string& column_family_name = cfd->GetName();

    Version* const current = cfd->current();
    assert(current);

    const VersionStorageInfo* const storage_info = current->storage_info();
    assert(storage_info);

    VersionStorageInfo::LevelSummaryStorage tmp;
    ROCKS_LOG_BUFFER(log_buffer, "[%s] Level summary: %s\n",
                     column_family_name.c_str(),
                     storage_info->LevelSummary(&tmp));

    const auto& blob_files = storage_info->GetBlobFiles();
    if (!blob_files.empty()) {
      assert(blob_files.front());
      assert(blob_files.back());

      ROCKS_LOG_BUFFER(
          log_buffer,
          "[%s] Blob file summary: head=%" PRIu64 ", tail=%" PRIu64 "\n",
          column_family_name.c_str(), blob_files.front()->GetBlobFileNumber(),
          blob_files.back()->GetBlobFileNumber());
    }
  }

  if (!s.ok() && !s.IsShutdownInProgress() && !s.IsColumnFamilyDropped()) {
    Status new_bg_error = s;
    error_handler_.SetBGError(new_bg_error, BackgroundErrorReason::kFlush);
  }

  // If flush ran smoothly and no mempurge happened
  // install new SST file path.
  if (s.ok() && (!switched_to_mempurge)) {
    // may temporarily unlock and lock the mutex.
    NotifyOnFlushCompleted(cfd, mutable_cf_options,
                           flush_job.GetCommittedFlushJobsInfo());
    auto sfm = static_cast<SstFileManagerImpl*>(
        immutable_db_options_.sst_file_manager.get());
    if (sfm) {
      // Notify sst_file_manager that a new file was added
      std::string file_path = MakeTableFileName(
          cfd->ioptions()->cf_paths[0].path, file_meta.fd.GetNumber());
      // TODO (PR7798).  We should only add the file to the FileManager if it
      // exists. Otherwise, some tests may fail.  Ignore the error in the
      // interim.
      sfm->OnAddFile(file_path).PermitUncheckedError();
      if (sfm->IsMaxAllowedSpaceReached()) {
        Status new_bg_error =
            Status::SpaceLimit("Max allowed space was reached");
        error_handler_.SetBGError(new_bg_error, BackgroundErrorReason::kFlush);
      }
    }
  }
  --bg_partial_or_range_flush_running_;
  return s;
}

Status DBImpl::FlushPartialOrRangeFiles(
    const autovector<BGFlushArg>& bg_flush_args, bool* made_progress,
    JobContext* job_context, LogBuffer* log_buffer, Env::Priority thread_pri) {
  assert(bg_flush_args.size() == 1);
  std::vector<SequenceNumber> snapshot_seqs;
  SequenceNumber earliest_write_conflict_snapshot;
  SnapshotChecker* snapshot_checker;
  GetSnapshotContext(job_context, &snapshot_seqs,
                     &earliest_write_conflict_snapshot, &snapshot_checker);
  const auto& bg_flush_arg = bg_flush_args[0];
  ColumnFamilyData* cfd = bg_flush_arg.cfd_;
  // intentional infrequent copy for each flush
  MutableCFOptions mutable_cf_options_copy = *cfd->GetLatestMutableCFOptions();
  SuperVersionContext* superversion_context =
      bg_flush_arg.superversion_context_;
  FlushReason flush_reason = bg_flush_arg.flush_reason_;
  MemTable* memtable_to_flush = bg_flush_arg.memtable_;
  int level = bg_flush_arg.level_;
  FileMetaData* file_meta = bg_flush_arg.meta_data_;

  Status s = FlushPartialOrRangeFile(
      cfd, mutable_cf_options_copy, made_progress, job_context, flush_reason,
      superversion_context, snapshot_seqs, earliest_write_conflict_snapshot,
      snapshot_checker, log_buffer, thread_pri, memtable_to_flush, level,
      file_meta);
  return s;
}

Status DBImpl::BackgroundPartialOrRangeFlush(bool* made_progress,
                                             JobContext* job_context,
                                             LogBuffer* log_buffer,
                                             FlushReason* reason,
                                             Env::Priority thread_pri) {
  mutex_.AssertHeld();

  Status status;
  *reason = FlushReason::kOthers;
  // If BG work is stopped due to an error, but a recovery is in progress,
  // that means this flush is part of the recovery. So allow it to go through
  if (!error_handler_.IsBGWorkStopped()) {
    if (shutting_down_.load(std::memory_order_acquire)) {
      status = Status::ShutdownInProgress();
    }
  } else if (!error_handler_.IsRecoveryInProgress()) {
    status = error_handler_.GetBGError();
  }

  if (!status.ok()) {
    return status;
  }

  autovector<BGFlushArg> bg_flush_args;
  std::vector<SuperVersionContext>& superversion_contexts =
      job_context->superversion_contexts;
  autovector<ColumnFamilyData*> column_families_not_to_flush;
  autovector<FlushRequest> to_be_pushed_back;
  while (!flush_queue_.empty()) {
    const FlushRequest& flush_req = PopFirstFromFlushQueue();
    FlushReason flush_reason = flush_req.flush_reason;
    MemTable* memtable = flush_req.mem_to_flush;
    int level = flush_req.level;
    bool just_delete = flush_req.just_delete;
    FileMetaData* file_meta = flush_req.meta_data;

    if (flush_reason != FlushReason::kPartialFlush &&
        flush_reason != FlushReason::kRangeFlush) {
      to_be_pushed_back.push_back(flush_req);
      continue;
    }

    if (flush_reason == FlushReason::kRangeFlush) {
      level = range_query_last_level_;
    }

    if (immutable_db_options().verbosity > 0) {
      std::cout << "\n[Verbosity]: running job_id: " << job_context->job_id
                << " flush_reason: " << GetFlushReasonString(flush_reason)
                << " level: " << level
                << " just_delete: " << (just_delete ? "True " : "False ")
                << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
      if (flush_reason == FlushReason::kPartialFlush) {
        std::cout << "file_number: " << file_meta->fd.GetNumber()
                  << " smallest_key: " << file_meta->smallest.user_key().data()
                  << " largest_key: " << file_meta->largest.user_key().data()
                  << " " << __FILE__ ":" << __LINE__ << " " << __FUNCTION__
                  << std::endl;
      } else {
        std::cout << "memtable_id: " << memtable->GetID()
                  << " num_entries: " << memtable->num_entries() << " "
                  << __FILE__ ":" << __LINE__ << " " << __FUNCTION__
                  << std::endl;
      }
    }

    superversion_contexts.clear();
    superversion_contexts.reserve(
        flush_req.cfd_to_max_mem_id_to_persist.size());

    for (const auto& iter : flush_req.cfd_to_max_mem_id_to_persist) {
      ColumnFamilyData* cfd = iter.first;
      // TODO: (shubham) Not sure what mempurged is used for

      // if reason is kPartialFlush and just_delete is true
      // add this file to the edits Delete and we are done!
      if (flush_reason == FlushReason::kPartialFlush && just_delete) {
        assert(file_meta != nullptr);
        VersionEdit* edit_ = new VersionEdit();
        // const MutableCFOptions& mutable_cf_options =
        // *cfd->GetLatestMutableCFOptions();;
        edit_->SetPrevLogNumber(0);
        edit_->SetLogNumber(0);
        edit_->SetColumnFamily(cfd->GetID());
        uint64_t file_number = file_meta->fd.GetNumber();
        edit_->DeleteFile(level, file_number);
        Status ios = versions_->LogAndApply(
            cfd, *cfd->GetLatestMutableCFOptions(), read_options_, edit_,
            &mutex_, directories_.GetDbDir());

        if (immutable_db_options().verbosity > 0) {
          std::cout << "\n[Verbosity]: file deleted, "
                    << " flush_reason: " << GetFlushReasonString(flush_reason)
                    << " level: " << level
                    << " just_delete: " << (just_delete ? "True " : "False ")
                    << " file_number: " << file_meta->fd.GetNumber()
                    << " smallest_key: "
                    << file_meta->smallest.user_key().data()
                    << " largest_key: " << file_meta->largest.user_key().data()
                    << ", finished"
                    << " LogAndApply status: " << ios.ToString() << " "
                    << __FILE__ ":" << __LINE__ << " " << __FUNCTION__
                    << std::endl;
          std::cout << "Will use same job_id: " << job_context->job_id
                    << " for next work" << std::endl;
        }
        flush_queue_.size() > 1 ? --unscheduled_partial_or_range_flushes_
                                : unscheduled_partial_or_range_flushes_;
        // InstallSuperVersionAndScheduleWork(cfd,
        // &(superversion_contexts.back()),
        //                                    mutable_cf_options);
        break;
      }

      if (cfd->IsDropped()) {
        column_families_not_to_flush.push_back(cfd);
        continue;
      }
      superversion_contexts.emplace_back(SuperVersionContext(true));
      bg_flush_args.emplace_back(cfd, iter.second,
                                 &(superversion_contexts.back()), flush_reason,
                                 memtable, level, just_delete, file_meta);
    }
    if (!bg_flush_args.empty()) {
      break;
    }
  }

  // Add other flush request back to queue
  while (to_be_pushed_back.size() > 0) {
    flush_queue_.push_back(to_be_pushed_back.back());
    to_be_pushed_back.pop_back();
    ;
  }

  if (!bg_flush_args.empty()) {
    auto bg_job_limits = GetBGJobLimits();
    for (const auto& arg : bg_flush_args) {
      ColumnFamilyData* cfd = arg.cfd_;
      ROCKS_LOG_BUFFER(
          log_buffer,
          "Calling FlushPartialOrRangeFiles with column "
          "family [%s], flush slots available %d, compaction slots available "
          "%d, "
          "flush slots scheduled %d, compaction slots scheduled %d",
          cfd->GetName().c_str(), bg_job_limits.max_flushes,
          bg_job_limits.max_compactions, bg_flush_scheduled_,
          bg_compaction_scheduled_);
    }
    status = FlushPartialOrRangeFiles(bg_flush_args, made_progress, job_context,
                                      log_buffer, thread_pri);
    *reason = bg_flush_args[0].flush_reason_;
    for (auto& arg : bg_flush_args) {
      ColumnFamilyData* cfd = arg.cfd_;
      if (cfd->UnrefAndTryDelete()) {
        arg.cfd_ = nullptr;
      }
    }
  }
  for (auto cfd : column_families_not_to_flush) {
    cfd->UnrefAndTryDelete();
  }
  return status;
}

void DBImpl::BackgroundCallPartialOrRangeFlush(Env::Priority thread_pri) {
  bool made_progress = false;
  JobContext job_context(next_job_id_.fetch_add(1), true);

  LogBuffer log_buffer(InfoLogLevel::INFO_LEVEL,
                       immutable_db_options_.info_log.get());
  {
    InstrumentedMutexLock l(&mutex_);
    assert(bg_partial_or_range_flush_scheduled_);
    num_running_flushes_++;

    std::unique_ptr<std::list<uint64_t>::iterator>
        pending_outputs_inserted_elem(new std::list<uint64_t>::iterator(
            CaptureCurrentFileNumberInPendingOutputs()));
    FlushReason reason;

    Status s = BackgroundPartialOrRangeFlush(&made_progress, &job_context,
                                             &log_buffer, &reason, thread_pri);

    // (shubham) below code is similar to BackgroundCallFlush
    if (!s.ok() && !s.IsShutdownInProgress() && !s.IsColumnFamilyDropped() &&
        reason != FlushReason::kErrorRecovery) {
      // Wait a little bit before retrying background flush in
      // case this is an environmental problem and we do not want to
      // chew up resources for failed flushes for the duration of
      // the problem.
      uint64_t error_cnt =
          default_cf_internal_stats_->BumpAndGetBackgroundErrorCount();
      bg_cv_.SignalAll();  // In case a waiter can proceed despite the error
      mutex_.Unlock();
      ROCKS_LOG_ERROR(immutable_db_options_.info_log,
                      "Waiting after background flush error: %s"
                      "Accumulated background error counts: %" PRIu64,
                      s.ToString().c_str(), error_cnt);
      log_buffer.FlushBufferToLog();
      LogFlush(immutable_db_options_.info_log);
      immutable_db_options_.clock->SleepForMicroseconds(1000000);
      mutex_.Lock();
    }

    TEST_SYNC_POINT("DBImpl::BackgroundCallFlush:FlushFinish:0");
    ReleaseFileNumberFromPendingOutputs(pending_outputs_inserted_elem);

    // If flush failed, we want to delete all temporary files that we might have
    // created. Thus, we force full scan in FindObsoleteFiles()
    FindObsoleteFiles(&job_context, !s.ok() && !s.IsShutdownInProgress() &&
                                        !s.IsColumnFamilyDropped());
    // delete unnecessary files if any, this is done outside the mutex
    if (job_context.HaveSomethingToClean() ||
        job_context.HaveSomethingToDelete() || !log_buffer.IsEmpty()) {
      mutex_.Unlock();
      TEST_SYNC_POINT("DBImpl::BackgroundCallFlush:FilesFound");
      // Have to flush the info logs before bg_flush_scheduled_--
      // because if bg_flush_scheduled_ becomes 0 and the lock is
      // released, the deconstructor of DB can kick in and destroy all the
      // states of DB so info_log might not be available after that point.
      // It also applies to access other states that DB owns.
      log_buffer.FlushBufferToLog();
      if (job_context.HaveSomethingToDelete()) {
        PurgeObsoleteFiles(job_context);
      }
      job_context.Clean();
      mutex_.Lock();
    }
    TEST_SYNC_POINT("DBImpl::BackgroundCallFlush:ContextCleanedUp");

    assert(num_running_flushes_ > 0);
    num_running_flushes_--;
    bg_partial_or_range_flush_scheduled_--;
    // See if there's more work to be done
    SchedulePartialOrRangeFileFlush();
    atomic_flush_install_cv_.SignalAll();
    bg_cv_.SignalAll();
    // IMPORTANT: there should be no code after calling SignalAll. This call may
    // signal the DB destructor that it's OK to proceed with destruction. In
    // that case, all DB variables will be dealloacated and referencing them
    // will cause trouble.
  }
}

void DBImpl::BGWorkPartialOrRangeFlush(void* args) {
  FlushThreadArg fta = *(reinterpret_cast<FlushThreadArg*>(args));
  delete reinterpret_cast<FlushThreadArg*>(args);

  IOSTATS_SET_THREAD_POOL_ID(fta.thread_pri_);
  static_cast_with_check<DBImpl>(fta.db_)->BackgroundCallPartialOrRangeFlush(
      fta.thread_pri_);
}

void DBImpl::SchedulePartialOrRangeFileFlush() {
  mutex_.AssertHeld();
  if (!opened_successfully_) {
    // partial flush should not happen when
    // DB is not opened successfully
    return;
  } else if (shutting_down_.load(std::memory_order_acquire)) {
    // DB is being deleted; no more partial/Range flushes
    return;
  }
  // background work should not run during partial or range file flush
  assert(bg_work_paused_ > 0);
  assert(bg_compaction_paused_ > 0);

  auto bg_job_limits = GetBGJobLimits();

  if (immutable_db_options().verbosity > 0) {
    std::cout << "\n[Verbosity]: trying to schedule, current - scheduled: "
              << bg_partial_or_range_flush_scheduled_
              << " running: " << bg_partial_or_range_flush_running_
              << " unscheduled: " << unscheduled_partial_or_range_flushes_
              << " max_bg_job_limit: " << bg_job_limits.max_flushes << " "
              << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
  }

  while (unscheduled_partial_or_range_flushes_ > 0 &&
         bg_partial_or_range_flush_scheduled_ < bg_job_limits.max_flushes) {
    bg_partial_or_range_flush_scheduled_++;
    FlushThreadArg* fta = new FlushThreadArg;
    fta->db_ = this;
    fta->thread_pri_ =
        Env::Priority::HIGH;  // schedule everything on high priority thread

    if (immutable_db_options().verbosity > 0) {
      std::cout << "\n[Verbosity]: scheduling more, now - scheduled: "
                << bg_partial_or_range_flush_scheduled_
                << " running: " << bg_partial_or_range_flush_running_
                << " unscheduled: " << unscheduled_partial_or_range_flushes_
                << " max_bg_job_limit: " << bg_job_limits.max_flushes << " "
                << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
    }

    env_->Schedule(&DBImpl::BGWorkPartialOrRangeFlush, fta, Env::Priority::HIGH,
                   this, &DBImpl::UnschedulePartialOrRangeFlushCallback);

    if (immutable_db_options().verbosity > 0) {
      std::cout << "\n[Verbosity]: scheduling more, now - scheduled: "
                << bg_partial_or_range_flush_scheduled_
                << " running: " << bg_partial_or_range_flush_running_
                << " unscheduled: " << unscheduled_partial_or_range_flushes_
                << " max_bg_job_limit: " << bg_job_limits.max_flushes << " "
                << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
    }

    env_->Schedule(&DBImpl::BGWorkPartialOrRangeFlush, fta, Env::Priority::HIGH,
                   this, &DBImpl::UnschedulePartialOrRangeFlushCallback);
    --unscheduled_partial_or_range_flushes_;
  }
}

void DBImpl::UnschedulePartialOrRangeFlushCallback(void* arg) {
  // Decrement bg_partial_or_range_flush_scheduled_ in flush callback
  reinterpret_cast<FlushThreadArg*>(arg)
      ->db_->bg_partial_or_range_flush_scheduled_--;
  Env::Priority flush_pri = reinterpret_cast<FlushThreadArg*>(arg)->thread_pri_;
  if (Env::Priority::LOW == flush_pri) {
    TEST_SYNC_POINT("DBImpl::UnscheduleLowFlushCallback");
  } else if (Env::Priority::HIGH == flush_pri) {
    TEST_SYNC_POINT("DBImpl::UnscheduleHighFlushCallback");
  }
  delete reinterpret_cast<FlushThreadArg*>(arg);
  TEST_SYNC_POINT("DBImpl::UnscheduleFlushCallback");
}

void DBImpl::SchedulePendingPartialRangeFlush(const FlushRequest& flush_req) {
  // flush_req should contain reason and map of cfd to max file id if possible
  // the `cfd_to_max_mem_id_to_persist` seems to be not used anywhere
  mutex_.AssertHeld();
  if (flush_req.cfd_to_max_mem_id_to_persist.empty()) {
    return;
  }
  for (auto& iter : flush_req.cfd_to_max_mem_id_to_persist) {
    ColumnFamilyData* cfd = iter.first;
    cfd->Ref();
  }
  ++unscheduled_partial_or_range_flushes_;
  flush_queue_.push_back(flush_req);

  if (immutable_db_options().verbosity > 0) {
    std::cout << "\n[Verbosity]: adding to flush queue, scheduled: "
              << bg_partial_or_range_flush_scheduled_
              << " running: " << bg_partial_or_range_flush_running_
              << " unscheduled: " << unscheduled_partial_or_range_flushes_
              << " " << __FILE__ ":" << __LINE__ << " " << __FUNCTION__
              << std::endl;
  }
}

void DBImpl::AddPartialOrRangeFileFlushRequest(FlushReason flush_reason,
                                               ColumnFamilyData* cfd,
                                               MemTable* mem_range, int level,
                                               bool just_delete,
                                               FileMetaData* file_meta) {
  if (immutable_db_options().verbosity > 0) {
    std::cout << "\n[Verbosity]: creating new flush request reason: "
              << GetFlushReasonString(flush_reason) << " level: " << level
              << " just_delete: " << (just_delete ? "True " : "False ")
              << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
    if (flush_reason == FlushReason::kPartialFlush) {
      std::cout << "file_number: " << file_meta->fd.GetNumber()
                << " smallest_key: " << file_meta->smallest.user_key().data()
                << " largest_key: " << file_meta->largest.user_key().data()
                << " " << __FILE__ ":" << __LINE__ << " " << __FUNCTION__
                << std::endl;
    } else {
      std::cout << "memtable_id: " << mem_range->GetID()
                << " num_entries: " << mem_range->num_entries() << " "
                << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
    }
  }

  if (cfd == nullptr) {
    
    auto cfh =
        static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
    cfd = cfh->cfd();
  }


  FlushRequest req{flush_reason, {{cfd, 0}},  memtable_to_flush,
                   level,        just_delete, file_meta};
  SchedulePendingPartialRangeFlush(req);
  SchedulePartialOrRangeFileFlush();
}

void DBImpl::DumpHumanReadableFormatOfFullLSM(std::string name, ColumnFamilyHandle* column_family) {

  std::ofstream human_readable_file;
  human_readable_file.open(name + ".txt");

  if (!human_readable_file.is_open()) {
      std::cerr << "Error opening the file!" << std::endl;
      exit(1);
  }

  ColumnFamilyData* cfd;
  if (column_family == nullptr) {
    cfd = default_cf_handle_->cfd();
  } else {
    auto cfh = static_cast_with_check<ColumnFamilyHandleImpl>(column_family);
    cfd = cfh->cfd();
  }
  mutex_.Lock();
  SuperVersion* super_version = cfd->GetSuperVersion()->Ref();
  // Arena arena;
  mutex_.Unlock();

  // LEVELS
  auto storage_info_ = super_version->current->storage_info();

  for (int level = 0; level < storage_info_->num_non_empty_levels(); level++) {
    human_readable_file << "Level: " << level << std::endl;
    if (level >= storage_info_->num_non_empty_levels()) {
      human_readable_file << std::endl << std::endl;
      continue;
    } else if (storage_info_->LevelFilesBrief(level).num_files == 0) {
      human_readable_file << std::endl << std::endl;
      continue;
    }
    for (size_t i = 0; i < storage_info_->LevelFilesBrief(level).num_files; i++) {
      const auto& file = storage_info_->LevelFilesBrief(level).files[i];
      human_readable_file << "\tFile[" << file.fd.GetNumber() << "(Smallest Key: " << file.file_metadata->smallest.user_key().ToString()
                          << ", Largest Key: " << file.file_metadata->largest.user_key().ToString() << ")]" << std::endl;
  
      Options op;
      Temperature tmpperature = file.file_metadata->temperature;
      SstFileDumper sst_dump(op, TableFileName(immutable_db_options_.db_paths, file.file_metadata->fd.GetNumber(), 0), tmpperature,
      cfd->GetLatestCFOptions().target_file_size_base, false, false, false);
      sst_dump.DumpTable("db_working_home/DumpOf(Level: " + std::to_string(level) + ") FileNumber: [" + std::to_string(file.file_metadata->fd.GetNumber()) + "]_"+name);
    }
    human_readable_file << std::endl << std::endl;
  }

  human_readable_file.close();
}

// TODO: (shubham)
//  - We may need to add mem_range_ in new_superversion while
//  InstallSuperVersion in ColumnFamily
//  - Remove the start_key and end_key from the BlockBasedIterator and
//  TableReader

}  // namespace ROCKSDB_NAMESPACE
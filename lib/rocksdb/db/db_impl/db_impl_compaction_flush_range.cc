// This file contain implementation for range query driven flush and compactions
// It would be quite similar to db_impl_compaction_flush.cc

#include <fstream>
#include <iostream>
#include <sstream>

#include "db/builder.h"
#include "db/compaction/compaction_outputs.h"
#include "db/db_impl/db_impl.h"
#include "file/read_write_util.h"
#include "logging/logging.h"
#include "monitoring/iostats_context_imp.h"
#include "monitoring/thread_status_util.h"
#include "options/options_helper.h"
#include "table/sst_file_dumper.h"

namespace ROCKSDB_NAMESPACE {

std::string DBImpl::GetLevelsState() {
  std::stringstream all_level_details;
  all_level_details.str("");

  auto cfh =
      static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  auto storage_info = cfd->current()->storage_info();
  for (int l = 0; l < storage_info->num_non_empty_levels(); l++) {
    all_level_details << storage_info->LevelFilesBrief(l).num_files << ",";
  }
  return all_level_details.str();
}

/**
 * (shubham) Deprecated, as it throws errors when accessing VersionStorageInfo.
 * The compactions updates the VersionStorageInfo which is not protected with
 * mutex.
 */
std::tuple<unsigned long long, std::string> DBImpl::GetTreeState() {
  using TypedHandle = TableCache::TypedHandle;

  Status s;
  TableReader* table_reader = nullptr;
  TypedHandle* handle = nullptr;

  auto cfh =
      static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  auto storage_info = cfd->current()->storage_info();

  std::stringstream all_level_details;
  all_level_details.str("");
  unsigned long long total_entries_in_cfd = 0;

  for (int l = 0; l < storage_info->num_non_empty_levels(); l++) {
    std::stringstream level_details;
    level_details.str("");
    auto level_files_brief_ = storage_info->LevelFilesBrief(l);
    // auto num_files = storage_info->LevelFilesBrief(l).num_files;
    unsigned long long level_size_in_bytes = 0;
    level_details << "\tLevel: " << std::to_string(l);

    unsigned long long total_entries_in_one_level = 0;
    std::stringstream level_sst_file_details;

    for (size_t file_index = 0; file_index < level_files_brief_.num_files;
         file_index++) {
      table_reader = nullptr;
      handle = nullptr;
      // auto fd = storage_info->LevelFilesBrief(l).files[file_index];
      auto fd = level_files_brief_.files[file_index];
      auto file_meta = fd.file_metadata;

      table_reader = fd.file_metadata->fd.table_reader;

      if (table_reader == nullptr) {
        auto mutable_cf_options_ = cfd->GetLatestMutableCFOptions();
        auto file_read_hist = cfd->internal_stats()->GetFileReadHist(0);
        auto max_file_size_for_l0_meta_pin_ =
            MaxFileSizeForL0MetaPin(*mutable_cf_options_);
        s = cfd->table_cache()->FindTable(
            read_options_, file_options_, cfd->internal_comparator(),
            *file_meta, &(handle),
            mutable_cf_options_->block_protection_bytes_per_key,
            mutable_cf_options_->prefix_extractor,
            read_options_.read_tier == kBlockCacheTier /* no_io */,
            file_read_hist, false, l, true, max_file_size_for_l0_meta_pin_,
            file_meta->temperature);

        if (s.ok()) {
          table_reader = cfd->table_cache()->get_cache().Value(handle);
        }  // (Shubham) What if table_reader is still null?
      }

      auto tp = table_reader->GetTableProperties();
      total_entries_in_one_level += tp->num_entries;
      level_size_in_bytes += fd.fd.GetFileSize();

      level_sst_file_details
          << "[#" << std::to_string(fd.fd.GetNumber()) << ":"
          << std::to_string(fd.fd.file_size) << " ("
          << fd.file_metadata->smallest.user_key().ToString() << ", "
          << fd.file_metadata->largest.user_key().ToString() << ") "
          << tp->num_entries << "], ";
    }
    total_entries_in_cfd += total_entries_in_one_level;
    level_details << ", Size: " << level_size_in_bytes
                  << " bytes, Files Count: " << level_files_brief_.num_files
                  << ", Entries Count: " << total_entries_in_one_level
                  << "\n\t\t";
    all_level_details << level_details.str() << level_sst_file_details.str()
                      << std::endl;
  }

  return std::make_tuple(total_entries_in_cfd, all_level_details.str());
}

// Find the rough index of the target to find the overlap percentage
long long DBImpl::GetRoughOverlappingEntries(const std::string given_start_key,
                                             const std::string given_end_key,
                                             int level, FileMetaData* file_meta,
                                             ColumnFamilyData* cfd,
                                             Slice& useful_min_key,
                                             Slice& useful_max_key) {
  using TypedHandle = TableCache::TypedHandle;
  long long overlapping_count = 0;

  Status s;
  TableReader* table_reader = file_meta->fd.table_reader;
  TypedHandle* handle = nullptr;

  if (table_reader == nullptr) {
    auto mutable_cf_options_ = cfd->GetLatestMutableCFOptions();
    auto file_read_hist = cfd->internal_stats()->GetFileReadHist(0);
    auto max_file_size_for_l0_meta_pin_ =
        MaxFileSizeForL0MetaPin(*mutable_cf_options_);

    s = cfd->table_cache()->FindTable(
        read_options_, file_options_, cfd->internal_comparator(), *file_meta,
        &(handle), mutable_cf_options_->block_protection_bytes_per_key,
        mutable_cf_options_->prefix_extractor,
        read_options_.read_tier == kBlockCacheTier /* no_io */, file_read_hist,
        false, level, true, max_file_size_for_l0_meta_pin_,
        file_meta->temperature);

    if (s.ok() && handle != nullptr) {
      table_reader = cfd->table_cache()->get_cache().Value(handle);
    }
  }

  // # TODO: Check if this is appropriate
  // If table_reader is still null, return 0
  if (table_reader == nullptr) {
    return 0;
  }

  const ReadOptions read_options;
  auto table_properties = table_reader->GetTableProperties();
  auto num_entries = table_properties->num_entries;
  uint64_t avg_raw_key_size =
      num_entries != 0 ? 1.0 * table_properties->raw_key_size / num_entries
                       : 0.0;
  uint64_t avg_raw_value_size =
      num_entries != 0 ? 1.0 * table_properties->raw_value_size / num_entries
                       : 0.0;

  if (avg_raw_key_size + avg_raw_value_size == 0) {
    return 0;
  }

  SequenceNumber seq = GetLatestSequenceNumber();

  if (!given_start_key.empty() && given_end_key.empty()) {
    //          |-----|
    //    |----------|
    //    |          |
    //    |          |
    //    |----------|

    InternalKey internal_start_key(Slice(given_start_key), seq,
                                   kValueTypeForSeek);
    Slice target = internal_start_key.Encode();
    auto [skip_count, min_key] =
        table_reader->GetNumOfRangeOverlappingEntriesFromFile(read_options,
                                                              target);
    overlapping_count = file_meta->num_entries -
                        (skip_count / (avg_raw_key_size + avg_raw_value_size));
    useful_min_key = min_key;
  } else if (given_start_key.empty() && !given_end_key.empty()) {
    //    |-----|
    //     |----------|
    //     |          |
    //     |          |
    //     |----------|

    InternalKey internal_end_key(Slice(given_end_key), seq, kValueTypeForSeek);
    Slice target = internal_end_key.Encode();
    auto [skip_count, max_key] =
        table_reader->GetNumOfRangeOverlappingEntriesFromFile(read_options,
                                                              target);
    overlapping_count = (skip_count / (avg_raw_key_size + avg_raw_value_size));
    useful_max_key = max_key;
  } else if (!given_start_key.empty() && !given_end_key.empty()) {
    //            |-----|
    //          |----------|
    //          |          |
    //          |          |
    //          |----------|

    InternalKey internal_start_key(Slice(given_start_key), seq,
                                   kValueTypeForSeek);
    InternalKey internal_end_key(Slice(given_end_key), seq, kValueTypeForSeek);
    Slice start = internal_start_key.Encode();
    Slice end = internal_end_key.Encode();
    auto [start_skip, min_key] =
        table_reader->GetNumOfRangeOverlappingEntriesFromFile(read_options,
                                                              start);
    auto [end_skip, max_key] =
        table_reader->GetNumOfRangeOverlappingEntriesFromFile(read_options,
                                                              end);
    overlapping_count =
        ((end_skip - start_skip) / (avg_raw_key_size + avg_raw_value_size));
    useful_min_key = min_key;
    useful_max_key = max_key;
  }

  return overlapping_count;
}

Status DBImpl::FlushPartialOrRangeFile(
    ColumnFamilyData* cfd, const MutableCFOptions& mutable_cf_options,
    bool* made_progress, JobContext* job_context, FlushReason flush_reason,
    SuperVersionContext* superversion_context,
    std::vector<SequenceNumber>& snapshot_seqs,
    SequenceNumber earliest_write_conflict_snapshot,
    SnapshotChecker* snapshot_checker, LogBuffer* log_buffer,
    Env::Priority thread_pri, std::shared_ptr<MemTable> memtable, int level,
    FileMetaData* meta_data) {
  mutex_.AssertHeld();
  assert(cfd);
  assert(flush_reason == FlushReason::kRangeFlush ||
         flush_reason == FlushReason::kPartialFlush);
  assert(level > 0);

  // Only works for single column family
  uint64_t max_memtable_id = std::numeric_limits<uint64_t>::max();

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
      level, meta_data, this);
  FileMetaData file_meta;

  Status s = Status::OK();

  flush_job.InitNewTable();

  NotifyOnFlushBegin(cfd, &file_meta, mutable_cf_options, job_context->job_id,
                     flush_reason);

  bool switched_to_mempurge = false;
  ++bg_partial_or_range_flush_running_;
  s = flush_job.Run(&logs_with_prep_tracker_, &file_meta,
                    &switched_to_mempurge);

  if (s.ok()) {
    // TODO: (shubham) Instead collect all edits and install it once in end of
    // range query
    Status ios = versions_->LogAndApply(cfd, *cfd->GetLatestMutableCFOptions(),
                                        read_options_, flush_job.GetJobEdits(),
                                        &mutex_, directories_.GetDbDir());
    InstallSuperVersionAndScheduleWork(cfd, superversion_context,
                                       mutable_cf_options);
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
    flush_job.SetFlushJobInfo();
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
  std::shared_ptr<MemTable> memtable_to_flush = bg_flush_arg.memtable_;
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
    FlushRequest flush_req = flush_queue_.front();
    flush_queue_.pop_front();
    FlushReason flush_reason = flush_req.flush_reason;
    std::shared_ptr<MemTable> memtable = flush_req.mem_to_flush;
    int level = flush_req.level;
    bool just_delete = flush_req.just_delete;
    FileMetaData* file_meta = flush_req.meta_data;

    if (flush_reason != FlushReason::kPartialFlush &&
        flush_reason != FlushReason::kRangeFlush) {
      to_be_pushed_back.push_back(flush_req);
      continue;
    }

    if (flush_reason == FlushReason::kRangeFlush) {
      // level = range_query_last_level_;
      level = decision_cell_.end_level_;
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
        if (immutable_db_options().verbosity > 1) {
          std::cout << "{\"FileNumber\": " << file_meta->fd.GetNumber()
                    << ", \"Level\": " << level
                    << ", \"ToCompactAccurate\": " << file_meta->num_entries
                    << "}," << std::endl
                    << std::flush;
        }
        assert(file_meta != nullptr);
        VersionEdit* edit_ = new VersionEdit();
        // edit_->SetPrevLogNumber(0);  # (Shubham) This is not required since
        // LogandApply will set it anyway edit_->SetLogNumber(0);
        edit_->SetColumnFamily(cfd->GetID());
        uint64_t file_number = file_meta->fd.GetNumber();
        edit_->DeleteFile(level, file_number);
        Status ios = versions_->LogAndApply(
            cfd, *cfd->GetLatestMutableCFOptions(), read_options_, edit_,
            &mutex_, directories_.GetDbDir());
        flush_queue_.size() > 1 ? --unscheduled_partial_or_range_flushes_
                                : unscheduled_partial_or_range_flushes_;
        // InstallSuperVersionAndScheduleWork(cfd,
        // &(superversion_contexts.back()),
        //                                    mutable_cf_options);
        cfd->UnrefAndTryDelete();
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

    if (unscheduled_partial_or_range_flushes_ == 0 &&
        bg_partial_or_range_flush_running_ == 0 &&
        bg_partial_or_range_flush_scheduled_ == 0) {
      range_queries_complete_cv_.Signal();
    }
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

  while (unscheduled_partial_or_range_flushes_ > 0 &&
         bg_partial_or_range_flush_scheduled_ < bg_job_limits.max_flushes) {
    bg_partial_or_range_flush_scheduled_++;
    FlushThreadArg* fta = new FlushThreadArg;
    fta->db_ = this;
    fta->thread_pri_ =
        Env::Priority::HIGH;  // schedule everything on high priority thread

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
  if (!immutable_db_options_.atomic_flush) {
    assert(flush_req.cfd_to_max_mem_id_to_persist.size() == 1);
    ColumnFamilyData* cfd =
        flush_req.cfd_to_max_mem_id_to_persist.begin()->first;
    assert(cfd);
    cfd->Ref();
    ++unscheduled_partial_or_range_flushes_;
    flush_queue_.push_back(flush_req);
  }
}

void DBImpl::AddPartialOrRangeFileFlushRequest(FlushReason flush_reason,
                                               ColumnFamilyData* cfd,
                                               std::shared_ptr<MemTable> mem_range, int level,
                                               bool just_delete,
                                               FileMetaData* file_meta) {
  // if FlushReason is kPartialFlush then *mem_range must be nullptr
  // if FlushReason is kRangeFlush then *mem_range must be valid pointer
  // just_delete:
  //    - always False for kRangeFlush
  //    - when True for kPartialFlush, it means the file completely overlap with
  //    range
  //    - when False for kPartialFlush, it will write partial file to same level
  // level:
  //    - always -1 for kRangeFlush
  //    - else level on which the file exists for FileMetaData pointer

  if (level != -1 && (level < decision_cell_.start_level_ ||
                      level > decision_cell_.end_level_)) {
    if (flush_reason == FlushReason::kPartialFlush) {
      file_meta->being_compacted = false;
    }
    return;
  }

  if (cfd == nullptr) {
    auto cfh =
        static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
    cfd = cfh->cfd();
  }

  // std::cout << "FlushReason: " << (flush_reason==FlushReason::kRangeFlush ?
  // "RangeFlush" : "PartialFlush") << std::endl << std::flush;

  // switch new range memtable
  if (flush_reason == FlushReason::kRangeFlush) {
    mutex_.Lock();
    cfd->SetMemtableRange(std::shared_ptr<MemTable>(cfd->ConstructNewVectorMemtable(
        *cfd->GetLatestMutableCFOptions(), GetLatestSequenceNumber())));
    mutex_.Unlock();
    if (immutable_db_options().verbosity > 1) {
      std::cout << "{\"MemtableId\": " << mem_range->GetID()
                << ", \"Level\": " << decision_cell_.end_level_
                << ", \"entriesCompacted\": "
                << mem_range->num_entries() << "}," << std::endl
                << std::flush;
    }
  } else {
    if (immutable_db_options().verbosity > 1) {
      std::cout << "{\"FileNumber\": " << file_meta->fd.GetNumber()
                << ", \"Level\": " << level
                << ", \"entriesToCompact\": " << file_meta->num_entries << "},"
                << std::endl
                << std::flush;
    }
  }

  FlushRequest req{flush_reason, {{cfd, 0}},  mem_range,
                   level,        just_delete, file_meta};

  {
    InstrumentedMutexLock l(&mutex_);
    SchedulePendingPartialRangeFlush(req);
    SchedulePartialOrRangeFileFlush();
  }
}

}  // namespace ROCKSDB_NAMESPACE
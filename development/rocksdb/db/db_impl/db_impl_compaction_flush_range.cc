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

void DBImpl::TryAndInstallRangeQueryEdits(ColumnFamilyData* cfd_) {
  const MutableCFOptions* mutable_cf_options =
      cfd_->GetLatestMutableCFOptions();

  {
    InstrumentedMutexLock l(&mutex_);
    autovector<VersionEdit*> edit_list_;
    edit_list_.push_back(range_edit_);

    for (auto deleted_file : range_edit_->GetDeletedFiles()) {
      std::cout << "[Delete File] Level: " << deleted_file.first
                << " File No.: " << deleted_file.second << " " << __FILE__
                << ":" << __LINE__ << __FUNCTION__ << std::endl;
      // MarkAsGrabbedForPurge(deleted_file.second);
    }

    for (auto new_file : range_edit_->GetNewFiles()) {
      std::cout << "[New File] Level: " << new_file.first
                << " File No.: " << new_file.second.fd.GetNumber() << " "
                << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__
                << std::endl;
    }

    // uint64_t min_wal_number_to_keep =
    //     PrecomputeMinLogNumberToKeepNon2PC(GetVersionSet(), {{cfd_}},
    //     {{edit_list_}});

    // VersionEdit wal_deletion;
    // wal_deletion.SetMinLogNumberToKeep(min_wal_number_to_keep);
    // edit_list_.push_back(&wal_deletion);

    // cfd_->current()->version_set()->LogAndApply(
    //     cfd_, *mutable_cf_options, read_options_, edit_list_, &mutex_,
    //     directories_.GetDbDir());
    // InstallSuperVersionAndScheduleWork(cfd_, new SuperVersionContext(false),
    //                                    *mutable_cf_options);
    cfd_->RecalculateWriteStallConditions(*mutable_cf_options);
  }
  delete range_edit_;
}

// void DBImpl::SetRangeQueryRunningToTrue(Slice* start_key, Slice* end_key) {
//   auto cfh =
//       static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
//   ColumnFamilyData* cfd = cfh->cfd();
//   cfd->SetRangeQueryRunningToTrue();

//   range_start_key_ = start_key->data();
//   range_end_key_ = end_key->data();
//   read_options_.range_query_compaction_enabled = true;
//   std::cout << std::endl
//             << std::endl
//             << std::endl
//             << std::endl
//             << std::endl
//             << std::endl;
// }

// void DBImpl::SetRangeQueryRunningToFalse() {
//   auto cfh =
//       static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
//   ColumnFamilyData* cfd = cfh->cfd();

//   std::string levels_state_before = "LSM State Before:";
//   auto storage_info_before = cfd->current()->storage_info();
//   for (int l = 0; l < storage_info_before->num_non_empty_levels(); l++) {
//     levels_state_before +=
//         "\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tLevel-" +
//         std::to_string(l) + ": ";
//     auto num_files = storage_info_before->LevelFilesBrief(l).num_files;
//     for (size_t file_index = 0; file_index < num_files; file_index++) {
//       auto fd = storage_info_before->LevelFilesBrief(l).files[file_index];
//       levels_state_before +=
//           "[" + std::to_string(fd.fd.GetNumber()) + "(" +
//           fd.file_metadata->smallest.user_key().ToString() + ", " +
//           fd.file_metadata->largest.user_key().ToString() + ")" + "] ";
//     }
//   }

//   ROCKS_LOG_INFO(immutable_db_options_.info_log, "%s \n",
//                  levels_state_before.c_str());

//   ApplyRangeQueryEdits();

//   range_start_key_ = "";
//   range_end_key_ = "";
//   read_options_.range_query_compaction_enabled = false;

//   auto cfh_ =
//       static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
//   ColumnFamilyData* cfd_ = cfh_->cfd();
//   cfd_->current()->storage_info()->ComputeCompactionScore(
//       *cfd_->ioptions(), *cfd_->GetLatestMutableCFOptions());
//   MaybeScheduleFlushOrCompaction();
//   cfd_->RecalculateWriteStallConditions(*cfd_->GetLatestMutableCFOptions());

//   std::string levels_state_after = "LSM State After:";
//   auto storage_info_after = cfd_->current()->storage_info();
//   for (int l = 0; l < storage_info_after->num_non_empty_levels(); l++) {
//     levels_state_after +=
//         "\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tLevel-" +
//         std::to_string(l) + ": ";
//     auto num_files = storage_info_after->LevelFilesBrief(l).num_files;
//     for (size_t file_index = 0; file_index < num_files; file_index++) {
//       auto fd = storage_info_after->LevelFilesBrief(l).files[file_index];
//       levels_state_after +=
//           "[" + std::to_string(fd.fd.GetNumber()) + "(" +
//           fd.file_metadata->smallest.user_key().ToString() + ", " +
//           fd.file_metadata->largest.user_key().ToString() + ")" + "] ";
//     }
//   }

//   ROCKS_LOG_INFO(immutable_db_options_.info_log, "%s \n",
//                  levels_state_after.c_str());
//   edits_ = new VersionEdit();
//   cfd_->SetRangeQueryRunningToFalse();
//   cfd_->RecalculateWriteStallConditions(*cfd->GetLatestMutableCFOptions());
//   bg_cv_.SignalAll();
//   mutex()->Unlock();
//   AddToCompactionQueue(cfd_);
//   // range_start_key_here = nullptr;
//   // range_end_key_here = nullptr;
// }

// Status DBImpl::FlushLevelNPartialFile(const LevelFilesBrief* flevel_,
//                                       size_t file_index, int level) {
//   std::cout << "[####] Starting Write Level: " << level
//             << " file_index: " << file_index << " " << __FILE__ << ":"
//             << __LINE__ << " " << __FUNCTION__ << std::endl;
//   std::cout << "[####] File Number : "
//             << flevel_->files[file_index].fd.GetNumber() << " " << __FILE__
//             << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;

//   AutoThreadOperationStageUpdater stage_run(ThreadStatus::STAGE_FLUSH_RUN);
//   ColumnFamilyData* cfd_ =
//       static_cast<ColumnFamilyHandleImpl*>(default_cf_handle_)->cfd();
//   FileMetaData meta_;
//   bool is_bottom_most = false;  // TODO: (shubham) Find this out
//   JobContext job_context(next_job_id_.fetch_add(1), false);
//   LogBuffer log_buffer(InfoLogLevel::INFO_LEVEL,
//                        immutable_db_options_.info_log.get());

//   mutex()->Lock();
//   AutoThreadOperationStageUpdater stage_updater(
//       ThreadStatus::STAGE_FLUSH_WRITE_L0);
//   const uint64_t start_micros = GetSystemClock()->NowMicros();
//   const uint64_t start_cpu_micros = GetSystemClock()->CPUMicros();
//   Env::IOPriority io_priority = Env::IO_HIGH;
//   const MutableCFOptions* mutable_cf_options_ =
//       cfd_->GetLatestMutableCFOptions();

//   ReadOptions ro;
//   Status s;
//   // skipping part of smallest_seqno ... ** NOT SURE WHERE IT IS USED **

//   std::vector<BlobFileAddition> blob_file_additions;

//   {
//     auto write_hint = cfd_->CalculateSSTWriteHint(0);
//     FileMetaData* old_file_meta = flevel_->files[file_index].file_metadata;
//     Arena arena;
//     // RangeDelAggregator* range_del_agg_;
//     TruncatedRangeDelIterator* tombstone_iter = nullptr;

//     mutex()->Unlock();

//     ReadOptions range_read_options = read_options_;
//     range_read_options.iterate_upper_bound = new Slice(range_start_key_);
//     range_read_options.iterate_lower_bound = new Slice(range_end_key_);
//     range_read_options.range_query_compaction_enabled = true;

//     if (cfd_->internal_comparator().user_comparator()->Compare(
//             flevel_->files[file_index].smallest_key, Slice(range_end_key_)) >
//         0) {
//       range_read_options.iterate_lower_bound = nullptr;
//     }

//     InternalIterator* file_iter_ = cfd_->table_cache()->NewIterator(
//         range_read_options, file_options_, cfd_->internal_comparator(),
//         *old_file_meta,
//         /*range_del_agg_=*/nullptr, mutable_cf_options_->prefix_extractor,
//         nullptr, cfd_->internal_stats()->GetFileReadHist(0),
//         TableReaderCaller::kUserIterator, nullptr, /*skip_filters=*/false,
//         /*level=*/0, MaxFileSizeForL0MetaPin(*mutable_cf_options_),
//         /*smallest_compaction_key=*/nullptr,
//         /*largest_compaction_key=*/nullptr, /*allow_unprepared_value=*/true,
//         cfd_->GetLatestMutableCFOptions()->block_protection_bytes_per_key,
//         &tombstone_iter, range_start_key_, range_end_key_);

//     std::vector<InternalIterator*> partial_file_iter;
//     // TODO: (shubham) How to pull only range deletes for before and after
//     range
//     // [<<start, end>>]
//     std::vector<std::unique_ptr<FragmentedRangeTombstoneIterator>>
//         range_del_iters;

//     ro.total_order_seek = true;  // TODO: (shubham) Why ?
//     ro.io_activity = Env::IOActivity::kUnknown;
//     // Arena arena;  // TODO: (shubham) This might not be required

//     partial_file_iter.push_back(file_iter_);

//     ROCKS_LOG_INFO(immutable_db_options_.info_log,
//                    "[%s] [JOB %d] Initiating partial flush for #%" PRIu64
//                    "\n", cfd_->GetName().c_str(), job_context.job_id,
//                    old_file_meta->fd.GetNumber());

//     event_logger_.Log() << "job" << job_context.job_id << "event"
//                         << "partial_flush_started"
//                         << "file_number" << old_file_meta->fd.GetNumber()
//                         << "num_entries" << old_file_meta->num_entries
//                         << "num_deletes" << old_file_meta->num_deletions
//                         << "total_data_size" <<
//                         old_file_meta->fd.GetFileSize()
//                         << "memory_usage"
//                         << old_file_meta->ApproximateMemoryUsage()
//                         << "flush_reason"
//                         << "range_query_compaction";

//     ScopedArenaIterator iter(NewMergingIterator(
//         &cfd_->internal_comparator(), partial_file_iter.data(),
//         static_cast<int>(partial_file_iter.size()), &arena));

//     ROCKS_LOG_INFO(immutable_db_options_.info_log,
//                    "[%s] [JOB %d] Level-%d partial flush file #%" PRIu64
//                    ": started",
//                    cfd_->GetName().c_str(), job_context.job_id, level,
//                    old_file_meta->fd.GetNumber());

//     int64_t _current_time = 0;
//     auto status = GetSystemClock()->GetCurrentTime(&_current_time);

//     if (!status.ok()) {
//       ROCKS_LOG_WARN(
//           immutable_db_options_.info_log,
//           "Failed to get current time to populate creation_time property. "
//           "Status: %s",
//           status.ToString().c_str());
//     }

//     // TODO: (shubham) WARN ROCKSDB FOR FALIED status.ok() while getting
//     current
//     // time

//     const uint64_t current_time = static_cast<uint64_t>(_current_time);
//     uint64_t oldest_key_time = old_file_meta->file_creation_time;
//     uint64_t oldest_ancester_time = std::min(current_time, oldest_key_time);

//     meta_.fd = FileDescriptor(versions_->NewFileNumber(), 0, 0);
//     meta_.epoch_number = cfd_->NewEpochNumber();
//     meta_.oldest_ancester_time = oldest_ancester_time;
//     meta_.file_creation_time = current_time;

//     const std::string* const full_history_ts_low = nullptr;
//     const std::string db_id = db_id_;
//     const std::string db_session_id = db_session_id_;

//     TableBuilderOptions tboptions(
//         *cfd_->ioptions(), *mutable_cf_options_, cfd_->internal_comparator(),
//         cfd_->int_tbl_prop_collector_factories(),
//         GetCompressionFlush(*cfd_->ioptions(), *mutable_cf_options_),
//         cfd_->GetCurrentMutableCFOptions()->compression_opts, cfd_->GetID(),
//         cfd_->GetName(), level, is_bottom_most,
//         TableFileCreationReason::kCompaction, oldest_key_time, current_time,
//         db_id, db_session_id, 0 /* target_file_size */,
//         meta_.fd.GetNumber());

//     uint64_t num_input_entries = 0;
//     uint64_t payload_bytes = 0;
//     uint64_t garbage_bytes = 0;
//     IOStatus io_s;

//     // const std::shared_ptr<IOTracer> io_tracer_;
//     // const SequenceNumber seq_no = 0;  // TODO: (shubham) Find this out
//     const ReadOptions roptions(Env::IOActivity::kCompaction);
//     std::vector<SequenceNumber> snapshot_seqs;
//     SequenceNumber earliest_write_conflict_snapshot_;
//     SnapshotChecker* snapshot_checker;
//     GetSnapshotContext(&job_context, &snapshot_seqs,
//                        &earliest_write_conflict_snapshot_,
//                        &snapshot_checker);
//     const SequenceNumber job_snapshot_seq_ =
//         job_context.GetJobSnapshotSequence();
//     SeqnoToTimeMapping seqno_to_time_mapping_;
//     // EventLogger* event_logger_;
//     TableProperties table_properties_;

//     s = BuildTable(
//         dbname_, GetVersionSet(), immutable_db_options_, tboptions,
//         file_options_, roptions, cfd_->table_cache(), iter.get(),
//         std::move(range_del_iters), &meta_, &blob_file_additions,
//         snapshot_seqs, earliest_write_conflict_snapshot_, job_snapshot_seq_,
//         snapshot_checker,
//         cfd_->GetCurrentMutableCFOptions()->paranoid_file_checks,
//         cfd_->internal_stats(), &io_s, io_tracer_,
//         BlobFileCreationReason::kCompaction, seqno_to_time_mapping_,
//         &event_logger_, job_context.job_id, io_priority, &table_properties_,
//         write_hint, full_history_ts_low, &blob_callback_, cfd_->current(),
//         &num_input_entries, &payload_bytes, &garbage_bytes);

//     // TODO: (shubham) may need verification for number of entries flushed
//     s = io_s;

//     // TODO: (shubham) may need to flush log here
//     ROCKS_LOG_BUFFER(
//         &log_buffer,
//         "[%s] [JOB %d] Level-%d flush new file #%" PRIu64 ": %" PRIu64
//         " bytes %s"
//         "%s",
//         cfd_->GetName().c_str(), job_context.job_id, level,
//         meta_.fd.GetNumber(), meta_.fd.GetFileSize(), s.ToString().c_str(),
//         meta_.marked_for_compaction ? " (needs compaction)" : "");

//     if (s.ok()) {
//       s = GetDataDir(cfd_, 0U)->FsyncWithDirOptions(
//           IOOptions(), nullptr,
//           DirFsyncOptions(DirFsyncOptions::FsyncReason::kNewFileSynced));
//     }
//     mutex()->Unlock();
//   }

//   const bool has_output = meta_.fd.GetFileSize() > 0;
//   log_buffer.FlushBufferToLog();

//   if (s.ok() && has_output) {
//     std::cout << "[####] Adding it to edits  for Level: " << level
//               << " FileNumber: " << meta_.fd.GetNumber() << " " << __FILE__
//               << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
//     edits_->AddFile(level, meta_.fd.GetNumber(), meta_.fd.GetPathId(),
//                     meta_.fd.GetFileSize(), meta_.smallest, meta_.largest,
//                     meta_.fd.smallest_seqno, meta_.fd.largest_seqno,
//                     meta_.marked_for_compaction, meta_.temperature,
//                     meta_.oldest_blob_file_number,
//                     meta_.oldest_ancester_time, meta_.file_creation_time,
//                     meta_.epoch_number, meta_.file_checksum,
//                     meta_.file_checksum_func_name, meta_.unique_id,
//                     meta_.compensated_range_deletion_size, meta_.tail_size,
//                     meta_.user_defined_timestamps_persisted);
//     edits_->SetBlobFileAdditions(std::move(blob_file_additions));

//   } else {
//     return s.Aborted();
//   }

//   InternalStats::CompactionStats stats(CompactionReason::kManualCompaction,
//   1); const uint64_t micros = GetSystemClock()->NowMicros() - start_micros;
//   const uint64_t cpu_micros = GetSystemClock()->CPUMicros() -
//   start_cpu_micros; stats.micros = micros; stats.cpu_micros = cpu_micros;

//   ROCKS_LOG_INFO(immutable_db_options_.info_log,
//                  "[%s] [JOB %d] Flush lasted %" PRIu64
//                  " microseconds, and %" PRIu64 " cpu microseconds.\n",
//                  cfd_->GetName().c_str(), job_context.job_id, micros,
//                  cpu_micros);

//   if (has_output) {
//     stats.bytes_written = meta_.fd.GetFileSize();
//     stats.num_output_files = 1;
//   }

//   const auto& blobs = edits_->GetBlobFileAdditions();
//   for (const auto& blob : blobs) {
//     stats.bytes_written_blob += blob.GetTotalBlobBytes();
//   }

//   stats.num_output_files_blob = static_cast<int>(blobs.size());

//   cfd_->internal_stats()->AddCompactionStats(level, Env::Priority::HIGH,
//   stats); cfd_->internal_stats()->AddCFStats(
//       InternalStats::BYTES_FLUSHED,
//       stats.bytes_written + stats.bytes_written_blob);

//   return s;
//   // TODO: (shubham) might need to update the column family stats here
// }

// Status DBImpl::WriteLevelNFile() {
//   std::cout << "[####] Starting Flush in Range Query at Level: "
//             << range_query_last_level_ << " " << __FILE__ << ":" << __LINE__
//             << " " << __FUNCTION__ << std::endl;

//   AutoThreadOperationStageUpdater stage_run(ThreadStatus::STAGE_FLUSH_RUN);
//   ColumnFamilyData* cfd_ =
//       static_cast<ColumnFamilyHandleImpl*>(default_cf_handle_)->cfd();
//   FileMetaData meta_;
//   meta_.fd = FileDescriptor(versions_->NewFileNumber(), 0, 0);
//   range_query_memtable_->SetFileNumber(meta_.fd.GetNumber());
//   bool is_bottom_most = false;  // TODO: (shubham) Find this out
//   JobContext job_context(next_job_id_.fetch_add(1), false);
//   LogBuffer log_buffer(InfoLogLevel::INFO_LEVEL,
//                        immutable_db_options_.info_log.get());

//   AutoThreadOperationStageUpdater stage_updater(
//       ThreadStatus::STAGE_FLUSH_WRITE_L0);
//   mutex()->Lock();

//   const uint64_t start_micros = GetSystemClock()->NowMicros();
//   const uint64_t start_cpu_micros = GetSystemClock()->CPUMicros();
//   Env::IOPriority io_priority = Env::IO_HIGH;
//   const MutableCFOptions* mutable_cf_options_ =
//       cfd_->GetLatestMutableCFOptions();

//   ReadOptions ro;
//   Status s;
//   // skipping part of smallest_seqno ... ** NOT SURE WHERE IT IS USED **

//   std::vector<BlobFileAddition> blob_file_additions;

//   {
//     auto write_hint = cfd_->CalculateSSTWriteHint(0);

//     mutex()->Unlock();
//     std::vector<InternalIterator*> memtables;
//     std::vector<std::unique_ptr<FragmentedRangeTombstoneIterator>>
//         range_del_iters;
//     ro.total_order_seek = true;
//     ro.io_activity = Env::IOActivity::kCompaction;
//     Arena arena;

//     memtables.push_back(range_query_memtable_->NewIterator(ro, &arena));
//     // // TODO: (shubham) May need to add range deletes

//     ROCKS_LOG_INFO(immutable_db_options_.info_log,
//                    "[%s] [JOB %d] Initiating in-range file flush #%" PRIu64
//                    "\n",
//                    cfd_->GetName().c_str(), job_context.job_id,
//                    range_query_memtable_->GetFileNumber());

//     event_logger_.Log() << "job" << job_context.job_id << "event"
//                         << "in_range_file_flush_started"
//                         << "file_number"
//                         << range_query_memtable_->GetFileNumber()
//                         << "num_entries" <<
//                         range_query_memtable_->num_entries()
//                         << "num_deletes" <<
//                         range_query_memtable_->num_deletes()
//                         << "total_data_size"
//                         << range_query_memtable_->get_data_size()
//                         << "memory_usage"
//                         << range_query_memtable_->ApproximateMemoryUsage()
//                         << "flush_reason"
//                         << "range_query_compaction";

//     ScopedArenaIterator iter(
//         NewMergingIterator(&cfd_->internal_comparator(), memtables.data(),
//                            static_cast<int>(memtables.size()), &arena));

//     ROCKS_LOG_INFO(immutable_db_options_.info_log,
//                    "[%s] [JOB %d] Level-%d in-range file flush #%" PRIu64
//                    ": started",
//                    cfd_->GetName().c_str(), job_context.job_id,
//                    range_query_last_level_, meta_.fd.GetNumber());

//     int64_t _current_time = 0;
//     auto status = GetSystemClock()->GetCurrentTime(&_current_time);

//     if (!status.ok()) {
//       ROCKS_LOG_WARN(
//           immutable_db_options_.info_log,
//           "Failed to get current time to populate creation_time property. "
//           "Status: %s",
//           status.ToString().c_str());
//     }

//     const uint64_t current_time = static_cast<uint64_t>(_current_time);

//     uint64_t oldest_key_time =
//         range_query_memtable_->ApproximateOldestKeyTime();

//     // It's not clear whether oldest_key_time is always available. In case
//     // it is not available, use current_time.
//     uint64_t oldest_ancester_time = std::min(current_time, oldest_key_time);

//     meta_.epoch_number = cfd_->NewEpochNumber();
//     meta_.oldest_ancester_time = oldest_ancester_time;
//     meta_.file_creation_time = current_time;

//     const std::string* const full_history_ts_low = nullptr;
//     const std::string db_id = db_id_;
//     const std::string db_session_id = db_session_id_;

//     TableBuilderOptions tboptions(
//         *cfd_->ioptions(), *mutable_cf_options_, cfd_->internal_comparator(),
//         cfd_->int_tbl_prop_collector_factories(),
//         GetCompressionFlush(*cfd_->ioptions(), *mutable_cf_options_),
//         cfd_->GetCurrentMutableCFOptions()->compression_opts, cfd_->GetID(),
//         cfd_->GetName(), range_query_last_level_, is_bottom_most,
//         TableFileCreationReason::kCompaction, oldest_key_time, current_time,
//         db_id, db_session_id, 0 /* target_file_size */,
//         meta_.fd.GetNumber());

//     uint64_t num_input_entries = 0;
//     uint64_t payload_bytes = 0;
//     uint64_t garbage_bytes = 0;
//     IOStatus io_s;
//     const ReadOptions roptions(Env::IOActivity::kCompaction);
//     std::vector<SequenceNumber> snapshot_seqs;
//     SequenceNumber earliest_write_conflict_snapshot_;
//     SnapshotChecker* snapshot_checker;
//     GetSnapshotContext(&job_context, &snapshot_seqs,
//                        &earliest_write_conflict_snapshot_,
//                        &snapshot_checker);
//     const SequenceNumber job_snapshot_seq_ =
//         job_context.GetJobSnapshotSequence();
//     SeqnoToTimeMapping seqno_to_time_mapping_;
//     TableProperties table_properties_;

//     s = BuildTable(
//         dbname_, GetVersionSet(), immutable_db_options_, tboptions,
//         file_options_, roptions, cfd_->table_cache(), iter.get(),
//         std::move(range_del_iters), &meta_, &blob_file_additions,
//         snapshot_seqs, earliest_write_conflict_snapshot_, job_snapshot_seq_,
//         snapshot_checker,
//         cfd_->GetCurrentMutableCFOptions()->paranoid_file_checks,
//         cfd_->internal_stats(), &io_s, io_tracer_,
//         BlobFileCreationReason::kCompaction, seqno_to_time_mapping_,
//         &event_logger_, job_context.job_id, io_priority, &table_properties_,
//         write_hint, full_history_ts_low, &blob_callback_, cfd_->current(),
//         &num_input_entries, &payload_bytes, &garbage_bytes);

//     // TODO: (shubham) may need verification for number of entries flushed
//     s = io_s;

//     // TODO: (shubham) may need to flush log here

//     ROCKS_LOG_BUFFER(
//         &log_buffer,
//         "[%s] [JOB %d] Level-%d flush new file #%" PRIu64 ": %" PRIu64
//         " bytes %s"
//         "%s",
//         cfd_->GetName().c_str(), job_context.job_id, range_query_last_level_,
//         meta_.fd.GetNumber(), meta_.fd.GetFileSize(), s.ToString().c_str(),
//         meta_.marked_for_compaction ? " (needs compaction)" : "");

//     if (s.ok()) {
//       s = GetDataDir(cfd_, 0U)->FsyncWithDirOptions(
//           IOOptions(), nullptr,
//           DirFsyncOptions(DirFsyncOptions::FsyncReason::kNewFileSynced));
//     }
//     mutex()->Unlock();
//   }
//   // base_->Unref();

//   log_buffer.FlushBufferToLog();
//   const bool has_output = meta_.fd.GetFileSize() > 0;

//   if (s.ok() && has_output) {
//     std::cout << "[####] Adding it to edits  for Level: "
//               << range_query_last_level_
//               << " FileNumber: " << meta_.fd.GetNumber() << " " << __FILE__
//               << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
//     edits_->AddFile(range_query_last_level_, meta_.fd.GetNumber(),
//                     meta_.fd.GetPathId(), meta_.fd.GetFileSize(),
//                     meta_.smallest, meta_.largest, meta_.fd.smallest_seqno,
//                     meta_.fd.largest_seqno, meta_.marked_for_compaction,
//                     meta_.temperature, meta_.oldest_blob_file_number,
//                     meta_.oldest_ancester_time, meta_.file_creation_time,
//                     meta_.epoch_number, meta_.file_checksum,
//                     meta_.file_checksum_func_name, meta_.unique_id,
//                     meta_.compensated_range_deletion_size, meta_.tail_size,
//                     meta_.user_defined_timestamps_persisted);
//     edits_->SetBlobFileAdditions(std::move(blob_file_additions));

//     SequenceNumber seq = versions_->LastSequence();
//     range_query_memtable_ = cfd_->ConstructNewMemtable(
//         cfd_->GetSuperVersion()->mutable_cf_options, seq);

//   } else {
//     return s.Aborted();
//   }

//   InternalStats::CompactionStats stats(CompactionReason::kManualCompaction,
//   1); const uint64_t micros = GetSystemClock()->NowMicros() - start_micros;
//   const uint64_t cpu_micros = GetSystemClock()->CPUMicros() -
//   start_cpu_micros; stats.micros = micros; stats.cpu_micros = cpu_micros;

//   ROCKS_LOG_INFO(immutable_db_options_.info_log,
//                  "[%s] [JOB %d] Flush lasted %" PRIu64
//                  " microseconds, and %" PRIu64 " cpu microseconds.\n",
//                  cfd_->GetName().c_str(), job_context.job_id, micros,
//                  cpu_micros);

//   if (has_output) {
//     stats.bytes_written = meta_.fd.GetFileSize();
//     stats.num_output_files = 1;
//   }

//   const auto& blobs = edits_->GetBlobFileAdditions();
//   for (const auto& blob : blobs) {
//     stats.bytes_written_blob += blob.GetTotalBlobBytes();
//   }

//   stats.num_output_files_blob = static_cast<int>(blobs.size());

//   cfd_->internal_stats()->AddCompactionStats(range_query_last_level_,
//                                              Env::Priority::HIGH, stats);
//   cfd_->internal_stats()->AddCFStats(
//       InternalStats::BYTES_FLUSHED,
//       stats.bytes_written + stats.bytes_written_blob);

//   return s;
//   // TODO: (shubham) might need to update the column family stats here

//   // TODO: (shubham)
//   // Flush the table to level N take reference from
//   Flush_Job::WriteLevel0Table
//   // and FlushLevelNPartialFile Modify the common part from the
//   // FlushLevelNPartialFile and WriteLevelNFile
// }

void DBImpl::DumpHumanReadableFormatOfFullLSM(
    std::string name, ColumnFamilyHandle* column_family) {
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
    for (size_t i = 0; i < storage_info_->LevelFilesBrief(level).num_files;
         i++) {
      const auto& file = storage_info_->LevelFilesBrief(level).files[i];
      human_readable_file << "\tFile[" << file.fd.GetNumber()
                          << "(Smallest Key: "
                          << file.file_metadata->smallest.user_key().ToString()
                          << ", Largest Key: "
                          << file.file_metadata->largest.user_key().ToString()
                          << ")]" << std::endl;

      Options op;
      Temperature tmpperature = file.file_metadata->temperature;
      SstFileDumper sst_dump(
          op,
          TableFileName(immutable_db_options_.db_paths,
                        file.file_metadata->fd.GetNumber(), 0),
          tmpperature, cfd->GetLatestCFOptions().target_file_size_base, false,
          false, false);
      sst_dump.DumpTable(
          "db_working_home/DumpOf(Level: " + std::to_string(level) +
          ") FileNumber: [" +
          std::to_string(file.file_metadata->fd.GetNumber()) + "]_" + name);
    }
    human_readable_file << std::endl << std::endl;
  }

  human_readable_file.close();
}

Status DBImpl::FlushPartialOrRangeFile(
    ColumnFamilyData* cfd, const MutableCFOptions& mutable_cf_options,
    bool* made_progress, JobContext* job_context, FlushReason flush_reason,
    SuperVersionContext* superversion_context,
    std::vector<SequenceNumber>& snapshot_seqs,
    SequenceNumber earliest_write_conflict_snapshot,
    SnapshotChecker* snapshot_checker, LogBuffer* log_buffer,
    Env::Priority thread_pri, MemTable* memtable, size_t file_index, int level,
    uint64_t file_number) {
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
      file_index, level, file_number);
  FileMetaData file_meta;

  Status s = Status::OK();

  flush_job.InitNewTable(range_edit_);

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
    std::cout << "LOGANDAPPLY STATUS: " << ios.ToString() << std::endl;
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
  }

  if (!s.ok() && !s.IsShutdownInProgress() && !s.IsColumnFamilyDropped()) {
    Status new_bg_error = s;
    error_handler_.SetBGError(new_bg_error, BackgroundErrorReason::kFlush);
  }

  // If flush ran smoothly and no mempurge happened
  // install new SST file path.
  if (s.ok() && (!switched_to_mempurge)) {
    // may temporarily unlock and lock the mutex.
    // TODO: (shubham) currently the flush job info is nullptr for
    // PartialOrRangeFlushJob
    // VersionEdit* temp_ = flush_job.GetJobEdits();
    // if (temp_ != nullptr) {
    //   range_edit_list.push_back(std::move(temp_));
    // } else {
    //   std::cout << "Found NULL VersionEdit" << std::endl;
    // }
    // delete temp_;
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
  size_t file_index = bg_flush_arg.file_index_;
  int level = bg_flush_arg.level_;
  uint64_t file_number = bg_flush_arg.file_number_;

  if (flush_reason == FlushReason::kRangeFlush) {
    level = range_query_last_level_;
  }

  Status s = FlushPartialOrRangeFile(
      cfd, mutable_cf_options_copy, made_progress, job_context, flush_reason,
      superversion_context, snapshot_seqs, earliest_write_conflict_snapshot,
      snapshot_checker, log_buffer, thread_pri, memtable_to_flush, file_index,
      level, file_number);
  return s;
}

Status DBImpl::BackgroundPartialOrRangeFlush(bool* made_progress,
                                             JobContext* job_context,
                                             LogBuffer* log_buffer,
                                             FlushReason* reason,
                                             Env::Priority thread_pri) {
  mutex_.AssertHeld();

  Status status;
  *reason = FlushReason::kOthers;  // Why this is updated ?
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
    size_t file_index = flush_req.file_index;
    int level = flush_req.level;
    bool just_delete = flush_req.just_delete;
    uint64_t file_number = flush_req.file_number;

    if (flush_reason != FlushReason::kPartialFlush &&
        flush_reason != FlushReason::kRangeFlush) {
      to_be_pushed_back.push_back(flush_req);
      continue;
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
        VersionEdit* edit_ = new VersionEdit();
        edit_->SetPrevLogNumber(0);
        edit_->SetLogNumber(0);
        edit_->SetColumnFamily(cfd->GetID());
        std::cout << "[File Deleted] Level: " << level
                  << " File No.: " << file_number << " " << __FILE__ << ":"
                  << __LINE__ << " " << __FUNCTION__ << std::endl;
        edit_->DeleteFile(level, file_number);
        versions_->LogAndApply(cfd, *cfd->GetLatestMutableCFOptions(),
                               read_options_, edit_, &mutex_,
                               directories_.GetDbDir());
        continue;
      }

      if (cfd->IsDropped()) {
        column_families_not_to_flush.push_back(cfd);
        continue;
      }
      superversion_contexts.emplace_back(SuperVersionContext(true));
      bg_flush_args.emplace_back(
          cfd, iter.second, &(superversion_contexts.back()), flush_reason,
          memtable, file_index, level, just_delete, file_number);
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
          "Calling FlushMemTableToOutputFile with column "
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
  for (auto& iter : flush_req.cfd_to_max_mem_id_to_persist) {
    ColumnFamilyData* cfd = iter.first;
    cfd->Ref();
  }
  ++unscheduled_partial_or_range_flushes_;
  flush_queue_.push_back(flush_req);
}

void DBImpl::AddPartialOrRangeFileFlushRequest(
    FlushReason flush_reason, ColumnFamilyData* cfd, MemTable* mem_range,
    size_t file_index, int level, bool just_delete, uint64_t file_number) {
  if (cfd == nullptr) {
    auto cfh =
        static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
    cfd = cfh->cfd();
  }

  MemTable* memtable_to_flush = mem_range;

  if (flush_reason == FlushReason::kRangeFlush) {
    mutex_.Lock();
    cfd->SetMemtableRange(cfd->ConstructNewMemtable(
        *cfd->GetLatestMutableCFOptions(), GetLatestSequenceNumber()));
    mutex_.Unlock();
  }

  std::cout << "[Shubham] Creating new flush request " << __FILE__ << ":"
            << __LINE__ << " " << __FUNCTION__ << std::endl;
  FlushRequest req{flush_reason, {{cfd, 0}},  memtable_to_flush, file_index,
                   level,        just_delete, file_number};
  SchedulePendingPartialRangeFlush(req);
  SchedulePartialOrRangeFileFlush();
}

// TODO: (shubham)
//  - We may need to add mem_range_ in new_superversion while
//  InstallSuperVersion in ColumnFamily
//  - Remove the start_key and end_key from the BlockBasedIterator and
//  TableReader

}  // namespace ROCKSDB_NAMESPACE
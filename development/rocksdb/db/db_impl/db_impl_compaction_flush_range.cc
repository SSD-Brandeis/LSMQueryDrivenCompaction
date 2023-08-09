// This file contain implementation for range query driven flush and compactions
// It would be quite similar to db_impl_compaction_flush.cc

#include <iostream>
#include <fstream>
#include <iomanip>

#include "db/builder.h"
#include "db/compaction/compaction_outputs.h"
#include "db/db_impl/db_impl.h"
#include "file/read_write_util.h"
#include "table/sst_file_dumper.h"
#include "logging/logging.h"

namespace ROCKSDB_NAMESPACE {

void DBImpl::ApplyRangeQueryEdits() {
  mutex()->AssertHeld();

  for (auto deleted_file : edits_->GetDeletedFiles()) {
    MarkAsGrabbedForPurge(deleted_file.second);
  }

  auto cfh =
      static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  const ReadOptions read_options;
  const MutableCFOptions& cf_opts = *cfd->GetLatestMutableCFOptions();
  versions_->LogAndApply(cfd, cf_opts, read_options, &(*edits_), mutex(),
                       directories_.GetDbDir());
  SuperVersionContext* sv_context = new SuperVersionContext(true);
  InstallSuperVersionAndScheduleWork(cfd, sv_context, cf_opts);
  mutex()->Unlock();
}

void DBImpl::SetRangeQueryRunningToTrue(Slice* start_key, Slice* end_key) {
  auto cfh =
      static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  cfd->SetRangeQueryRunningToTrue();

  range_start_key_ = start_key->data();
  range_end_key_ = end_key->data();
  read_options_.is_range_query_compaction_enabled = true;
  std::cout << std::endl << std::endl << std::endl << std::endl << std::endl << std::endl;
}

void DBImpl::SetRangeQueryRunningToFalse() {
  auto cfh =
      static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();

  std::string levels_state_before = "LSM State Before:";
  auto storage_info_before = cfd->current()->storage_info();
  for (int l = 0; l < storage_info_before->num_non_empty_levels(); l++) {
    levels_state_before += "\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tLevel-" + std::to_string(l) + ": ";
    auto num_files = storage_info_before->LevelFilesBrief(l).num_files;
    for (size_t file_index = 0; file_index < num_files; file_index++) {
      auto fd = storage_info_before->LevelFilesBrief(l).files[file_index];
      levels_state_before += "[" + std::to_string(fd.fd.GetNumber()) + "(" + fd.file_metadata->smallest.user_key().ToString() + ", " + fd.file_metadata->largest.user_key().ToString() + ")" + "] ";
    }
  }

  ROCKS_LOG_INFO(immutable_db_options_.info_log, "%s \n", levels_state_before.c_str());

  ApplyRangeQueryEdits();

  cfd->SetRangeQueryRunningToFalse();
  range_start_key_ = "";
  range_end_key_ = "";
  read_options_.is_range_query_compaction_enabled = false;
  cfd->current()->storage_info()->ComputeCompactionScore(*cfd->ioptions(), *cfd->GetLatestMutableCFOptions());
  cfd->RecalculateWriteStallConditions(*cfd->GetLatestMutableCFOptions());

  std::string levels_state_after = "LSM State After:";
  auto storage_info_after = cfd->current()->storage_info();
  for (int l = 0; l < storage_info_after->num_non_empty_levels(); l++) {
    levels_state_after += "\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tLevel-" + std::to_string(l) + ": ";
    auto num_files = storage_info_after->LevelFilesBrief(l).num_files;
    for (size_t file_index = 0; file_index < num_files; file_index++) {
      auto fd = storage_info_after->LevelFilesBrief(l).files[file_index];
      levels_state_after += "[" + std::to_string(fd.fd.GetNumber()) + "(" + fd.file_metadata->smallest.user_key().ToString() + ", " + fd.file_metadata->largest.user_key().ToString() + ")" + "] ";
    }
  }

  ROCKS_LOG_INFO(immutable_db_options_.info_log, "%s \n", levels_state_after.c_str());
  // range_start_key_here = nullptr;
  // range_end_key_here = nullptr;
}

Status DBImpl::FlushLevelNPartialFile(const LevelFilesBrief* flevel_, size_t file_index, int level) {
  std::cout << "[####] Starting Write Level: " << level << " file_index: " << file_index << " " << __FILE__ << ":"
            << __LINE__ << " " << __FUNCTION__ << std::endl;
  std::cout << "[####] File Number : " << flevel_->files[file_index].fd.GetNumber() << " " << __FILE__ << ":"
            << __LINE__ << " " << __FUNCTION__ << std::endl;

  ColumnFamilyData* cfd_ =
      static_cast<ColumnFamilyHandleImpl*>(default_cf_handle_)->cfd();
  FileMetaData meta_;
  bool is_bottom_most = false;  // TODO: (shubham) Find this out
  JobContext job_context(next_job_id_.fetch_add(1), false);
  LogBuffer log_buffer(InfoLogLevel::INFO_LEVEL,
                       immutable_db_options_.info_log.get());

  mutex()->Lock();

  const uint64_t start_micros = GetSystemClock()->NowMicros();
  const uint64_t start_cpu_micros = GetSystemClock()->CPUMicros();
  Env::IOPriority io_priority = Env::IO_HIGH;
  const MutableCFOptions* mutable_cf_options_ =
      cfd_->GetLatestMutableCFOptions();
  
  ReadOptions ro;
  Status s;
  // skipping part of smallest_seqno ... ** NOT SURE WHERE IT IS USED **

  std::vector<BlobFileAddition> blob_file_additions;

  {
    auto write_hint = cfd_->CalculateSSTWriteHint(0);
    FileMetaData* old_file_meta = flevel_->files[file_index].file_metadata;
    Arena arena;
    // RangeDelAggregator* range_del_agg_;
    TruncatedRangeDelIterator* tombstone_iter = nullptr;

    mutex()->Unlock();

    ReadOptions range_read_options = read_options_;
    range_read_options.iterate_upper_bound = new Slice(range_start_key_);
    range_read_options.iterate_lower_bound = new Slice(range_end_key_);
    range_read_options.is_range_query_compaction_enabled = true;

    InternalIterator* file_iter_ = cfd_->table_cache()->NewIterator(
        range_read_options, file_options_, cfd_->internal_comparator(), *old_file_meta,
        /*range_del_agg_=*/nullptr, mutable_cf_options_->prefix_extractor, nullptr,
        cfd_->internal_stats()->GetFileReadHist(0),
        TableReaderCaller::kUserIterator, nullptr, /*skip_filters=*/false,
        /*level=*/0, MaxFileSizeForL0MetaPin(*mutable_cf_options_),
        /*smallest_compaction_key=*/nullptr,
        /*largest_compaction_key=*/nullptr, /*allow_unprepared_value=*/true,
        cfd_->GetLatestMutableCFOptions()->block_protection_bytes_per_key,
        &tombstone_iter, range_start_key_, range_end_key_);

    std::vector<InternalIterator*> partial_file_iter;
    // TODO: (shubham) How to pull only range deletes for before and after range
    // [<<start, end>>]
    std::vector<std::unique_ptr<FragmentedRangeTombstoneIterator>>
        range_del_iters;

    ro.total_order_seek = true;  // TODO: (shubham) Why ?
    ro.io_activity = Env::IOActivity::kUnknown;
    // Arena arena;  // TODO: (shubham) This might not be required

    partial_file_iter.push_back(file_iter_);

    ROCKS_LOG_INFO(
        immutable_db_options_.info_log,
        "[%s] [JOB %d] Initiating partial flush for #%" PRIu64 "\n",
        cfd_->GetName().c_str(), job_context.job_id, old_file_meta->fd.GetNumber());
    
    event_logger_.Log() << "job" << job_context.job_id << "event"
                         << "partial_flush_started"
                         << "file_number" << old_file_meta->fd.GetNumber() << "num_entries"
                         << old_file_meta->num_entries << "num_deletes"
                         << old_file_meta->num_deletions << "total_data_size"
                         << old_file_meta->fd.GetFileSize() << "memory_usage"
                         << old_file_meta->ApproximateMemoryUsage() << "flush_reason"
                         << "range_query_compaction";


    ScopedArenaIterator iter(NewMergingIterator(
        &cfd_->internal_comparator(), partial_file_iter.data(),
        static_cast<int>(partial_file_iter.size()), &arena));

    ROCKS_LOG_INFO(
        immutable_db_options_.info_log,
        "[%s] [JOB %d] Level-%d partial flush file #%" PRIu64 ": started",
        cfd_->GetName().c_str(), job_context.job_id, level, old_file_meta->fd.GetNumber());


    int64_t _current_time = 0;
    auto status = GetSystemClock()->GetCurrentTime(&_current_time);

    if (!status.ok()) {
      ROCKS_LOG_WARN(
          immutable_db_options_.info_log,
          "Failed to get current time to populate creation_time property. "
          "Status: %s",
          status.ToString().c_str());
    }


    // TODO: (shubham) WARN ROCKSDB FOR FALIED status.ok() while getting current
    // time

    const uint64_t current_time = static_cast<uint64_t>(_current_time);
    uint64_t oldest_key_time = old_file_meta->file_creation_time;
    uint64_t oldest_ancester_time = std::min(current_time, oldest_key_time);

    meta_.fd = FileDescriptor(versions_->NewFileNumber(), 0, 0);
    meta_.epoch_number = cfd_->NewEpochNumber();
    meta_.oldest_ancester_time = oldest_ancester_time;
    meta_.file_creation_time = current_time;

    const std::string* const full_history_ts_low = nullptr;
    const std::string db_id = db_id_;
    const std::string db_session_id = db_session_id_;

    TableBuilderOptions tboptions(
        *cfd_->ioptions(), *mutable_cf_options_, cfd_->internal_comparator(),
        cfd_->int_tbl_prop_collector_factories(),
        GetCompressionFlush(*cfd_->ioptions(), *mutable_cf_options_),
        cfd_->GetCurrentMutableCFOptions()->compression_opts,
        cfd_->GetID(), cfd_->GetName(), level, is_bottom_most,
        TableFileCreationReason::kCompaction, oldest_key_time, current_time, db_id,
        db_session_id, 0 /* target_file_size */, meta_.fd.GetNumber());

    uint64_t num_input_entries = 0;
    uint64_t payload_bytes = 0;
    uint64_t garbage_bytes = 0;
    IOStatus io_s;

    // const std::shared_ptr<IOTracer> io_tracer_;
    // const SequenceNumber seq_no = 0;  // TODO: (shubham) Find this out
    const ReadOptions roptions(Env::IOActivity::kCompaction);
    std::vector<SequenceNumber> snapshot_seqs;
    SequenceNumber earliest_write_conflict_snapshot_;
    SnapshotChecker* snapshot_checker;
    GetSnapshotContext(&job_context, &snapshot_seqs,
                       &earliest_write_conflict_snapshot_, &snapshot_checker);
    const SequenceNumber job_snapshot_seq_ =
        job_context.GetJobSnapshotSequence();
    SeqnoToTimeMapping seqno_to_time_mapping_;
    // EventLogger* event_logger_;
    TableProperties table_properties_;

    s = BuildTable(
        dbname_, GetVersionSet(), immutable_db_options_, tboptions,
        file_options_, roptions, cfd_->table_cache(), iter.get(),
        std::move(range_del_iters), &meta_, &blob_file_additions, snapshot_seqs,
        earliest_write_conflict_snapshot_, job_snapshot_seq_, snapshot_checker,
        cfd_->GetCurrentMutableCFOptions()->paranoid_file_checks,
        cfd_->internal_stats(), &io_s, io_tracer_,
        BlobFileCreationReason::kCompaction, seqno_to_time_mapping_, &event_logger_,
        job_context.job_id, io_priority, &table_properties_, write_hint,
        full_history_ts_low, &blob_callback_, cfd_->current(), &num_input_entries,
        &payload_bytes, &garbage_bytes);

    // TODO: (shubham) may need verification for number of entries flushed
    s = io_s;
    
    // TODO: (shubham) may need to flush log here
    ROCKS_LOG_BUFFER(&log_buffer,
                     "[%s] [JOB %d] Level-%d flush new file #%" PRIu64 ": %" PRIu64
                     " bytes %s"
                     "%s",
                     cfd_->GetName().c_str(), job_context.job_id, level,
                     meta_.fd.GetNumber(), meta_.fd.GetFileSize(),
                     s.ToString().c_str(),
                     meta_.marked_for_compaction ? " (needs compaction)" : "");

    if (s.ok()) {
      s = GetDataDir(cfd_, 0U)->FsyncWithDirOptions(
          IOOptions(), nullptr,
          DirFsyncOptions(DirFsyncOptions::FsyncReason::kNewFileSynced));
    }
    mutex()->Unlock();
  }

  const bool has_output = meta_.fd.GetFileSize() > 0;

  if (s.ok() && has_output) {
    std::cout << "[####] Adding it to edits  for Level: " << level << " FileNumber: " << meta_.fd.GetNumber() << " " << __FILE__ << ":"
              << __LINE__ << " " << __FUNCTION__ << std::endl;
    edits_->AddFile(level, meta_.fd.GetNumber(), meta_.fd.GetPathId(),
                   meta_.fd.GetFileSize(), meta_.smallest, meta_.largest,
                   meta_.fd.smallest_seqno, meta_.fd.largest_seqno,
                   meta_.marked_for_compaction, meta_.temperature,
                   meta_.oldest_blob_file_number, meta_.oldest_ancester_time,
                   meta_.file_creation_time, meta_.epoch_number,
                   meta_.file_checksum, meta_.file_checksum_func_name,
                   meta_.unique_id, meta_.compensated_range_deletion_size,
                   meta_.tail_size, meta_.user_defined_timestamps_persisted);
    edits_->SetBlobFileAdditions(std::move(blob_file_additions));

  } else {
    return s.Aborted();
  }

  InternalStats::CompactionStats stats(CompactionReason::kManualCompaction, 1);
  const uint64_t micros = GetSystemClock()->NowMicros() - start_micros;
  const uint64_t cpu_micros = GetSystemClock()->CPUMicros() - start_cpu_micros;
  stats.micros = micros;
  stats.cpu_micros = cpu_micros;

  ROCKS_LOG_INFO(immutable_db_options_.info_log,
                 "[%s] [JOB %d] Flush lasted %" PRIu64
                 " microseconds, and %" PRIu64 " cpu microseconds.\n",
                 cfd_->GetName().c_str(), job_context.job_id, micros,
                 cpu_micros);

  if (has_output) {
    stats.bytes_written = meta_.fd.GetFileSize();
    stats.num_output_files = 1;
  }

  const auto& blobs = edits_->GetBlobFileAdditions();
  for (const auto& blob : blobs) {
    stats.bytes_written_blob += blob.GetTotalBlobBytes();
  }

  stats.num_output_files_blob = static_cast<int>(blobs.size());

  cfd_->internal_stats()->AddCompactionStats(level, Env::Priority::HIGH, stats);
  cfd_->internal_stats()->AddCFStats(
      InternalStats::BYTES_FLUSHED,
      stats.bytes_written + stats.bytes_written_blob);

  return s;
  // TODO: (shubham) might need to update the column family stats here
}

Status DBImpl::FlushLevelNFile() {
  std::cout << "[####] Starting Flush in Range Query at Level: " << range_query_last_level_ << " " << __FILE__ << ":"
            << __LINE__ << " " << __FUNCTION__ << std::endl;

  ColumnFamilyData* cfd_ =
      static_cast<ColumnFamilyHandleImpl*>(default_cf_handle_)->cfd();
  FileMetaData meta_;
  meta_.fd = FileDescriptor(versions_->NewFileNumber(), 0, 0);
  range_query_memtable_->SetFileNumber(meta_.fd.GetNumber());
  bool is_bottom_most = false;  // TODO: (shubham) Find this out
  JobContext job_context(next_job_id_.fetch_add(1), false);
  LogBuffer log_buffer(InfoLogLevel::INFO_LEVEL,
                       immutable_db_options_.info_log.get());

  mutex()->Lock();

  const uint64_t start_micros = GetSystemClock()->NowMicros();
  const uint64_t start_cpu_micros = GetSystemClock()->CPUMicros();
  Env::IOPriority io_priority = Env::IO_HIGH;
  const MutableCFOptions* mutable_cf_options_ =
      cfd_->GetLatestMutableCFOptions();
  
  ReadOptions ro;
  Status s;
  // skipping part of smallest_seqno ... ** NOT SURE WHERE IT IS USED **

  std::vector<BlobFileAddition> blob_file_additions;

  {
    auto write_hint = cfd_->CalculateSSTWriteHint(0);

    mutex()->Unlock();
    std::vector<InternalIterator*> memtables;
    std::vector<std::unique_ptr<FragmentedRangeTombstoneIterator>>
        range_del_iters;
    ro.total_order_seek = true;
    ro.io_activity = Env::IOActivity::kCompaction;
    Arena arena;

    memtables.push_back(range_query_memtable_->NewIterator(ro, &arena));
    // // TODO: (shubham) May need to add range deletes

    ROCKS_LOG_INFO(
        immutable_db_options_.info_log,
        "[%s] [JOB %d] Initiating in-range file flush #%" PRIu64 "\n",
        cfd_->GetName().c_str(), job_context.job_id, range_query_memtable_->GetFileNumber());
    
    event_logger_.Log() << "job" << job_context.job_id << "event"
                         << "in_range_file_flush_started"
                         << "file_number" << range_query_memtable_->GetFileNumber() << "num_entries"
                         << range_query_memtable_->num_entries() << "num_deletes"
                         << range_query_memtable_->num_deletes() << "total_data_size"
                         << range_query_memtable_->get_data_size() << "memory_usage"
                         << range_query_memtable_->ApproximateMemoryUsage() << "flush_reason"
                         << "range_query_compaction";

    ScopedArenaIterator iter(
        NewMergingIterator(&cfd_->internal_comparator(), memtables.data(),
                            static_cast<int>(memtables.size()), &arena));

    ROCKS_LOG_INFO(
        immutable_db_options_.info_log,
        "[%s] [JOB %d] Level-%d in-range file flush #%" PRIu64 ": started",
        cfd_->GetName().c_str(), job_context.job_id, range_query_last_level_, meta_.fd.GetNumber());


    int64_t _current_time = 0;
    auto status = GetSystemClock()->GetCurrentTime(&_current_time);

    if (!status.ok()) {
      ROCKS_LOG_WARN(
          immutable_db_options_.info_log,
          "Failed to get current time to populate creation_time property. "
          "Status: %s",
          status.ToString().c_str());
    }

    const uint64_t current_time = static_cast<uint64_t>(_current_time);

    uint64_t oldest_key_time = range_query_memtable_->ApproximateOldestKeyTime();

    // It's not clear whether oldest_key_time is always available. In case
    // it is not available, use current_time.
    uint64_t oldest_ancester_time = std::min(current_time, oldest_key_time);

    meta_.epoch_number = cfd_->NewEpochNumber();
    meta_.oldest_ancester_time = oldest_ancester_time;
    meta_.file_creation_time = current_time;

    const std::string* const full_history_ts_low = nullptr;
    const std::string db_id = db_id_;
    const std::string db_session_id = db_session_id_;

    TableBuilderOptions tboptions(
        *cfd_->ioptions(), *mutable_cf_options_, cfd_->internal_comparator(),
        cfd_->int_tbl_prop_collector_factories(),
        GetCompressionFlush(*cfd_->ioptions(), *mutable_cf_options_),
        cfd_->GetCurrentMutableCFOptions()->compression_opts,
        cfd_->GetID(), cfd_->GetName(), range_query_last_level_, is_bottom_most,
        TableFileCreationReason::kCompaction, oldest_key_time, current_time, db_id,
        db_session_id, 0 /* target_file_size */, meta_.fd.GetNumber());

    uint64_t num_input_entries = 0;
    uint64_t payload_bytes = 0;
    uint64_t garbage_bytes = 0;
    IOStatus io_s;
    const ReadOptions roptions(Env::IOActivity::kCompaction);
    std::vector<SequenceNumber> snapshot_seqs;
    SequenceNumber earliest_write_conflict_snapshot_;
    SnapshotChecker* snapshot_checker;
    GetSnapshotContext(&job_context, &snapshot_seqs,
                       &earliest_write_conflict_snapshot_, &snapshot_checker);
    const SequenceNumber job_snapshot_seq_ =
        job_context.GetJobSnapshotSequence();
    SeqnoToTimeMapping seqno_to_time_mapping_;
    TableProperties table_properties_;

    s = BuildTable(
        dbname_, GetVersionSet(), immutable_db_options_, tboptions,
        file_options_, roptions, cfd_->table_cache(), iter.get(),
        std::move(range_del_iters), &meta_, &blob_file_additions, snapshot_seqs,
        earliest_write_conflict_snapshot_, job_snapshot_seq_, snapshot_checker,
        cfd_->GetCurrentMutableCFOptions()->paranoid_file_checks,
        cfd_->internal_stats(), &io_s, io_tracer_,
        BlobFileCreationReason::kCompaction, seqno_to_time_mapping_, &event_logger_,
        job_context.job_id, io_priority, &table_properties_, write_hint,
        full_history_ts_low, &blob_callback_, cfd_->current(), &num_input_entries,
        &payload_bytes, &garbage_bytes);

    // TODO: (shubham) may need verification for number of entries flushed
    s = io_s;
    
    // TODO: (shubham) may need to flush log here

    ROCKS_LOG_BUFFER(&log_buffer,
                     "[%s] [JOB %d] Level-%d flush new file #%" PRIu64 ": %" PRIu64
                     " bytes %s"
                     "%s",
                     cfd_->GetName().c_str(), job_context.job_id, range_query_last_level_,
                     meta_.fd.GetNumber(), meta_.fd.GetFileSize(),
                     s.ToString().c_str(),
                     meta_.marked_for_compaction ? " (needs compaction)" : "");

    if (s.ok()) {
      s = GetDataDir(cfd_, 0U)->FsyncWithDirOptions(
          IOOptions(), nullptr,
          DirFsyncOptions(DirFsyncOptions::FsyncReason::kNewFileSynced));
    }
    mutex()->Unlock();
  }
  // base_->Unref();

  const bool has_output = meta_.fd.GetFileSize() > 0;

  if (s.ok() && has_output) {
    std::cout << "[####] Adding it to edits  for Level: " << range_query_last_level_ << " FileNumber: " << meta_.fd.GetNumber() << " " << __FILE__ << ":"
              << __LINE__ << " " << __FUNCTION__ << std::endl;
    edits_->AddFile(range_query_last_level_, meta_.fd.GetNumber(), meta_.fd.GetPathId(),
                   meta_.fd.GetFileSize(), meta_.smallest, meta_.largest,
                   meta_.fd.smallest_seqno, meta_.fd.largest_seqno,
                   meta_.marked_for_compaction, meta_.temperature,
                   meta_.oldest_blob_file_number, meta_.oldest_ancester_time,
                   meta_.file_creation_time, meta_.epoch_number,
                   meta_.file_checksum, meta_.file_checksum_func_name,
                   meta_.unique_id, meta_.compensated_range_deletion_size,
                   meta_.tail_size, meta_.user_defined_timestamps_persisted);
    edits_->SetBlobFileAdditions(std::move(blob_file_additions));

  SequenceNumber seq = versions_->LastSequence();
  range_query_memtable_ = cfd_->ConstructNewMemtable(cfd_->GetSuperVersion()->mutable_cf_options, seq);

  } else {
    return s.Aborted();
  }

  InternalStats::CompactionStats stats(CompactionReason::kManualCompaction, 1);
  const uint64_t micros = GetSystemClock()->NowMicros() - start_micros;
  const uint64_t cpu_micros = GetSystemClock()->CPUMicros() - start_cpu_micros;
  stats.micros = micros;
  stats.cpu_micros = cpu_micros;

  ROCKS_LOG_INFO(immutable_db_options_.info_log,
                 "[%s] [JOB %d] Flush lasted %" PRIu64
                 " microseconds, and %" PRIu64 " cpu microseconds.\n",
                 cfd_->GetName().c_str(), job_context.job_id, micros,
                 cpu_micros);

  if (has_output) {
    stats.bytes_written = meta_.fd.GetFileSize();
    stats.num_output_files = 1;
  }

  const auto& blobs = edits_->GetBlobFileAdditions();
  for (const auto& blob : blobs) {
    stats.bytes_written_blob += blob.GetTotalBlobBytes();
  }

  stats.num_output_files_blob = static_cast<int>(blobs.size());

  cfd_->internal_stats()->AddCompactionStats(range_query_last_level_, Env::Priority::HIGH, stats);
  cfd_->internal_stats()->AddCFStats(
      InternalStats::BYTES_FLUSHED,
      stats.bytes_written + stats.bytes_written_blob);

  return s;
  // TODO: (shubham) might need to update the column family stats here

  // TODO: (shubham)
  // Flush the table to level N take reference from Flush_Job::WriteLevel0Table and FlushLevelNPartialFile
  // Modify the common part from the FlushLevelNPartialFile and FlushLevelNFile
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

}  // namespace ROCKSDB_NAMESPACE
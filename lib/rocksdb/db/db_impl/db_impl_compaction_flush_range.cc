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
    unsigned long long level_size_in_bytes = 0;
    level_details << "\tLevel: " << std::to_string(l);

    unsigned long long total_entries_in_one_level = 0;
    std::stringstream level_sst_file_details;

    for (size_t file_index = 0; file_index < level_files_brief_.num_files;
         file_index++) {
      table_reader = nullptr;
      handle = nullptr;
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
    overlapping_count = table_properties->num_entries -
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

void DBImpl::SchedulePendingPartialRangeFlush(
    const RangeReduceFlushRequest& flush_req) {
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
    ++unscheduled_partial_flushes_;
    range_reduce_flush_queue_.push_back(flush_req);
  }
}

Status DBImpl::GetRangeReduceOutputs(
    int level, ColumnFamilyData* cfd,
    std::shared_ptr<RangeReduceOutputs>& rroutput, FileMetaData* file_meta) {
  std::lock_guard<std::mutex> lock(range_reduce_outputs_mutex_);
  uint64_t max_size =
      MaxFileSizeForLevel((*cfd->GetLatestMutableCFOptions()), level,
                          cfd->ioptions()->compaction_style);
  if (range_reduce_outputs_.find(level) != range_reduce_outputs_.end() &&
      !range_reduce_outputs_[level].empty()) {
    assert(range_reduce_outputs_[level].back() &&
           range_reduce_outputs_[level].back()->builder_);
    if (range_reduce_outputs_[level].back()->builder_->FileSize() > max_size) {
      range_reduce_outputs_[level].back()->finished.store(
          true, std::memory_order_relaxed);
      GetRangeReduceTableForLevel(level, cfd, file_meta);
    }
  } else {
    GetRangeReduceTableForLevel(level, cfd, file_meta);
  }
  if (!range_reduce_seen_error_.load(std::memory_order_relaxed)) {
    assert(!range_reduce_outputs_[level].empty());
    rroutput = range_reduce_outputs_[level].back();
    return Status::OK();
  }
  return Status::Corruption();
}

void DBImpl::GetRangeReduceTableForLevel(int level, ColumnFamilyData* cfd,
                                         FileMetaData* file_meta) {
  uint64_t max_size =
      MaxFileSizeForLevel((*cfd->GetLatestMutableCFOptions()), level,
                          cfd->ioptions()->compaction_style);
  std::shared_ptr<TableBuilder> piggyback_table = nullptr;
  std::unique_ptr<FSWritableFile> fs_writable_file;

  uint64_t file_number = versions_->NewFileNumber();
  std::string fname = TableFileName(cfd->ioptions()->cf_paths, file_number,
                                    0 /* output_path_id not applicable */);
  FileOptions fo_copy = file_options_;
  ROCKS_LOG_INFO(immutable_db_options_.info_log,
                 "Creating File #%" PRIu64 " or level %d", file_number, level);

  if (file_meta != nullptr) {
    ROCKS_LOG_INFO(immutable_db_options_.info_log,
                   "File #%" PRIu64 " is against File #%" PRIu64 "\n",
                   file_number, file_meta->fd.GetNumber());
  }

  Status s;
  IOStatus io_s = NewWritableFile(fs_.get(), fname, &fs_writable_file, fo_copy);
  s = io_s;

  if (!s.ok()) {
    range_reduce_seen_error_.store(true, std::memory_order_relaxed);
    ROCKS_LOG_ERROR(
        immutable_db_options_.info_log, "Failed to create table file #%llu: %s",
        static_cast<unsigned long long>(file_number), s.ToString().c_str());
    LogFlush(immutable_db_options_.info_log);
    return;
  }

  int64_t temp_current_time = 0;
  auto get_time_status =
      immutable_db_options_.clock->GetCurrentTime(&temp_current_time);
  if (!get_time_status.ok()) {
    ROCKS_LOG_WARN(immutable_db_options_.info_log,
                   "Failed to get current time. Status: %s",
                   get_time_status.ToString().c_str());
  }
  uint64_t current_time = static_cast<uint64_t>(temp_current_time);
  uint64_t oldest_ancester_time = 0;
  if (file_meta != nullptr) {
    oldest_ancester_time = file_meta->TryGetOldestAncesterTime();
  }
  uint64_t min_oldest_ancester_time =
      std::min(std::numeric_limits<uint64_t>::max(), oldest_ancester_time);

  if (level == range_query_last_level_ && file_meta != nullptr) {
    smallest_epoch_number_for_rr = file_meta->epoch_number;
  }

  uint64_t epoch_number = smallest_epoch_number_for_rr;

  if (file_meta != nullptr) {
    epoch_number = file_meta->epoch_number;
  }

  FileMetaData* meta = new FileMetaData();
  meta->fd = FileDescriptor(file_number, 0, 0);
  meta->oldest_ancester_time = oldest_ancester_time;
  meta->file_creation_time = current_time;
  meta->epoch_number = epoch_number;
  meta->temperature = Temperature::kUnknown;
  meta->fd.smallest_seqno = std::numeric_limits<uint64_t>::max();
  meta->fd.largest_seqno = 0;

  if (file_meta != nullptr) {
    meta->temperature = file_meta->temperature;
  }

  assert(!db_id_.empty());
  assert(!db_session_id_.empty());
  s = GetSstInternalUniqueId(db_id_, db_session_id_, meta->fd.GetNumber(),
                             &meta->unique_id);
  if (!s.ok()) {
    range_reduce_seen_error_.store(true, std::memory_order_relaxed);
    ROCKS_LOG_ERROR(immutable_db_options_.info_log,
                    "[%s] File #%" PRIu64 " failed to generate unique id: %s.",
                    cfd->GetName().c_str(), meta->fd.GetNumber(),
                    s.ToString().c_str());
    return;
  }
  fs_writable_file->SetIOPriority(Env::IOPriority::IO_LOW);
  fs_writable_file->SetWriteLifeTimeHint(cfd->CalculateSSTWriteHint(level));
  FileTypeSet tmp_set = immutable_db_options_.checksum_handoff_file_types;
  fs_writable_file->SetPreallocationBlockSize(max_size);
  auto writable_file_writer =
      std::shared_ptr<WritableFileWriter>(new WritableFileWriter(
          std::move(fs_writable_file), fname, fo_copy,
          immutable_db_options_.clock, io_tracer_, immutable_db_options_.stats,
          cfd->ioptions()->listeners,
          immutable_db_options_.file_checksum_gen_factory.get(),
          tmp_set.Contains(FileType::kTableFile), false));

  TableBuilderOptions tboptions(
      *cfd->ioptions(), *(cfd->GetLatestMutableCFOptions()),
      cfd->internal_comparator(), cfd->int_tbl_prop_collector_factories(),
      cfd->GetLatestMutableCFOptions()->compression,
      cfd->GetLatestMutableCFOptions()->compression_opts, cfd->GetID(),
      cfd->GetName(), level, false, TableFileCreationReason::kCompaction,
      0 /* oldest key time*/, current_time, db_id_, db_session_id_, max_size,
      file_number);

  piggyback_table = std::shared_ptr<TableBuilder>(
      NewTableBuilder(tboptions, writable_file_writer.get()));
  range_reduce_outputs_[level].push(std::make_shared<RangeReduceOutputs>(
      cfd, writable_file_writer, piggyback_table, meta, file_meta));

  ROCKS_LOG_INFO(immutable_db_options_.info_log,
                 "TableBuilder created for File #%llu at Level %d",
                 static_cast<unsigned long long>(file_number), level);
}

Status DBImpl::BackgroundPartialFlush(bool* made_progress,
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

  std::vector<SuperVersionContext>& superversion_contexts =
      job_context->superversion_contexts;
  while (!range_reduce_flush_queue_.empty()) {
    RangeReduceFlushRequest flush_req = range_reduce_flush_queue_.front();
    range_reduce_flush_queue_.pop_front();
    RQueryFileOverlap overlap_type = flush_req.overlap_type;
    FileMetaData* file_meta = flush_req.meta_data;
    int level = flush_req.level;

    if (overlap_type == RQueryFileOverlap::kHeadOverlap &&
        level == range_query_last_level_ &&
        !rq_done.load(std::memory_order_relaxed)) {
      range_reduce_flush_queue_.push_back(flush_req);
      unscheduled_partial_flushes_++;
      break;
    }

    ROCKS_LOG_INFO(immutable_db_options_.info_log,
                   "Processing partial flush request for Level: %d, Overlap "
                   "Type: %d, OldFileNo: %" PRIu64,
                   level, static_cast<int>(overlap_type),
                   file_meta->fd.GetNumber());

    superversion_contexts.clear();
    superversion_contexts.reserve(
        flush_req.cfd_to_max_mem_id_to_persist.size());
    for (const auto& iter : flush_req.cfd_to_max_mem_id_to_persist) {
      ColumnFamilyData* cfd = iter.first;
      FileMetaData* new_file_meta;
      // if just_delete is true add this file to the edits Delete and done!
      // handle non-range-qualifying entries of this file
      std::shared_ptr<RangeReduceOutputs> rroutput;
      status = GetRangeReduceOutputs(level, cfd, rroutput, file_meta);

      if (!status.ok()) {
        ROCKS_LOG_ERROR(immutable_db_options_.info_log,
                        "Failed to get the file from GetRangeReduceOutputs for "
                        "Level %d: %s",
                        level, status.ToString().c_str());
        cfd->UnrefAndTryDelete();
        return status;
      }

      std::shared_ptr<TableBuilder> tmp_memtable = rroutput->builder_;
      new_file_meta = rroutput->new_file_meta_;
      uint64_t max_size =
          MaxFileSizeForLevel((*cfd->GetLatestMutableCFOptions()), level,
                              cfd->ioptions()->compaction_style);

      ROCKS_LOG_INFO(immutable_db_options_.info_log,
                     "Created new SST table for Level %d, New FileNo: #%" PRIu64
                     "\n",
                     level, new_file_meta->fd.GetNumber());

      Arena arena;
      auto file_iter = cfd->table_cache()->NewIterator(
          read_options_, file_options_, cfd->internal_comparator(), *file_meta,
          /*range_del_agg=*/nullptr,
          cfd->GetLatestMutableCFOptions()->prefix_extractor, nullptr,
          cfd->internal_stats()->GetFileReadHist(0),
          TableReaderCaller::kUserIterator, &arena, /*skip_filters=*/false,
          level, MaxFileSizeForL0MetaPin((*cfd->GetLatestMutableCFOptions())),
          /*smallest_compaction_key=*/nullptr,
          /*largest_compaction_key=*/nullptr,
          /*allow_unprepared_value=*/true,
          cfd->GetLatestMutableCFOptions()->block_protection_bytes_per_key,
          /*range_del_iter=*/nullptr);

      if (overlap_type == RQueryFileOverlap::kContainedRQ) {
        file_iter->SeekToFirst();
        ROCKS_LOG_INFO(
            immutable_db_options_.info_log,
            "Processing kContainedRQ overlap for Level %d OldFileNo: %" PRIu64
            " New FileNo: #%" PRIu64 "\n",
            level, file_meta->fd.GetNumber(), new_file_meta->fd.GetNumber());
        for (; file_iter->Valid() &&
               cfd->internal_comparator()
                       .user_comparator()
                       ->CompareWithoutTimestamp(
                           read_options_.range_start_key,
                           ExtractUserKey(file_iter->key())) > 0;
             file_iter->Next()) {
          ParsedInternalKey parsed_key;
          assert(ParseInternalKey(file_iter->key(), &parsed_key, true).ok());
          const Slice& key = file_iter->key();
          const Slice& value = file_iter->value();
          tmp_memtable->Add(key, value);
          new_file_meta->UpdateBoundaries(key, value, parsed_key.sequence,
                                          parsed_key.type);
        }
        if (file_iter->Valid()) {
          file_iter->Seek(read_options_.range_end_key);
          while (file_iter->Valid() &&
                 cfd->user_comparator()->CompareWithoutTimestamp(
                     ExtractUserKey(file_iter->key()),
                     read_options_.range_end_key) <= 0) {
            file_iter->Next();
          }
          if (file_iter->Valid()) {
            for (; file_iter->Valid(); file_iter->Next()) {
              ParsedInternalKey parsed_key;
              assert(
                  ParseInternalKey(file_iter->key(), &parsed_key, true).ok());
              const Slice& key = file_iter->key();
              const Slice& value = file_iter->value();
              tmp_memtable->Add(key, value);
              new_file_meta->UpdateBoundaries(key, value, parsed_key.sequence,
                                              parsed_key.type);
            }
          }
        }
      } else if (overlap_type == RQueryFileOverlap::kHeadOverlap) {
        ROCKS_LOG_INFO(
            immutable_db_options_.info_log,
            "Processing kHeadOverlap overlap for Level %d OldFileNo: %" PRIu64
            " New FileNo: #%" PRIu64 "\n",
            level, file_meta->fd.GetNumber(), new_file_meta->fd.GetNumber());
        file_iter->Seek(read_options_.range_end_key);
        while (file_iter->Valid() &&
               cfd->internal_comparator()
                       .user_comparator()
                       ->CompareWithoutTimestamp(
                           read_options_.range_end_key,
                           ExtractUserKey(file_iter->key())) >= 0) {
          file_iter->Next();
        }
        for (; file_iter->Valid(); file_iter->Next()) {
          if (tmp_memtable->FileSize() >= max_size) {
            std::shared_ptr<RangeReduceOutputs> new_rroutput;
            status = GetRangeReduceOutputs(level, cfd, new_rroutput);

            if (!status.ok()) {
              ROCKS_LOG_ERROR(
                  immutable_db_options_.info_log,
                  "Failed to get the file from GetRangeReduceOutputs for "
                  "Level %d: %s",
                  level, status.ToString().c_str());
              cfd->UnrefAndTryDelete();
              return status;
            }

            tmp_memtable = new_rroutput->builder_;
            new_file_meta = new_rroutput->new_file_meta_;
          }
          ParsedInternalKey parsed_key;
          assert(ParseInternalKey(file_iter->key(), &parsed_key, true).ok());
          const Slice& key = file_iter->key();
          const Slice& value = file_iter->value();
          tmp_memtable->Add(key, value);
          new_file_meta->UpdateBoundaries(key, value, parsed_key.sequence,
                                          parsed_key.type);
        }
      } else if (overlap_type == RQueryFileOverlap::kTailOverlap) {
        ROCKS_LOG_INFO(
            immutable_db_options_.info_log,
            "Processing kTailOverlap overlap for Level %d OldFileNo: #%" PRIu64
            " New FileNo: #%" PRIu64 "\n",
            level, file_meta->fd.GetNumber(), new_file_meta->fd.GetNumber());
        file_iter->SeekToFirst();
        for (; file_iter->Valid() &&
               cfd->internal_comparator()
                       .user_comparator()
                       ->CompareWithoutTimestamp(
                           read_options_.range_start_key,
                           ExtractUserKey(file_iter->key())) > 0;
             file_iter->Next()) {
          ParsedInternalKey parsed_key;
          assert(ParseInternalKey(file_iter->key(), &parsed_key, true).ok());
          const Slice& key = file_iter->key();
          const Slice& value = file_iter->value();
          tmp_memtable->Add(key, value);
          new_file_meta->UpdateBoundaries(key, value, parsed_key.sequence,
                                          parsed_key.type);
        }
      }
      ROCKS_LOG_INFO(immutable_db_options_.info_log,
                     "Completed processing for Level %d OldFileNo: #%" PRIu64
                     " New FileNo: #%" PRIu64 " Overlap Type: %d \n",
                     level, file_meta->fd.GetNumber(),
                     new_file_meta->fd.GetNumber(),
                     static_cast<int>(overlap_type));
      cfd->UnrefAndTryDelete();
    }
  }
  return Status::OK();
}

void DBImpl::BackgroundCallPartialFlush(Env::Priority thread_pri) {
  bool made_progress = false;
  JobContext job_context(next_job_id_.fetch_add(1), true);

  LogBuffer log_buffer(InfoLogLevel::INFO_LEVEL,
                       immutable_db_options_.info_log.get());
  {
    InstrumentedMutexLock l(&mutex_);
    assert(bg_partial_flush_scheduled_);
    num_running_flushes_++;

    std::unique_ptr<std::list<uint64_t>::iterator>
        pending_outputs_inserted_elem(new std::list<uint64_t>::iterator(
            CaptureCurrentFileNumberInPendingOutputs()));
    FlushReason reason;

    Status s = BackgroundPartialFlush(&made_progress, &job_context, &log_buffer,
                                      &reason, thread_pri);

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

    assert(num_running_flushes_ > 0);
    num_running_flushes_--;
    bg_partial_flush_scheduled_--;
    // See if there's more work to be done
    SchedulePartialFileFlush();

    if (unscheduled_partial_flushes_ == 0 && bg_partial_flush_running_ == 0 &&
        bg_partial_flush_scheduled_ == 0) {
      range_queries_complete_cv_.Signal();
    }
    atomic_flush_install_cv_.SignalAll();
    bg_cv_.SignalAll();
    // IMPORTANT: there should be no code after calling SignalAll. This call
    // may signal the DB destructor that it's OK to proceed with destruction.
    // In that case, all DB variables will be dealloacated and referencing
    // them will cause trouble.
  }
}

void DBImpl::BGWorkPartialFlush(void* args) {
  FlushThreadArg fta = *(reinterpret_cast<FlushThreadArg*>(args));
  delete reinterpret_cast<FlushThreadArg*>(args);

  IOSTATS_SET_THREAD_POOL_ID(fta.thread_pri_);
  static_cast_with_check<DBImpl>(fta.db_)->BackgroundCallPartialFlush(
      fta.thread_pri_);
}

void DBImpl::SchedulePartialFileFlush() {
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

  while (unscheduled_partial_flushes_ > 0 &&
         bg_partial_flush_scheduled_ < bg_job_limits.max_flushes) {
    bg_partial_flush_scheduled_++;
    FlushThreadArg* fta = new FlushThreadArg;
    fta->db_ = this;
    fta->thread_pri_ =
        Env::Priority::HIGH;  // schedule everything on high priority thread

    env_->Schedule(&DBImpl::BGWorkPartialFlush, fta, Env::Priority::HIGH, this,
                   &DBImpl::UnschedulePartialFlushCallback);
    --unscheduled_partial_flushes_;
  }
}

void DBImpl::UnschedulePartialFlushCallback(void* arg) {
  // Decrement bg_partial_flush_scheduled_ in flush callback
  reinterpret_cast<FlushThreadArg*>(arg)->db_->bg_partial_flush_scheduled_--;
  Env::Priority flush_pri = reinterpret_cast<FlushThreadArg*>(arg)->thread_pri_;
  if (Env::Priority::LOW == flush_pri) {
    TEST_SYNC_POINT("DBImpl::UnscheduleLowFlushCallback");
  } else if (Env::Priority::HIGH == flush_pri) {
    TEST_SYNC_POINT("DBImpl::UnscheduleHighFlushCallback");
  }
  delete reinterpret_cast<FlushThreadArg*>(arg);
  TEST_SYNC_POINT("DBImpl::UnscheduleFlushCallback");
}

void DBImpl::TryCleaningUpRangeReduce(ColumnFamilyData* cfd,
                                      JobContext* job_context) {
  ROCKS_LOG_WARN(immutable_db_options_.info_log,
                 "Seen error during RangeReduce porcess, cleaning up!");
  only_deletes_->Clear();

  for (const auto& pair : range_reduce_outputs_) {
    auto range_reduce_queue = range_reduce_outputs_[pair.first /* level */];
    while (!range_reduce_queue.empty()) {
      auto rr_output = range_reduce_queue.front();
      range_reduce_queue.pop();
      auto tmp_memtable = rr_output->builder_;
      auto fswritable_file = rr_output->writable_file_writer_;

      if (fswritable_file != nullptr) {
        tmp_memtable->Abandon();
        fswritable_file.reset();
      }
    }
  }
  Status s = Status::IOError();
  // If flush failed, we want to delete all temporary files that we might
  // have created. Thus, we force full scan in FindObsoleteFiles()
  FindObsoleteFiles(job_context, !s.ok() && !s.IsShutdownInProgress() &&
                                     !s.IsColumnFamilyDropped());
  // delete unnecessary files if any, this is done outside the mutex
  if (job_context->HaveSomethingToClean() ||
      job_context->HaveSomethingToDelete()) {
    mutex_.Unlock();
    TEST_SYNC_POINT("DBImpl::BackgroundCallFlush:FilesFound");
    // Have to flush the info logs before bg_flush_scheduled_--
    // because if bg_flush_scheduled_ becomes 0 and the lock is
    // released, the deconstructor of DB can kick in and destroy all the
    // states of DB so info_log might not be available after that point.
    // It also applies to access other states that DB owns.
    if (job_context->HaveSomethingToDelete()) {
      PurgeObsoleteFiles(*job_context);
    }
    job_context->Clean();
    mutex_.Lock();
  }
  TEST_SYNC_POINT("DBImpl::BackgroundCallFlush:ContextCleanedUp");

  cfd->UnrefAndTryDelete();
  range_reduce_outputs_.clear();
  ROCKS_LOG_WARN(immutable_db_options_.info_log,
                 "Seen error during RangeReduce porcess, cleanup done!");
  return;
}

void DBImpl::TakecareOfLeftoverPart(ColumnFamilyData* cfd_) {
  std::lock_guard<std::mutex> lock(range_reduce_outputs_mutex_);
  JobContext job_context(next_job_id_.fetch_add(1), true);
  if (range_reduce_seen_error_.load(std::memory_order_relaxed)) {
    TryCleaningUpRangeReduce(cfd_, &job_context);
    return;
  }

  {
    InstrumentedMutexLock l(&mutex_);

    Status ss;
    std::unique_ptr<VersionEdit> add_files_ = std::make_unique<VersionEdit>();
    ColumnFamilyData* cfd = nullptr;
    std::stringstream new_files;
    uint64_t bytes_written = 0;
    uint64_t files_flushed = 0;
    auto sfm = static_cast<SstFileManagerImpl*>(
        initial_db_options_.sst_file_manager.get());
    assert(sfm != nullptr);

    for (const auto& pair : range_reduce_outputs_) {
      int level = pair.first;
      auto range_reduce_queue = range_reduce_outputs_[level];
      while (!range_reduce_queue.empty()) {
        auto rr_output = range_reduce_queue.front();
        range_reduce_queue.pop();
        auto tmp_memtable = rr_output->builder_;
        cfd = rr_output->cfd_;
        auto new_file_meta = rr_output->new_file_meta_;
        auto fswriteable_file = rr_output->writable_file_writer_;
        auto file_meta = rr_output->old_file_meta_;
        tmp_memtable->Finish();
        new_file_meta->fd.file_size = tmp_memtable->FileSize();
        new_file_meta->tail_size = tmp_memtable->GetTailSize();
        new_file_meta->user_defined_timestamps_persisted =
            static_cast<bool>(tmp_memtable->GetTableProperties()
                                  .user_defined_timestamps_persisted);
        fswriteable_file->Flush();
        fswriteable_file->Sync(true);
        fswriteable_file.reset();
        add_files_->AddFile(level, *new_file_meta);

        if (sfm && new_file_meta != nullptr &&
            new_file_meta->fd.GetPathId() == 0) {
          ROCKS_LOG_INFO(
              immutable_db_options_.info_log,
              "Informing new file creation to SFM for File: #%" PRIu64
              " FileSize: %" PRIu64 "\n",
              new_file_meta->fd.GetNumber(), new_file_meta->fd.GetFileSize());
          Status add_s = sfm->OnAddFile(TableFileName(
              cfd->ioptions()->cf_paths, new_file_meta->fd.GetNumber(),
              0 /* output path id*/));
          if (!add_s.ok()) {
            ROCKS_LOG_ERROR(
                immutable_db_options_.info_log,
                "Failed informing new file creation to SFM for File: #%" PRIu64
                ". Error: %s FileSize: %" PRIu64 "\n",
                new_file_meta->fd.GetNumber(), add_s.ToString().c_str(),
                new_file_meta->fd.GetFileSize());
            range_reduce_seen_error_.store(true, std::memory_order_relaxed);
            break;
          }
        }

        new_files << "FNo. #" << new_file_meta->fd.GetNumber() << ":" << level
                  << " ";
        bytes_written += new_file_meta->fd.GetFileSize();
        files_flushed += 1;
      }
    }

    if (range_reduce_seen_error_.load(std::memory_order_relaxed) ||
        cfd == nullptr) {
      TryCleaningUpRangeReduce(cfd, &job_context);
      return;
    }

    ss = versions_->LogAndApply(cfd_, *cfd_->GetLatestMutableCFOptions(),
                                read_options_, only_deletes_, &mutex_,
                                directories_.GetDbDir());
    if (!ss.ok()) {
      ROCKS_LOG_ERROR(immutable_db_options_.info_log,
                      "Failed to delete files for RangeReduce: %s",
                      ss.ToString().c_str());
    }
    ROCKS_LOG_INFO(
        immutable_db_options_.info_log,
        "Applied log and cleaned up older files for ColumnFamily: %s",
        cfd_->GetName().c_str());

    ss = versions_->LogAndApply(cfd, *cfd->GetLatestMutableCFOptions(),
                                read_options_, add_files_.get(), &mutex_,
                                directories_.GetDbDir());
    if (!ss.ok()) {
      ROCKS_LOG_ERROR(immutable_db_options_.info_log,
                      "Failed to apply log for new files in RangeReduce: %s",
                      ss.ToString().c_str());
    }
    ROCKS_LOG_INFO(immutable_db_options_.info_log,
                   "Successfully applied log for newly generated files [%s]",
                   new_files.str().c_str());
    assert(ss.ok());

    RecordTick(stats_, RANGEREDUCE_FILE_WRITE_BYTES, bytes_written);
    RecordTick(stats_, RANGEREDUCE_FILE_FLUSH_COUNT, files_flushed);

    SuperVersionContext* superversion_context =
        &job_context.superversion_contexts.back();
    InstallSuperVersionAndScheduleWork(cfd_, superversion_context,
                                       *cfd_->GetLatestMutableCFOptions());
    cfd_->current()->storage_info()->ComputeCompactionScore(
        *cfd->ioptions(), *cfd_->GetLatestMutableCFOptions());
    ROCKS_LOG_INFO(immutable_db_options_.info_log,
                   "Installed new SuperVersion and compaction score updated.");
    range_reduce_outputs_.clear();
    only_deletes_->Clear();
  }
}

void DBImpl::ForegroundPartialFlush(ColumnFamilyData* cfd,
                                    FileMetaData* file_meta, int level) {
  ROCKS_LOG_INFO(
      immutable_db_options_.info_log,
      "Starting foreground partial flush for ColumnFamily: %s, Level: "
      "%d, OldFileNo: #%" PRIu64 "\n",
      cfd->GetName().c_str(), level, file_meta->fd.GetNumber());
  std::shared_ptr<RangeReduceOutputs> rroutput;
  Status status = GetRangeReduceOutputs(level, cfd, rroutput, file_meta);

  if (!status.ok()) {
    ROCKS_LOG_ERROR(immutable_db_options_.info_log,
                    "Failed to get the file from GetRangeReduceOutputs for "
                    "Level %d: %s",
                    level, status.ToString().c_str());
    return;
  }

  std::shared_ptr<TableBuilder> sstable = rroutput->builder_;
  FileMetaData* new_file_meta = rroutput->new_file_meta_;
  uint64_t max_size =
      MaxFileSizeForLevel((*cfd->GetLatestMutableCFOptions()), level,
                          cfd->ioptions()->compaction_style);
  Arena arena;
  auto file_iter = cfd->table_cache()->NewIterator(
      read_options_, file_options_, cfd->internal_comparator(), *file_meta,
      /*range_del_agg=*/nullptr,
      cfd->GetLatestMutableCFOptions()->prefix_extractor, nullptr,
      cfd->internal_stats()->GetFileReadHist(0),
      TableReaderCaller::kUserIterator, &arena, /*skip_filters=*/false, level,
      MaxFileSizeForL0MetaPin((*cfd->GetLatestMutableCFOptions())),
      /*smallest_compaction_key=*/nullptr,
      /*largest_compaction_key=*/nullptr,
      /*allow_unprepared_value=*/true,
      cfd->GetLatestMutableCFOptions()->block_protection_bytes_per_key,
      /*range_del_iter=*/nullptr);
  file_iter->SeekToFirst();
  for (;
       file_iter->Valid() &&
       cfd->internal_comparator().user_comparator()->CompareWithoutTimestamp(
           read_options_.range_start_key, ExtractUserKey(file_iter->key())) > 0;
       file_iter->Next()) {
    ParsedInternalKey parsed_key;
    assert(ParseInternalKey(file_iter->key(), &parsed_key, true).ok());
    const Slice& key = file_iter->key();
    const Slice& value = file_iter->value();
    sstable->Add(key, value);
    new_file_meta->UpdateBoundaries(key, value, parsed_key.sequence,
                                    parsed_key.type);
  }
  ROCKS_LOG_INFO(immutable_db_options_.info_log,
                 "Foreground partial flush completed successfully for Level: "
                 "%d, OldFileNo: #%" PRIu64 " NewFileNo. #%" PRIu64 "\n",
                 level, file_meta->fd.GetNumber(),
                 new_file_meta->fd.GetNumber());
}

void DBImpl::AddPartialFileFlushRequest(RQueryFileOverlap overlap_type,
                                        FileMetaData* file_meta, int level) {
  if (level != -1 && (level < decision_cell_.start_level_ ||
                      level > decision_cell_.end_level_)) {
    file_meta->being_compacted = false;
    return;
  }

  ROCKS_LOG_INFO(immutable_db_options_.info_log,
                 "Adding partial flush request for Level: %d, Overlap Type: "
                 "%d, FileNo. #%" PRIu64 "\n",
                 level, static_cast<int>(overlap_type),
                 file_meta->fd.GetNumber());

  if (range_reduce_seen_error_.load(std::memory_order_relaxed)) {
    ROCKS_LOG_ERROR(immutable_db_options_.info_log,
                    "Flush request ignored due to seen range reduce error.");
    return;
  }

  auto cfh =
      static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  only_deletes_->SetColumnFamily(cfd->GetID());
  uint64_t file_number = file_meta->fd.GetNumber();
  only_deletes_->DeleteFile(level, file_number);

  ROCKS_LOG_INFO(immutable_db_options_.info_log,
                 "Marked FileNo. #%llu for deletion from Level %d.",
                 static_cast<unsigned long long>(file_number), level);

  // This below check cannot go up than this line
  if (overlap_type == RQueryFileOverlap::kCompleteOverlap) {
    ROCKS_LOG_INFO(
        immutable_db_options_.info_log,
        "File %llu has a complete overlap. No further action required.",
        static_cast<unsigned long long>(file_number));
    return;
  }

  if (level == range_query_last_level_) {
    if (overlap_type == RQueryFileOverlap::kTailOverlap ||
        overlap_type == RQueryFileOverlap::kContainedRQ) {
      ROCKS_LOG_INFO(immutable_db_options_.info_log,
                     "Processing foreground flush for Level: %d, File: %llu",
                     level, static_cast<unsigned long long>(file_number));
      ForegroundPartialFlush(cfd, file_meta, level);
    }
    if (overlap_type == RQueryFileOverlap::kHeadOverlap ||
        overlap_type == RQueryFileOverlap::kContainedRQ) {
      RangeReduceFlushRequest req{
          {{cfd, 0}}, RQueryFileOverlap::kHeadOverlap, file_meta, level};
      {
        InstrumentedMutexLock l(&mutex_);
        SchedulePendingPartialRangeFlush(req);
        SchedulePartialFileFlush();
        ROCKS_LOG_INFO(immutable_db_options_.info_log,
                       "Scheduled partial flush for Level: %d, File: %llu",
                       level, static_cast<unsigned long long>(file_number));
      }
    }
  } else {
    RangeReduceFlushRequest req{{{cfd, 0}}, overlap_type, file_meta, level};
    {
      InstrumentedMutexLock l(&mutex_);
      SchedulePendingPartialRangeFlush(req);
      SchedulePartialFileFlush();
      ROCKS_LOG_INFO(immutable_db_options_.info_log,
                     "Scheduled partial flush for Level: %d, File: %llu", level,
                     static_cast<unsigned long long>(file_number));
    }
  }
}
}  // namespace ROCKSDB_NAMESPACE
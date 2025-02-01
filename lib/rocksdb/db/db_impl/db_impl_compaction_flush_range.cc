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
    ++unscheduled_partial_or_range_flushes_;
    range_reduce_flush_queue_.push_back(flush_req);
  }
}

std::shared_ptr<TableBuilder> DBImpl::GetRangeReduceTableForLevel(
    int level, ColumnFamilyData* cfd, uint32_t job_id, FileMetaData* file_meta,
    bool create_forcefully) {
  // std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__ <<
  // std::endl
  //           << std::flush;
  std::shared_ptr<TableBuilder> piggyback_table = nullptr;
  uint64_t max_size =
      MaxFileSizeForLevel((*cfd->GetLatestMutableCFOptions()), level,
                          cfd->ioptions()->compaction_style);
  if (!create_forcefully && cfd->piggyback_table_map().find(level) !=
                                cfd->piggyback_table_map().end()) {
    piggyback_table = cfd->piggyback_table_map()[level];
  } else {
    // create a new table and return that pointer
    uint64_t file_number = versions_->NewFileNumber();
    std::string fname = TableFileName(cfd->ioptions()->cf_paths, file_number,
                                      0 /* output_path_id not applicable */);
    EventHelpers::NotifyTableFileCreationStarted(
        cfd->ioptions()->listeners, dbname_, cfd->GetName(), fname, job_id,
        TableFileCreationReason::kCompaction);
    std::unique_ptr<FSWritableFile> writable_file;
    FileOptions fo_copy = file_options_;

    std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
              << " file_name: " << fname
              << " last_file_name: " << file_meta->fd.GetNumber() << std::endl
              << std::flush;
    Status s;
    IOStatus io_s = NewWritableFile(fs_.get(), fname, &writable_file, fo_copy);
    s = io_s;

    if (!s.ok()) {
      ROCKS_LOG_ERROR(immutable_db_options_.info_log,
                      "[JOB %d] OpenCompactionOutputFiles for table #%" PRIu64
                      " fails at NewWritableFile with status %s",
                      job_id, file_number, s.ToString().c_str());
      LogFlush(immutable_db_options_.info_log);
      EventHelpers::LogAndNotifyTableFileCreationFinished(
          &event_logger_, cfd->ioptions()->listeners, dbname_, cfd->GetName(),
          fname, job_id, FileDescriptor(), kInvalidBlobFileNumber,
          TableProperties(), TableFileCreationReason::kCompaction, s,
          kUnknownFileChecksum, kUnknownFileChecksumFuncName);
      return nullptr;
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
    uint64_t oldest_ancester_time = file_meta->TryGetOldestAncesterTime();
    uint64_t min_oldest_ancester_time =
        std::min(std::numeric_limits<uint64_t>::max(), oldest_ancester_time);
    uint64_t epoch_number = file_meta->epoch_number;

    {
      FileMetaData meta;
      meta.fd = FileDescriptor(file_number, 0, 0);
      meta.oldest_ancester_time = oldest_ancester_time;
      meta.file_creation_time = current_time;
      meta.epoch_number = epoch_number;
      meta.temperature = file_meta->temperature;

      assert(!db_id_.empty());
      assert(!db_session_id_.empty());
      s = GetSstInternalUniqueId(db_id_, db_session_id_, meta.fd.GetNumber(),
                                 &meta.unique_id);
      if (!s.ok()) {
        ROCKS_LOG_ERROR(immutable_db_options_.info_log,
                        "[%s] [JOB %d] file #%" PRIu64
                        " failed to generate unique id: %s.",
                        cfd->GetName().c_str(), job_id, meta.fd.GetNumber(),
                        s.ToString().c_str());
        return nullptr;

        // BUG (Shubham): what do we do with meta????
      }
    }
      writable_file->SetIOPriority(Env::IOPriority::IO_USER);
      writable_file->SetWriteLifeTimeHint(cfd->CalculateSSTWriteHint(level));
      FileTypeSet tmp_set = immutable_db_options_.checksum_handoff_file_types;
      writable_file->SetPreallocationBlockSize(max_size);
      cfd->fswritable_file_map()[level] =
          std::shared_ptr<WritableFileWriter>(new WritableFileWriter(
              std::move(writable_file), fname, fo_copy,
              immutable_db_options_.clock, io_tracer_,
              immutable_db_options_.stats, cfd->ioptions()->listeners,
              immutable_db_options_.file_checksum_gen_factory.get(),
              tmp_set.Contains(FileType::kTableFile), false));

      TableBuilderOptions tboptions(
          *cfd->ioptions(), *(cfd->GetLatestMutableCFOptions()),
          cfd->internal_comparator(), cfd->int_tbl_prop_collector_factories(),
          cfd->GetLatestMutableCFOptions()->compression,
          cfd->GetLatestMutableCFOptions()->compression_opts, cfd->GetID(),
          cfd->GetName(), level, false, TableFileCreationReason::kCompaction,
          0 /* oldest key time*/, current_time, db_id_, db_session_id_,
          max_size, file_number);

      piggyback_table = std::shared_ptr<TableBuilder>(
          NewTableBuilder(tboptions, cfd->fswritable_file_map()[level].get()));

      cfd->piggyback_table_map()[level] = piggyback_table;
      std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
                << " File created, WritableFileWriter: "
                << cfd->fswritable_file_map()[level] << std::endl
                << std::flush;
      std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
                << " piggyback table PTR: " << cfd->piggyback_table_map()[level]
                << std::endl
                << std::flush;
  }
  return piggyback_table;
}

Status DBImpl::BackgroundPartialOrRangeFlush(bool* made_progress,
                                             JobContext* job_context,
                                             LogBuffer* log_buffer,
                                             FlushReason* reason,
                                             Env::Priority thread_pri) {
  // std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__ <<
  // std::endl
  //           << std::flush;
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
  // autovector<FlushRequest> to_be_pushed_back;
  while (!range_reduce_flush_queue_.empty()) {
    RangeReduceFlushRequest flush_req = range_reduce_flush_queue_.front();
    range_reduce_flush_queue_.pop_front();
    FlushReason flush_reason = flush_req.flush_reason;
    std::shared_ptr<TableBuilder> piggyback_table = flush_req.piggyback_table;
    int level = flush_req.level;
    bool just_delete = flush_req.just_delete;
    FileMetaData* file_meta = flush_req.meta_data;

    if (flush_reason == FlushReason::kRangeFlush) {
      level = decision_cell_.end_level_;
    }

    superversion_contexts.clear();
    superversion_contexts.reserve(
        flush_req.cfd_to_max_mem_id_to_persist.size());
    // std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
    //           << std::endl
    //           << std::flush;
    for (const auto& iter : flush_req.cfd_to_max_mem_id_to_persist) {
      // std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
      //           << std::endl
      //           << std::flush;
      ColumnFamilyData* cfd = iter.first;
      FileMetaData mmeta_;
      // if reason is kPartialFlush and just_delete is true
      // add this file to the edits Delete and we are done!
      if (flush_reason == FlushReason::kPartialFlush) {
        std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
                  << " JustDelete: " << just_delete << " level: " << level
                  << std::endl
                  << std::flush;
        if (just_delete) {
          if (immutable_db_options().verbosity > 1) {
            std::cout << "{\"FileNumber\": " << file_meta->fd.GetNumber()
                      << ", \"Level\": " << level
                      << ", \"ToCompactAccurate\": " << file_meta->num_entries
                      << "}," << std::endl
                      << std::flush;
          }
          assert(file_meta != nullptr);
          VersionEdit* edit_ = new VersionEdit();
          edit_->SetColumnFamily(cfd->GetID());
          uint64_t file_number = file_meta->fd.GetNumber();
          edit_->DeleteFile(level, file_number);
          Status ios = versions_->LogAndApply(
              cfd, *cfd->GetLatestMutableCFOptions(), read_options_, edit_,
              &mutex_, directories_.GetDbDir());
          range_reduce_flush_queue_.size() > 1
              ? --unscheduled_partial_or_range_flushes_
              : unscheduled_partial_or_range_flushes_;
          cfd->UnrefAndTryDelete();
          break;
        } else {
          std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
                    << " Prepare Piggyback table" << std::endl
                    << std::flush;
          // handle non-range-qualifying entries of this file
          std::shared_ptr<TableBuilder> tmp_memtable =
              GetRangeReduceTableForLevel(level, cfd, job_context->job_id,
                                          file_meta);
          uint64_t max_size =
              MaxFileSizeForLevel((*cfd->GetLatestMutableCFOptions()), level,
                                  cfd->ioptions()->compaction_style);
          Arena arena;
          auto file_iter = cfd->table_cache()->NewIterator(
              read_options_, file_options_, cfd->internal_comparator(),
              *file_meta,
              /*range_del_agg=*/nullptr,
              cfd->GetLatestMutableCFOptions()->prefix_extractor, nullptr,
              cfd->internal_stats()->GetFileReadHist(0),
              TableReaderCaller::kUserIterator, &arena, /*skip_filters=*/false,
              level,
              MaxFileSizeForL0MetaPin((*cfd->GetLatestMutableCFOptions())),
              /*smallest_compaction_key=*/nullptr,
              /*largest_compaction_key=*/nullptr,
              /*allow_unprepared_value=*/true,
              cfd->GetLatestMutableCFOptions()->block_protection_bytes_per_key,
              /*range_del_iter=*/nullptr);
          file_iter->SeekToFirst();
          std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
                    << std::endl
                    << std::flush;

          /*
            6. Range fits inside file overlap -- (Partial Partial Flush)

                        |---|
                      ---------
                      |       |
                      ---------
          */
          if (cfd->internal_comparator()
                      .user_comparator()
                      ->CompareWithoutTimestamp(
                          read_options_.range_start_key,
                          file_meta->smallest.user_key()) > 0 &&
              cfd->internal_comparator()
                      .user_comparator()
                      ->CompareWithoutTimestamp(read_options_.range_end_key,
                                                file_meta->largest.user_key()) <
                  0) {
            for (; file_iter->Valid() &&
                   cfd->internal_comparator()
                           .user_comparator()
                           ->CompareWithoutTimestamp(
                               read_options_.range_start_key,
                               file_iter->key()) > 0;
                 file_iter->Next()) {
              ParsedInternalKey parsed_key;
              if (ParseInternalKey(file_iter->key(), &parsed_key, true).ok()) {
                const Slice& key = file_iter->key();
                const Slice& value = file_iter->value();
                tmp_memtable->Add(key, value);
              } else {
                std::cout << __FILE__ << "[" << __FUNCTION__
                          << "]: " << __LINE__ << "ERROR: parsing internal key"
                          << std::endl
                          << std::flush;
              }
            }
            while (file_iter->Valid() &&
                   cfd->internal_comparator()
                           .user_comparator()
                           ->CompareWithoutTimestamp(
                               read_options_.range_end_key, file_iter->key()) <
                       0) {
              file_iter->Next();
            }
            for (; file_iter->Valid(); file_iter->Next()) {
              ParsedInternalKey parsed_key;
              if (ParseInternalKey(file_iter->key(), &parsed_key, true).ok()) {
                const Slice& key = file_iter->key();
                const Slice& value = file_iter->value();
                tmp_memtable->Add(key, value);
              } else {
                std::cout << __FILE__ << "[" << __FUNCTION__
                          << "]: " << __LINE__ << "ERROR: parsing internal key"
                          << std::endl
                          << std::flush;
              }
            }
          } else if ((cfd->internal_comparator().user_comparator()->Compare(
                          read_options_.range_start_key,
                          file_meta->smallest.user_key()) < 0 &&
                      cfd->internal_comparator().user_comparator()->Compare(
                          read_options_.range_end_key,
                          file_meta->smallest.user_key()) == 0) ||
                     (cfd->internal_comparator().user_comparator()->Compare(
                          read_options_.range_start_key,
                          file_meta->smallest.user_key()) <= 0 &&
                      cfd->internal_comparator().user_comparator()->Compare(
                          read_options_.range_end_key,
                          file_meta->largest.user_key()) < 0 &&
                      cfd->internal_comparator().user_comparator()->Compare(
                          read_options_.range_end_key,
                          file_meta->smallest.user_key()) > 0)) {
            while (file_iter->Valid() &&
                   cfd->internal_comparator()
                           .user_comparator()
                           ->CompareWithoutTimestamp(
                               read_options_.range_end_key, file_iter->key()) <
                       0) {
              file_iter->Next();
            }
            for (; file_iter->Valid(); file_iter->Next()) {
              ParsedInternalKey parsed_key;
              if (ParseInternalKey(file_iter->key(), &parsed_key, true).ok()) {
                const Slice& key = file_iter->key();
                const Slice& value = file_iter->value();
                tmp_memtable->Add(key, value);
              } else {
                std::cout << __FILE__ << "[" << __FUNCTION__
                          << "]: " << __LINE__ << "ERROR: parsing internal key"
                          << std::endl
                          << std::flush;
              }
              if (tmp_memtable->FileSize() >= max_size) {
                superversion_contexts.emplace_back(SuperVersionContext(true));
                bg_flush_args.emplace_back(
                    cfd, iter.second, &(superversion_contexts.back()),
                    FlushReason::kRangeFlush, tmp_memtable, level, just_delete,
                    nullptr);
                tmp_memtable = GetRangeReduceTableForLevel(
                    level, cfd, job_context->job_id, file_meta, true);
              }
            }
          } else {
            for (; file_iter->Valid() &&
                   cfd->internal_comparator()
                           .user_comparator()
                           ->CompareWithoutTimestamp(
                               read_options_.range_start_key,
                               file_iter->key()) > 0;
                 file_iter->Next()) {
              ParsedInternalKey parsed_key;
              if (ParseInternalKey(file_iter->key(), &parsed_key, true).ok()) {
                const Slice& key = file_iter->key();
                const Slice& value = file_iter->value();
                tmp_memtable->Add(key, value);
              } else {
                std::cout << __FILE__ << "[" << __FUNCTION__
                          << "]: " << __LINE__ << "ERROR: parsing internal key"
                          << std::endl
                          << std::flush;
              }
            }
          }
          tmp_memtable->Finish();
        }
      }
      std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
                << std::endl
                << std::flush;
      if (cfd->IsDropped()) {
        column_families_not_to_flush.push_back(cfd);
        continue;
      }
      // superversion_contexts.emplace_back(SuperVersionContext(true));
      // bg_flush_args.emplace_back(
      //     cfd, iter.second, &(superversion_contexts.back()), flush_reason,
      //     piggyback_table, level, just_delete, file_meta);
    }
    if (!bg_flush_args.empty()) {
      break;
    }
  }

  if (!bg_flush_args.empty()) {
    std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
              << " Piggyback Table was full flushing" << std::endl
              << std::flush;
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
    std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
              << " Finishing" << std::endl
              << std::flush;
    // bg_flush_args[0].piggyback_table_->Finish();
    // status = FlushPartialOrRangeFiles(bg_flush_args, made_progress,
    // job_context, log_buffer, thread_pri);
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

    // If flush failed, we want to delete all temporary files that we might
    // have created. Thus, we force full scan in FindObsoleteFiles()
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
    // IMPORTANT: there should be no code after calling SignalAll. This call
    // may signal the DB destructor that it's OK to proceed with destruction.
    // In that case, all DB variables will be dealloacated and referencing
    // them will cause trouble.
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
  std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__ << std::endl
            << std::flush;
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

void DBImpl::AddPartialOrRangeFileFlushRequest(
    FlushReason flush_reason, ColumnFamilyData* cfd,
    std::shared_ptr<TableBuilder> piggyback_table, int level, bool just_delete,
    FileMetaData* file_meta) {
  // std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__ <<
  // std::endl
  //           << std::flush;
  if (level != -1 && (level < decision_cell_.start_level_ ||
                      level > decision_cell_.end_level_)) {
    if (flush_reason == FlushReason::kPartialFlush) {
      file_meta->being_compacted = false;
    }
    // std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
    //           << std::endl
    //           << std::flush;
    return;
  }

  if (cfd == nullptr) {
    auto cfh =
        static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
    cfd = cfh->cfd();
  }

  if (flush_reason == FlushReason::kRangeFlush) {
    mutex_.Lock();
    // std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
    //           << std::endl
    //           << std::flush;
    FileMetaData new_file_meta;
    int64_t _current_time = 0;
    auto status = GetSystemClock()->GetCurrentTime(&_current_time);
    new_file_meta.fd = FileDescriptor(versions_->NewFileNumber(), 0, 0);
    new_file_meta.epoch_number = cfd->NewEpochNumber();
    auto mutable_cf_options = cfd->GetLatestMutableCFOptions();
    const uint64_t current_time = static_cast<uint64_t>(_current_time);
    uint64_t oldest_key_time = new_file_meta.file_creation_time;

    // TableBuilderOptions tboptions(
    //     *cfd->ioptions(), mutable_cf_options, cfd->internal_comparator(),
    //     cfd->int_tbl_prop_collector_factories(),
    //     GetCompressionFlush(*cfd->ioptions(), *mutable_cf_options),
    //     mutable_cf_options->compression_opts, cfd->GetID(), cfd->GetName(),
    //     0 /* level */, false /* is_bottommost */,
    //     TableFileCreationReason::kFlush, oldest_key_time, current_time,
    //     db_id_, db_session_id_, 0 /* target_file_size */,
    //     file_meta.fd.GetNumber());
  } else {
    if (immutable_db_options().verbosity > 1) {
      std::cout << "{\"FileNumber\": " << file_meta->fd.GetNumber()
                << ", \"Level\": " << level
                << ", \"entriesToCompact\": " << file_meta->num_entries << "},"
                << std::endl
                << std::flush;
    }
  }

  // std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__ <<
  // std::endl
  //           << std::flush;
  RangeReduceFlushRequest req{flush_reason, {{cfd, 0}},  piggyback_table,
                              level,        just_delete, file_meta};

  {
    // std::cout << __FILE__ << ":" << __LINE__ << ": " << __FUNCTION__
    //           << std::endl
    //           << std::flush;
    InstrumentedMutexLock l(&mutex_);
    SchedulePendingPartialRangeFlush(req);
    SchedulePartialOrRangeFileFlush();
  }
}
}  // namespace ROCKSDB_NAMESPACE
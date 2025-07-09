//  Copyright (c) 2011-present, Facebook, Inc.  All rights reserved.
//  This source code is licensed under both the GPLv2 (found in the
//  COPYING file in the root directory) and Apache 2.0 License
//  (found in the LICENSE.Apache file in the root directory).
//
// Copyright (c) 2011 The LevelDB Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file. See the AUTHORS file for names of contributors.

#include "db/arena_wrapped_db_iter.h"

#include <chrono>

#include "logging/logging.h"
#include "memory/arena.h"
#include "rocksdb/env.h"
#include "rocksdb/iterator.h"
#include "rocksdb/options.h"
#include "table/internal_iterator.h"
#include "table/iterator_wrapper.h"
#include "util/user_comparator_wrapper.h"

// #define TIMEBREAK

namespace ROCKSDB_NAMESPACE {

Status ArenaWrappedDBIter::GetProperty(std::string prop_name,
                                       std::string* prop) {
  if (prop_name == "rocksdb.iterator.super-version-number") {
    // First try to pass the value returned from inner iterator.
    if (!db_iter_->GetProperty(prop_name, prop).ok()) {
      *prop = std::to_string(sv_number_);
    }
    return Status::OK();
  }
  return db_iter_->GetProperty(prop_name, prop);
}

void ArenaWrappedDBIter::Init(
    Env* env, const ReadOptions& read_options, const ImmutableOptions& ioptions,
    const MutableCFOptions& mutable_cf_options, const Version* version,
    const SequenceNumber& sequence, uint64_t max_sequential_skip_in_iteration,
    uint64_t version_number, ReadCallback* read_callback, DBImpl* db_impl,
    ColumnFamilyData* cfd, bool expose_blob_index, bool allow_refresh) {
  auto mem = arena_.AllocateAligned(sizeof(DBIter));
  db_iter_ =
      new (mem) DBIter(env, read_options, ioptions, mutable_cf_options,
                       ioptions.user_comparator, /* iter */ nullptr, version,
                       sequence, true, max_sequential_skip_in_iteration,
                       read_callback, db_impl, cfd, expose_blob_index);
  sv_number_ = version_number;
  read_options_ = read_options;
  allow_refresh_ = allow_refresh;
  memtable_range_tombstone_iter_ = nullptr;

  if (!CheckFSFeatureSupport(env->GetFileSystem().get(),
                             FSSupportedOps::kAsyncIO)) {
    read_options_.async_io = false;
  }
}

long long ArenaWrappedDBIter::GuessTheNumberOfKeysBWStartAndEnd(
    const std::string& given_start_key, const std::string& given_end_key,
    int level, FileMetaData* file_meta, Slice& useful_min_key,
    Slice& useful_max_key) {
  return db_impl_->GetRoughOverlappingEntries(given_start_key, given_end_key,
                                              level, file_meta, cfd_,
                                              useful_min_key, useful_max_key);
}

bool ArenaWrappedDBIter::CanPerformRangeQueryCompaction(
    uint64_t& entries_count, long long min_entries_shld_be_read_per_lvl) {
  auto storage_info = cfd_->current()->storage_info();

  if (storage_info->num_non_empty_levels() <= 2) {
    return false;
  }

  auto user_comparator_ = cfd_->internal_comparator().user_comparator();
  int num_levels_are_overlapping = 0;
  std::vector<float> decision_matrix_meta_data;

  for (int lvl = 1; lvl < storage_info->num_non_empty_levels(); lvl++) {
    int num_files_are_overlapping = 0;
    auto level_files = storage_info->LevelFilesBrief(lvl);
    auto num_files = level_files.num_files;
    long long E_useful_entries_in_level = 0;
    Slice useful_min_key = "";
    Slice useful_max_key = "";

    SequenceNumber seq = db_impl_->GetLatestSequenceNumber();
    InternalKey internal_start_key(Slice(read_options_.range_start_key), seq,
                                   kValueTypeForSeek);
    InternalKey internal_end_key(Slice(read_options_.range_end_key), seq,
                                 kValueTypeForSeek);
    size_t file_index_ = FindFile(cfd_->internal_comparator(), level_files,
                                  internal_start_key.Encode());

    for (; file_index_ < num_files; file_index_++) {
      auto& fd = level_files.files[file_index_];
      const Slice& smallest_key = fd.file_metadata->smallest.user_key();
      const Slice& largest_key = fd.file_metadata->largest.user_key();
      long long num_entries = fd.file_metadata->num_entries;

      bool start_key_in_range =
          user_comparator_->CompareWithoutTimestamp(
              Slice(read_options_.range_start_key), smallest_key) <= 0;
      bool end_key_in_range =
          user_comparator_->CompareWithoutTimestamp(
              Slice(read_options_.range_end_key), largest_key) >= 0;

      if (start_key_in_range && end_key_in_range) {
        num_files_are_overlapping++;
        E_useful_entries_in_level += num_entries;
        if (useful_min_key.empty()) {
          useful_min_key = smallest_key;
        }
        useful_max_key = largest_key;
      } else if (start_key_in_range && !end_key_in_range) {
        if (user_comparator_->Compare(Slice(read_options_.range_end_key),
                                      smallest_key) >= 0) {
          num_files_are_overlapping++;
          E_useful_entries_in_level += GuessTheNumberOfKeysBWStartAndEnd(
              "", read_options_.range_end_key, lvl, fd.file_metadata,
              useful_min_key, useful_max_key);
          break;
        }
      } else if (!start_key_in_range && end_key_in_range) {
        if (user_comparator_->Compare(Slice(read_options_.range_start_key),
                                      largest_key) <= 0) {
          num_files_are_overlapping++;
          E_useful_entries_in_level += GuessTheNumberOfKeysBWStartAndEnd(
              read_options_.range_start_key, "", lvl, fd.file_metadata,
              useful_min_key, useful_max_key);
        }
      } else if (!start_key_in_range && !end_key_in_range) {
        if (user_comparator_->Compare(Slice(read_options_.range_start_key),
                                      smallest_key) > 0 &&
            user_comparator_->Compare(Slice(read_options_.range_end_key),
                                      largest_key) < 0) {
          num_files_are_overlapping++;
          E_useful_entries_in_level += GuessTheNumberOfKeysBWStartAndEnd(
              read_options_.range_start_key, read_options_.range_end_key, lvl,
              fd.file_metadata, useful_min_key, useful_max_key);
          break;
        }
      }
    }

    entries_count += E_useful_entries_in_level;
    decision_matrix_meta_data.push_back(E_useful_entries_in_level);

    if (num_files_are_overlapping > 0 && (min_entries_shld_be_read_per_lvl == 0 ||
        E_useful_entries_in_level > min_entries_shld_be_read_per_lvl)) {
      num_levels_are_overlapping++;
    }
  }

  if (num_levels_are_overlapping <= 1) {
    DecisionCell best_decision_cell;
    db_impl_->decision_cell_ = best_decision_cell;
    return false;
  }

  ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log,
                 "Decision Matrix Meta:");
  for (size_t i = 0; i < decision_matrix_meta_data.size(); i++) {
    ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log,
                   "Level: %zu --> Total in-range entries: %" PRIu64, i + 1,
                   static_cast<uint64_t>(decision_matrix_meta_data[i]));
  }

  std::vector<std::vector<DecisionCell>> decision_matrix(
      decision_matrix_meta_data.size(),
      std::vector<DecisionCell>(decision_matrix_meta_data.size()));

  for (int i = 0; i < static_cast<int>(decision_matrix.size()); i++) {
    for (int j = i; j < static_cast<int>(decision_matrix.size()); j++) {
      if (i == j) {
        decision_matrix[i][j] = DecisionCell(
            i + 1, j + 1,
            std::vector<float>(j - i + 1, read_options_.upper_threshold),
            read_options_);
      } else {
        std::vector<float> overlapping_entries_ratio(j - i, 0.0f);

        for (auto k = i; k < j; k++) {
          overlapping_entries_ratio[k - i] =
              decision_matrix_meta_data[k] / decision_matrix_meta_data[k + 1];
        }
        decision_matrix[i][j] = DecisionCell(
            i + 1, j + 1, overlapping_entries_ratio, read_options_);
      }
    }
  }

  DecisionCell best_decision_cell;

  for (size_t col = decision_matrix.size() - 1; col > 0; col--) {
    for (size_t row = 0; row < col; row++) {
      if (decision_matrix[row][col].GetDecision()) {
        best_decision_cell = decision_matrix[row][col];
        break;
      }
    }
    if (best_decision_cell.GetStartLevel() != 0) {
      db_impl_->decision_cell_ = best_decision_cell;
      db_impl_->range_query_last_level_ = best_decision_cell.GetEndLevel();
      ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log,
                     "[Verbosity]: Best decision cell: (%d, %d)",
                     best_decision_cell.GetStartLevel(),
                     best_decision_cell.GetEndLevel());
      break;
    }
  }

  return best_decision_cell.GetStartLevel() != 0;
}

void ArenaWrappedDBIter::ResumeBackgroundWork() {
  read_options_.enable_range_query_compaction = false;
  read_options_.range_start_key.clear();
  read_options_.range_end_key.clear();
  db_impl_->read_options_ = read_options_;
  db_impl_->ContinueBackgroundWork();
}

Status ArenaWrappedDBIter::Reset(uint64_t& total_keys_read, bool& did_run_RR) {
  total_keys_read = db_iter_->GetKeysReadCount();
  did_run_RR = db_impl_->was_decision_true;

  if (!read_options_.enable_range_query_compaction) {
    return Status::OK();
  }

  if (db_impl_->read_options_.enable_range_query_compaction) {
    db_impl_->rq_done.store(true);
    while (db_impl_->bg_partial_flush_scheduled_ > 0 ||
           db_impl_->unscheduled_partial_flushes_ > 0 ||
           db_impl_->bg_partial_flush_running_ > 0) {
      db_impl_->range_queries_complete_cv_.Wait();
    }
    db_impl_->TakecareOfLeftoverPart(cfd_);
  }

  db_impl_->range_reduce_seen_error_.store(false, std::memory_order_relaxed);
  db_impl_->was_decision_true = false;
  db_impl_->rq_done.store(false);
  ResumeBackgroundWork();
  return Status::OK();
}

Status ArenaWrappedDBIter::Refresh() {
  if (cfd_ == nullptr || db_impl_ == nullptr || !allow_refresh_) {
    return Status::NotSupported("Creating renew iterator is not allowed.");
  }
  assert(db_iter_ != nullptr);
  // TODO(yiwu): For last_seq_same_as_publish_seq_==false, this is not the
  // correct behavior. Will be corrected automatically when we take a snapshot
  // here for the case of WritePreparedTxnDB.
  uint64_t cur_sv_number = cfd_->GetSuperVersionNumber();
  TEST_SYNC_POINT("ArenaWrappedDBIter::Refresh:1");
  TEST_SYNC_POINT("ArenaWrappedDBIter::Refresh:2");
  auto reinit_internal_iter = [&]() {
    Env* env = db_iter_->env();
    db_iter_->~DBIter();
    arena_.~Arena();
    new (&arena_) Arena();

    SuperVersion* sv = cfd_->GetReferencedSuperVersion(db_impl_);
    SequenceNumber latest_seq = db_impl_->GetLatestSequenceNumber();
    if (read_callback_) {
      read_callback_->Refresh(latest_seq);
    }
    Init(env, read_options_, *(cfd_->ioptions()), sv->mutable_cf_options,
         sv->current, latest_seq,
         sv->mutable_cf_options.max_sequential_skip_in_iterations,
         cur_sv_number, read_callback_, db_impl_, cfd_, expose_blob_index_,
         allow_refresh_);

    InternalIterator* internal_iter = db_impl_->NewInternalIterator(
        read_options_, cfd_, sv, &arena_, latest_seq,
        /* allow_unprepared_value */ true, /* db_iter */ this);
    internal_iter->is_rq_running = true;
    internal_iter->keys_read.store(0);
    SetIterUnderDBIter(internal_iter);
  };
  while (true) {
    if (sv_number_ != cur_sv_number) {
      reinit_internal_iter();
      break;
    } else {
      db_iter_->ResetKeysRead();
      db_iter_->ResetDbImpl(db_impl_);
      db_iter_->ResetReadOptions(read_options_);
      SequenceNumber latest_seq = db_impl_->GetLatestSequenceNumber();
      // Refresh range-tombstones in MemTable
      if (!read_options_.ignore_range_deletions) {
        SuperVersion* sv = cfd_->GetThreadLocalSuperVersion(db_impl_);
        TEST_SYNC_POINT_CALLBACK("ArenaWrappedDBIter::Refresh:SV", nullptr);
        auto t = sv->mem->NewRangeTombstoneIterator(
            read_options_, latest_seq, false /* immutable_memtable */);
        if (!t || t->empty()) {
          // If memtable_range_tombstone_iter_ points to a non-empty tombstone
          // iterator, then it means sv->mem is not the memtable that
          // memtable_range_tombstone_iter_ points to, so SV must have changed
          // after the sv_number_ != cur_sv_number check above. We will fall
          // back to re-init the InternalIterator, and the tombstone iterator
          // will be freed during db_iter destruction there.
          if (memtable_range_tombstone_iter_) {
            assert(!*memtable_range_tombstone_iter_ ||
                   sv_number_ != cfd_->GetSuperVersionNumber());
          }
          delete t;
        } else {  // current mutable memtable has range tombstones
          if (!memtable_range_tombstone_iter_) {
            delete t;
            db_impl_->ReturnAndCleanupSuperVersion(cfd_, sv);
            // The memtable under DBIter did not have range tombstone before
            // refresh.
            reinit_internal_iter();
            break;
          } else {
            delete *memtable_range_tombstone_iter_;
            *memtable_range_tombstone_iter_ = new TruncatedRangeDelIterator(
                std::unique_ptr<FragmentedRangeTombstoneIterator>(t),
                &cfd_->internal_comparator(), nullptr, nullptr);
          }
        }
        db_impl_->ReturnAndCleanupSuperVersion(cfd_, sv);
      }
      // Refresh latest sequence number
      db_iter_->set_sequence(latest_seq);
      db_iter_->set_valid(false);
      // Check again if the latest super version number is changed
      uint64_t latest_sv_number = cfd_->GetSuperVersionNumber();
      if (latest_sv_number != cur_sv_number) {
        // If the super version number is changed after refreshing,
        // fallback to Re-Init the InternalIterator
        cur_sv_number = latest_sv_number;
        continue;
      }
      break;
    }
  }

  return Status::OK();
}

Status ArenaWrappedDBIter::Refresh(const std::string& start_key,
                                   const std::string& end_key,
                                   uint64_t& entries_count, bool rqdc_enabled,
                                   long long min_entries_shld_be_read_per_lvl) {
  if (!rqdc_enabled) {
    return Refresh();
  }

  read_options_.enable_range_query_compaction = rqdc_enabled;
  read_options_.range_start_key = start_key;
  read_options_.range_end_key = end_key;
  // read_options_.seq = db_impl_->GetLatestSequenceNumber();
  db_impl_->read_options_ = read_options_;

  auto pause_status = db_impl_->PauseBackgroundWork();
  if (!pause_status.ok() ||
      !CanPerformRangeQueryCompaction(entries_count,
                                      min_entries_shld_be_read_per_lvl)) {
    ResumeBackgroundWork();
  } else {
    db_impl_->was_decision_true = true;
    db_impl_->added_last_table = false;
  }

  return Refresh();
}

ArenaWrappedDBIter* NewArenaWrappedDbIterator(
    Env* env, const ReadOptions& read_options, const ImmutableOptions& ioptions,
    const MutableCFOptions& mutable_cf_options, const Version* version,
    const SequenceNumber& sequence, uint64_t max_sequential_skip_in_iterations,
    uint64_t version_number, ReadCallback* read_callback, DBImpl* db_impl,
    ColumnFamilyData* cfd, bool expose_blob_index, bool allow_refresh) {
  ArenaWrappedDBIter* iter = new ArenaWrappedDBIter();
  iter->Init(env, read_options, ioptions, mutable_cf_options, version, sequence,
             max_sequential_skip_in_iterations, version_number, read_callback,
             db_impl, cfd, expose_blob_index, allow_refresh);

  if (db_impl != nullptr && cfd != nullptr && allow_refresh) {
    iter->StoreRefreshInfo(db_impl, cfd, read_callback, expose_blob_index);
  }

  return iter;
}

}  // namespace ROCKSDB_NAMESPACE

//  Copyright (c) 2011-present, Facebook, Inc.  All rights reserved.
//  This source code is licensed under both the GPLv2 (found in the
//  COPYING file in the root directory) and Apache 2.0 License
//  (found in the LICENSE.Apache file in the root directory).
//
// Copyright (c) 2011 The LevelDB Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file. See the AUTHORS file for names of contributors.

#include "db/arena_wrapped_db_iter.h"

// #include <iomanip>
#include <chrono>
#include <iostream>

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
    uint64_t& entries_count) {
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
          user_comparator_->Compare(Slice(read_options_.range_start_key),
                                    smallest_key) <= 0;
      bool end_key_in_range =
          user_comparator_->Compare(Slice(read_options_.range_end_key),
                                    largest_key) >= 0;

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

    if (num_files_are_overlapping > 0) {
      num_levels_are_overlapping++;
    }
  }

  if (num_levels_are_overlapping <= 1) {
    DecisionCell best_decision_cell;
    db_impl_->decision_cell_ = best_decision_cell;
    return false;
  }

  // if (db_impl_->immutable_db_options().verbosity > 1) {
  //   std::cout << "\nDecision Matrix Meta: " << std::endl;
  //   for (size_t i = 0; i < decision_matrix_meta_data.size(); i++) {
  //     std::cout << "Level: " << i + 1 << " --> Total in-range entries: "
  //               << decision_matrix_meta_data[i] << std::endl;
  //   }
  // }

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

  // if (db_impl_->immutable_db_options().verbosity > 1) {
  //   std::cout << "\nDecision Matrix Flat: " << std::endl;
  //   for (size_t i = 0; i < decision_matrix.size(); i++) {
  //     for (size_t j = i; j < decision_matrix.size(); j++) {
  //       std::cout << "StartLevel: " << decision_matrix[i][j].GetStartLevel()
  //       << " EndLevel: " << decision_matrix[i][j].GetEndLevel() << "
  //       OverlappingRatios: "; for (float val :
  //       decision_matrix[i][j].overlapping_entries_ratio_) {
  //         std::cout << val << ", ";
  //       }
  //       std::cout << std::endl;
  //     }
  //   }

  //   std::cout << "\nDecision Matrix: " << std::endl;
  //   for (size_t i = 0; i < decision_matrix.size(); i++) {
  //     for (size_t j = 0; j < decision_matrix.size(); j++) {
  //       for (float val : decision_matrix[i][j].overlapping_entries_ratio_) {
  //         std::cout << val << ", ";
  //       }
  //       std::cout << " | ";
  //     }
  //     std::cout << std::endl;
  //   }
  // }

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
      // if (db_impl_->immutable_db_options().verbosity > 0) {
      //   std::cout << "\n[Verbosity]: Best decision cell: ("
      //             << best_decision_cell.GetStartLevel() << ", "
      //             << best_decision_cell.GetEndLevel() << ")\n\n"
      //             << std::endl;
      // }
      break;
    }
  }

  return best_decision_cell.GetStartLevel() != 0;
}

Status ArenaWrappedDBIter::Refresh(const std::string& start_key,
                                   const std::string& end_key,
                                   uint64_t& entries_count, bool rqdc_enabled) {
  read_options_.range_query_stat.is_range_query_running = true;

  if (!rqdc_enabled) {
    return Refresh();
  }

  db_impl_->num_entries_skipped = 0;
  db_impl_->num_entries_compacted = 0;

  // Assign read options once to avoid multiple assignments
  read_options_.range_end_key = end_key;
  read_options_.range_start_key = start_key;
  read_options_.seq = db_impl_->GetLatestSequenceNumber();
  read_options_.enable_range_query_compaction = rqdc_enabled;
  db_impl_->read_options_ = read_options_;

  auto pause_status = db_impl_->PauseBackgroundWork();
  if (!pause_status.ok() || !CanPerformRangeQueryCompaction(entries_count)) {
    ResumeBackgroundWork();
  } else {
    db_impl_->was_decision_true = true;
    db_impl_->added_last_table = false;
  }

  return Refresh();
}

void ArenaWrappedDBIter::ResumeBackgroundWork() {
    db_impl_->ContinueBackgroundWork();
    read_options_.enable_range_query_compaction = false;
    read_options_.range_start_key.clear();
    read_options_.range_end_key.clear();
    db_impl_->read_options_ = read_options_;
}

Status ArenaWrappedDBIter::Reset(uint64_t& entries_skipped,
                                 uint64_t& entries_to_compact) {
  // Check if the last table is added to the queue

  if (!read_options_.enable_range_query_compaction) {
    read_options_.range_query_stat.is_range_query_running = false;
    read_options_.range_query_stat.reset();
    return Status::OK();
  }

  if (db_impl_->read_options_.enable_range_query_compaction) {
    if (!db_impl_->added_last_table && cfd_->mem_range() != nullptr &&
        cfd_->mem_range()->num_entries() > 0) {
      db_impl_->AddPartialOrRangeFileFlushRequest(FlushReason::kRangeFlush,
                                                  cfd_, cfd_->mem_range());
      db_impl_->added_last_table = true;
    }
    while (db_impl_->bg_partial_or_range_flush_scheduled_ > 0 ||
           db_impl_->unscheduled_partial_or_range_flushes_ > 0 ||
           db_impl_->bg_partial_or_range_flush_running_ > 0) {
      db_impl_->range_queries_complete_cv_.Wait();
    }
  }

  entries_skipped = db_impl_->num_entries_skipped;
  entries_to_compact = db_impl_->num_entries_read_to_compact;
  std::string levels_state_before =
      "Range Query Complete: Compacted << " +
      std::to_string(db_impl_->num_entries_compacted) +
      " Skipped: " + std::to_string(db_impl_->num_entries_skipped) +
      " Read to Compact: " +
      std::to_string(db_impl_->num_entries_read_to_compact);
  auto storage_info_before = cfd_->current()->storage_info();
  for (int l = 0; l < storage_info_before->num_non_empty_levels(); l++) {
    uint64_t total_entries = 0;
    levels_state_before += "\n\tLevel-" + std::to_string(l) + ": ";
    auto num_files = storage_info_before->LevelFilesBrief(l).num_files;
    for (size_t file_index = 0; file_index < num_files; file_index++) {
      auto fd = storage_info_before->LevelFilesBrief(l).files[file_index];
      levels_state_before +=
          "[" + std::to_string(fd.fd.GetNumber()) + "(" +
          fd.file_metadata->smallest.user_key().ToString() + ", " +
          fd.file_metadata->largest.user_key().ToString() + ")" +
          std::to_string(fd.file_metadata->num_entries) + "] ";
      total_entries += fd.file_metadata->num_entries;
    }
    levels_state_before += " = " + std::to_string(total_entries);
  }
  ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log, "%s \n",
                 levels_state_before.c_str());

  read_options_.range_query_stat.is_range_query_running = false;
  read_options_.range_query_stat.reset();
  // check if range query compaction was enabled, set to true
  // otherwise background compaction is already running
  if (db_impl_->read_options_.enable_range_query_compaction) {
    // db_impl_->RenameLevels();
    read_options_.range_end_key = "";
    read_options_.range_start_key = "";
    read_options_.enable_range_query_compaction = false;
    db_impl_->read_options_ = read_options_;
  }
  db_impl_->was_decision_true = false;
  db_impl_->num_entries_skipped = 0;
  db_impl_->num_entries_compacted = 0;
  db_impl_->num_entries_read_to_compact = 0;
  db_impl_->ContinueBackgroundWork();
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
    SetIterUnderDBIter(internal_iter);

    std::string levels_state = "Range Query Started:";
    auto storage_info = cfd_->current()->storage_info();
    for (int l = 0; l < storage_info->num_non_empty_levels(); l++) {
      uint64_t total_entries = 0;
      levels_state += "\n\tLevel-" + std::to_string(l) + ": ";
      auto num_files = storage_info->LevelFilesBrief(l).num_files;
      for (size_t file_index = 0; file_index < num_files; file_index++) {
        auto fd = storage_info->LevelFilesBrief(l).files[file_index];
        levels_state += "[" + std::to_string(fd.fd.GetNumber()) + "(" +
                        fd.file_metadata->smallest.user_key().ToString() +
                        ", " + fd.file_metadata->largest.user_key().ToString() +
                        ")" + std::to_string(fd.file_metadata->num_entries) +
                        "] ";
        total_entries += fd.file_metadata->num_entries;
      }
      levels_state += " = " + std::to_string(total_entries);
    }

    ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log, "%s \n",
                   levels_state.c_str());
  };
  while (true) {
    if (sv_number_ != cur_sv_number) {
      reinit_internal_iter();
      break;
    } else {
      db_iter_->JustResetDbImpl(db_impl_);
      db_iter_->JustResetReadOptions(read_options_);
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

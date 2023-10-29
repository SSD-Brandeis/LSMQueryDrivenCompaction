//  Copyright (c) 2011-present, Facebook, Inc.  All rights reserved.
//  This source code is licensed under both the GPLv2 (found in the
//  COPYING file in the root directory) and Apache 2.0 License
//  (found in the LICENSE.Apache file in the root directory).
//
// Copyright (c) 2011 The LevelDB Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file. See the AUTHORS file for names of contributors.

#include "db/arena_wrapped_db_iter.h"

#include <iomanip>
#include <iostream>

#include "logging/logging.h"
#include "memory/arena.h"
#include "rocksdb/env.h"
#include "rocksdb/iterator.h"
#include "rocksdb/options.h"
#include "table/internal_iterator.h"
#include "table/iterator_wrapper.h"
#include "util/user_comparator_wrapper.h"

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

long long ArenaWrappedDBIter::GuessTheDifferenceWithMinMaxKey(
    const std::string given_start_key, const std::string given_end_key,
    int level, FileMetaData* file_meta, Slice& useful_min_key,
    Slice& useful_max_key) {
  // Let's guess the lexicographic difference between two strings
  // TODO: (shubham) Implement this algorithm and think about
  // the abstract class to make this configurable from application
  // std::cout << "[Optimization]: trying to gess the difference " << __FILE__
  //           << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
  return db_impl_->GetRoughOverlappingEntries(given_start_key, given_end_key,
                                              level, file_meta, cfd_,
                                              useful_min_key, useful_max_key);
}

bool ArenaWrappedDBIter::CanPerformRangeQueryCompaction() {
  // Let's see how many levels >= 1 have data
  // for the requested range query and then
  // see how many files in each level contains
  // data from each level and lastly compute
  // the % age of data on each level

  auto storage_info_before = cfd_->current()->storage_info();

  if (storage_info_before->num_non_empty_levels() <= 3) {
    return false;
  }

  auto user_comparator_ = cfd_->internal_comparator().user_comparator();
  int num_levels_are_overlapping =
      0;  // if num_files > 1 are overlapping on a level, increase this

  // `decision_matrix_meta_data` store the `level`, `E_useful`, `E_unuseful`,
  // `Min_E_useful`, `Max_E_useful` and `Overlapping_Min_Max_E_useful`
  // `total_entries` for each level.
  std::vector<std::tuple<int, float, float, Slice, Slice, float, float,
                         std::string>>  // TODO: (shubham) remove this
                                        // after testing
      decision_matrix_meta_data;

  for (int l = 1; l < storage_info_before->num_non_empty_levels(); l++) {
    int num_files_are_overlapping = 0;
    auto num_files = storage_info_before->LevelFilesBrief(l).num_files;
    long long total_entries_will_be_read =
        0;  // total entries that will be read from this level

    long long E_useful_entries_in_level = 0;
    // long long E_unuseful_entries_in_level = 0;
    std::string file_names = "";
    Slice useful_min_key = "";
    Slice useful_max_key = "";

    size_t file_index_ = FindFile(cfd_->internal_comparator(),
                                  storage_info_before->LevelFilesBrief(l),
                                  Slice(read_options_.range_start_key));

    for (; file_index_ < num_files; file_index_++) {
      auto fd = storage_info_before->LevelFilesBrief(l).files[file_index_];

      // refer to NOTE in LevelIterator::Seek function
      //  4 & 5. start <= smallest and end >= largest
      if (user_comparator_->Compare(Slice(read_options_.range_start_key),
                                    fd.file_metadata->smallest.user_key()) <=
              0 &&
          user_comparator_->Compare(Slice(read_options_.range_end_key),
                                    fd.file_metadata->largest.user_key()) >=
              0) {
        // 100 % overlap
        // std::cout
        //     << "[Optimization]: Found 100 percent overlap (Total Entries: "
        //     << fd.file_metadata->num_entries << " )" << __FILE__ << ":"
        //     << __LINE__ << " " << __FUNCTION__ << std::endl;
        num_files_are_overlapping += 1;
        total_entries_will_be_read += fd.file_metadata->num_entries;
        E_useful_entries_in_level += fd.file_metadata->num_entries;
        file_names += std::to_string(fd.fd.GetNumber()) + " ";

        if (useful_min_key.empty()) {
          useful_min_key = fd.file_metadata->smallest.user_key();
          useful_max_key = fd.file_metadata->largest.user_key();
        } else {
          useful_max_key = fd.file_metadata->largest.user_key();
        }
      }
      // 2 & 3. head of a file overlap
      else if (  // 3. starts here
          (user_comparator_->Compare(Slice(read_options_.range_start_key),
                                     fd.file_metadata->smallest.user_key()) <=
               0 &&
           user_comparator_->Compare(Slice(read_options_.range_end_key),
                                     fd.file_metadata->largest.user_key()) <
               0 &&
           user_comparator_->Compare(Slice(read_options_.range_end_key),
                                     fd.file_metadata->smallest.user_key()) >
               0) ||
          (user_comparator_->Compare(Slice(read_options_.range_start_key),
                                     fd.file_metadata->smallest.user_key()) <
               0 &&
           user_comparator_->Compare(Slice(read_options_.range_end_key),
                                     fd.file_metadata->smallest.user_key()) ==
               0)) {
        // head overlap
        // std::cout << "[Optimization]: Found head overlap (Total Entries: "
        //           << fd.file_metadata->num_entries << " )" << __FILE__ << ":"
        //           << __LINE__ << " " << __FUNCTION__ << std::endl;
        num_files_are_overlapping += 1;
        total_entries_will_be_read += fd.file_metadata->num_entries;
        E_useful_entries_in_level += GuessTheDifferenceWithMinMaxKey(
            "", read_options_.range_end_key, l, fd.file_metadata,
            useful_min_key, useful_max_key);
        file_names += std::to_string(fd.fd.GetNumber()) + " ";
        // E_unuseful_entries_in_level +=
        //     fd.file_metadata->num_entries - E_useful_entries_in_level;
      }
      // 2 & 3. tail of a file overlap
      else if ((user_comparator_->Compare(
                    Slice(read_options_.range_start_key),
                    fd.file_metadata->smallest.user_key()) > 0 &&
                user_comparator_->Compare(
                    Slice(read_options_.range_start_key),
                    fd.file_metadata->largest.user_key()) < 0 &&
                user_comparator_->Compare(
                    Slice(read_options_.range_end_key),
                    fd.file_metadata->largest.user_key()) >= 0) ||
               (user_comparator_->Compare(
                    Slice(read_options_.range_start_key),
                    fd.file_metadata->largest.user_key()) == 0 &&
                user_comparator_->Compare(
                    Slice(read_options_.range_end_key),
                    fd.file_metadata->largest.user_key()) > 0)) {
        // tail overlap
        // std::cout << "[Optimization]: Found tail overlap (Total Entries: "
        //           << fd.file_metadata->num_entries << " )" << __FILE__ << ":"
        //           << __LINE__ << " " << __FUNCTION__ << std::endl;
        num_files_are_overlapping += 1;
        total_entries_will_be_read += fd.file_metadata->num_entries;
        E_useful_entries_in_level += GuessTheDifferenceWithMinMaxKey(
            read_options_.range_start_key, "", l, fd.file_metadata,
            useful_min_key, useful_max_key);
        file_names += std::to_string(fd.fd.GetNumber()) + " ";
        // E_unuseful_entries_in_level +=
        //     fd.file_metadata->num_entries - E_useful_entries_in_level;
      }
      // 6. Range fits inside file overlap
      else if (user_comparator_->Compare(
                   Slice(read_options_.range_start_key),
                   fd.file_metadata->smallest.user_key()) > 0 &&
               user_comparator_->Compare(Slice(read_options_.range_end_key),
                                         fd.file_metadata->largest.user_key()) <
                   0) {
        // single file
        // std::cout
        //     << "[Optimization]: Found single file overlap (Total Entries: "
        //     << fd.file_metadata->num_entries << " )" << __FILE__ << ":"
        //     << __LINE__ << " " << __FUNCTION__ << std::endl;
        num_files_are_overlapping += 1;
        total_entries_will_be_read += fd.file_metadata->num_entries;
        E_useful_entries_in_level += GuessTheDifferenceWithMinMaxKey(
            read_options_.range_start_key, read_options_.range_end_key, l,
            fd.file_metadata, useful_min_key, useful_max_key);
        file_names += std::to_string(fd.fd.GetNumber()) + " ";
      }
    }

    auto decision_meta = std::make_tuple(
        l, E_useful_entries_in_level,
        total_entries_will_be_read - E_useful_entries_in_level, useful_min_key,
        useful_max_key, E_useful_entries_in_level, total_entries_will_be_read,
        file_names);

    decision_matrix_meta_data.push_back(decision_meta);

    if (num_files_are_overlapping > 1) {
      // std::cout << "[NUM FILES ARE OVERLAPPING] : " <<
      // num_files_are_overlapping
      //           << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__
      //           << std::endl;
      num_levels_are_overlapping += 1;
    }
  }

  std::vector<std::vector<DecisionCell>> decision_matrix(
      decision_matrix_meta_data.size(),
      std::vector<DecisionCell>(decision_matrix_meta_data.size()));

  // NOTE: (shubham) doing it with worst complexity (change this later)

  for (size_t i = 0; i < decision_matrix.size(); i++) {
    for (size_t j = i; j < decision_matrix.size(); j++) {
      if (i == j) {
        decision_matrix[i][j] = DecisionCell(
            i + 1, j + 1,
            std::get<1>(decision_matrix_meta_data[i]) /
                (std::get<1>(decision_matrix_meta_data[i]) +
                 std::get<2>(decision_matrix_meta_data[i])),
            std::vector<float>(j - i + 1, read_options_.ltu_threshold),
            read_options_);
      } else {
        float useful = 0;
        float unuseful = 0;

        for (auto k = i; k <= j; k++) {
          useful += std::get<1>(decision_matrix_meta_data[k]);
          unuseful += std::get<2>(decision_matrix_meta_data[k]);
        }

        std::vector<float> overlapping_entries_ratio(j - i, 0.0f);

        for (auto k = i; k < j && k < decision_matrix_meta_data.size() - 1;
             k++) {
          overlapping_entries_ratio[k - i] =
              std::get<1>(decision_matrix_meta_data[k]) /
              std::get<1>(decision_matrix_meta_data[k + 1]);
        }
        decision_matrix[i][j] =
            DecisionCell(i + 1, j + 1, useful / (useful + unuseful),
                         overlapping_entries_ratio, read_options_);
      }
    }
  }

  // This block is just for logging
  {
    std::string decision_matrix_meta_data_str =
        "Range Query: " + read_options_.range_start_key + " ... " +
        read_options_.range_end_key;
    decision_matrix_meta_data_str += "\n\tDecision Meta Matrix:";
    decision_matrix_meta_data_str +=
        "\n\t\tLevel|E_useful|E_unuseful|Min_E_useful|Max_E_"
        "useful|Overlapping_Min_Max_E_useful|Total Entries|File "
        "Names";
    for (size_t lvl = 0; lvl < decision_matrix_meta_data.size(); lvl++) {
      auto row_tuple = decision_matrix_meta_data[lvl];
      decision_matrix_meta_data_str +=
          "\n\t\t" + std::to_string(std::get<0>(row_tuple)) + "|" +
          std::to_string(std::get<1>(row_tuple)) + "|" +
          std::to_string(std::get<2>(row_tuple)) + "|" +
          std::get<3>(row_tuple).ToString() + "|" +
          std::get<4>(row_tuple).ToString() + "|" +
          std::to_string(std::get<5>(row_tuple)) + "|" +
          std::to_string(std::get<6>(row_tuple)) + "|" + std::get<7>(row_tuple);
    }

    decision_matrix_meta_data_str += "\n\n\n\tDecision Matrix:";

    decision_matrix_meta_data_str += "\n";
    for (size_t lvl = 0; lvl < decision_matrix.size(); lvl++) {
      decision_matrix_meta_data_str += "|Level-" + std::to_string(lvl + 1);
    }

    for (size_t i = 0; i < decision_matrix.size(); i++) {
      decision_matrix_meta_data_str += "\n\t\tLevel-" + std::to_string(i + 1);
      for (size_t j = 0; j < decision_matrix.size(); j++) {
        decision_matrix_meta_data_str += "|";
        std::stringstream ss;
        ss << decision_matrix[i][j];
        decision_matrix_meta_data_str += ss.str();
      }
    }

    decision_matrix_meta_data_str += "\n\n       ";
    for (size_t lvl = 0; lvl < decision_matrix.size(); lvl++) {
      decision_matrix_meta_data_str += "|Level-" + std::to_string(lvl + 1);
    }
    for (size_t i = 0; i < decision_matrix.size(); i++) {
      decision_matrix_meta_data_str += "\nLevel-" + std::to_string(i + 1);
      for (size_t j = 0; j < decision_matrix.size(); j++) {
        decision_matrix_meta_data_str +=
            "|" + decision_matrix[i][j].GetDecision();
      }
    }

    ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log, "%s \n",
                   decision_matrix_meta_data_str.c_str());
  }
  DecisionCell best_decision_cell;

  for (size_t cell = decision_matrix.size() - 1; cell > 0; cell--) {
    for (size_t row = 0; row < cell; row++) {
      if (decision_matrix[row][cell].GetDecision() == "True") {
        best_decision_cell = decision_matrix[row][cell];
        break;
      }
    }
    if (best_decision_cell.GetStartLevel() != 0) {
      db_impl_->decision_cell_ = best_decision_cell;
      if (db_impl_->immutable_db_options().verbosity > 0) {
        std::cout << "\n[Verbosity]: best decision cell: " << best_decision_cell
                  << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__
                  << std::endl;
      }
      break;
    }
  }
  return best_decision_cell.GetStartLevel() != 0;
}

Status ArenaWrappedDBIter::Refresh(const std::string start_key,
                                   const std::string end_key) {
  if (db_impl_->immutable_db_options().verbosity > 0) {
    std::cout << "\n[Verbosity]: refreshing iterator " << __FILE__ ":"
              << __LINE__ << " " << __FUNCTION__ << std::endl;
    std::cout << "setting range_start_key to: " << start_key << " "
              << __FILE__ ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
    std::cout << "setting range_end_key to: " << end_key << " " << __FILE__ ":"
              << __LINE__ << " " << __FUNCTION__ << std::endl;
    std::cout << "enabling read compaction " << __FILE__ ":" << __LINE__ << " "
              << __FUNCTION__ << std::endl;
  }
  read_options_.range_end_key = end_key;
  read_options_.range_start_key = start_key;
  read_options_.range_query_compaction_enabled =
      true;  // making it default for this refresh func
  db_impl_->read_options_ = read_options_;

  if (db_impl_->immutable_db_options().verbosity > 0) {
    std::cout << "\n[Verbosity]: pausing background work " << __FILE__ ":"
              << __LINE__ << " " << __FUNCTION__ << std::endl;
  }

  db_impl_->PauseBackgroundWork();

  if (!CanPerformRangeQueryCompaction()) {
    if (db_impl_->immutable_db_options().verbosity > 0) {
      std::cout << "\n[Verbosity]: skipping this time "
                   "num_levels_are_overlapping <= 1 "
                << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__
                << std::endl;
      std::cout << "\n[Verbosity]: continuing background work " << __FILE__ ":"
                << __LINE__ << " " << __FUNCTION__ << std::endl;
      db_impl_->ContinueBackgroundWork();
      read_options_.range_query_compaction_enabled = false;
      read_options_.range_start_key = "";
      read_options_.range_end_key = "";
      db_impl_->read_options_ = read_options_;
    }
  } else {
    db_impl_->added_last_table = false;
  }

  return Refresh();
}

Status ArenaWrappedDBIter::Reset() {
  // db_impl_->WaitForCompact(WaitForCompactOptions());
  // Check if the last table is added to the queue
  if (!db_impl_->added_last_table) {
    MemTable* imm_range = cfd_->mem_range();
    db_impl_->AddPartialOrRangeFileFlushRequest(FlushReason::kRangeFlush, cfd_,
                                                imm_range);
    db_impl_->added_last_table = true;
  }
  bool background_work_continued = false;
  while (db_impl_->bg_partial_or_range_flush_scheduled_ > 0 ||
         db_impl_->unscheduled_partial_or_range_flushes_ > 0 ||
         db_impl_->bg_partial_or_range_flush_running_ > 0) {
    if (db_impl_->immutable_db_options().verbosity > 0) {
      std::cout << "\n[Verbosity] waiting for flush jobs, scheduled: "
                << db_impl_->bg_partial_or_range_flush_scheduled_
                << " unscheduled: "
                << db_impl_->unscheduled_partial_or_range_flushes_
                << " running: " << db_impl_->bg_partial_or_range_flush_running_
                << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__
                << std::endl;
    }
    if (db_impl_->unscheduled_partial_or_range_flushes_ == 0) {
      background_work_continued = true;
      if (db_impl_->immutable_db_options().verbosity > 0) {
        std::cout << "\n[Verbosity]: continuing background work "
                  << __FILE__ ":" << __LINE__ << " " << __FUNCTION__
                  << std::endl;
      }
      db_impl_->ContinueBackgroundWork();
    }
    db_impl_->SchedulePartialOrRangeFileFlush();
    std::this_thread::sleep_for(std::chrono::milliseconds(5000));
  }

  std::string levels_state_before = "Range Query Complete:";
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

  // check if range query compaction was enabled, set to true
  // otherwise background compaction is already running
  if (db_impl_->read_options_.range_query_compaction_enabled) {
    read_options_.range_end_key = "";
    read_options_.range_start_key = "";
    read_options_.range_query_compaction_enabled = false;
    db_impl_->read_options_ = read_options_;

    if (!background_work_continued) {
      if (db_impl_->immutable_db_options().verbosity > 0) {
        std::cout << "\n[Verbosity]: continuing background work "
                  << __FILE__ ":" << __LINE__ << " " << __FUNCTION__
                  << std::endl;
      }

      db_impl_->ContinueBackgroundWork();
    }
  }
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

    std::string levels_state_after = "Range Query Started:";
    auto storage_info_after = cfd_->current()->storage_info();
    for (int l = 0; l < storage_info_after->num_non_empty_levels(); l++) {
      uint64_t total_entries = 0;
      levels_state_after += "\n\tLevel-" + std::to_string(l) + ": ";
      auto num_files = storage_info_after->LevelFilesBrief(l).num_files;
      for (size_t file_index = 0; file_index < num_files; file_index++) {
        auto fd = storage_info_after->LevelFilesBrief(l).files[file_index];
        levels_state_after +=
            "[" + std::to_string(fd.fd.GetNumber()) + "(" +
            fd.file_metadata->smallest.user_key().ToString() + ", " +
            fd.file_metadata->largest.user_key().ToString() + ")" +
            std::to_string(fd.file_metadata->num_entries) + "] ";
        total_entries += fd.file_metadata->num_entries;
      }
      levels_state_after += " = " + std::to_string(total_entries);
    }

    ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log, "%s \n",
                   levels_state_after.c_str());
  };
  while (true) {
    if (sv_number_ != cur_sv_number) {
      reinit_internal_iter();
      break;
    } else {
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

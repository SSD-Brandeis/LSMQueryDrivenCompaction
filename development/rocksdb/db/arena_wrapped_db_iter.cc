//  Copyright (c) 2011-present, Facebook, Inc.  All rights reserved.
//  This source code is licensed under both the GPLv2 (found in the
//  COPYING file in the root directory) and Apache 2.0 License
//  (found in the LICENSE.Apache file in the root directory).
//
// Copyright (c) 2011 The LevelDB Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file. See the AUTHORS file for names of contributors.

#include <iostream>

#include "db/arena_wrapped_db_iter.h"

#include "memory/arena.h"
#include "rocksdb/env.h"
#include "rocksdb/iterator.h"
#include "rocksdb/options.h"
#include "table/internal_iterator.h"
#include "table/iterator_wrapper.h"
#include "util/user_comparator_wrapper.h"
#include "logging/logging.h"

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
  // std::cout << "[Shubham]: Initializing Arena Wrapped Db Iter " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;

  auto mem = arena_.AllocateAligned(sizeof(DBIter));
  // std::cout << "[Shubham]: Creating new object of DBIter " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;

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

Status ArenaWrappedDBIter::Refresh(const Slice& start_key, const Slice& end_key) {
  if (read_options_.iterate_lower_bound != nullptr) {
    prev_iterate_lower_bound = read_options_.iterate_lower_bound;
  }
  if (read_options_.iterate_upper_bound != nullptr) {
    prev_iterate_upper_bound = read_options_.iterate_upper_bound;
  }

  read_options_.iterate_upper_bound = new Slice(end_key);
  read_options_.iterate_lower_bound = new Slice(start_key);
  read_options_.range_query_compaction_enabled = true; // making it default for this refresh func
  db_impl_->PauseBackgroundWork();
  db_impl_->range_edit_ = new VersionEdit();
  db_impl_->range_edit_->SetColumnFamily(cfd_->GetID());

  std::string levels_state_before = "Range Query Started:";
  auto storage_info_before = cfd_->current()->storage_info();
  for (int l = 0; l < storage_info_before->num_non_empty_levels(); l++) {
    levels_state_before += "\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tLevel-" + std::to_string(l) + ": ";
    auto num_files = storage_info_before->LevelFilesBrief(l).num_files;
    for (size_t file_index = 0; file_index < num_files; file_index++) {
      auto fd = storage_info_before->LevelFilesBrief(l).files[file_index];
      levels_state_before += "[" + std::to_string(fd.fd.GetNumber()) + "(" + fd.file_metadata->smallest.user_key().ToString() + ", " + fd.file_metadata->largest.user_key().ToString() + ")" + "] ";
    }
  }
  ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log, "%s \n", levels_state_before.c_str());
  return Refresh();
}

Status ArenaWrappedDBIter::Reset() {
  delete read_options_.iterate_lower_bound;
  delete read_options_.iterate_upper_bound;
  read_options_.iterate_lower_bound = prev_iterate_lower_bound;
  read_options_.iterate_upper_bound = prev_iterate_upper_bound;
  std::cout << "[Shubham] Waiting for Flushes to complete " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
  // db_impl_->SchedulePartialOrRangeFileFlush();
  // db_impl_->WaitForCompact(WaitForCompactOptions());
  while (db_impl_->bg_partial_or_range_flush_scheduled_ > 0 || 
         db_impl_->unscheduled_partial_or_range_flushes_ > 0 ||
         db_impl_->bg_partial_or_range_flush_running_ > 0) {
    std::cout << "[Shubham] Still Pending ... " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
    db_impl_->SchedulePartialOrRangeFileFlush();
    std::this_thread::sleep_for(std::chrono::milliseconds(10000));
  }
  // db_impl_->TryAndInstallRangeQueryEdits(cfd_);

  std::string levels_state_before = "Range Query Complete:";
  auto storage_info_before = cfd_->current()->storage_info();
  for (int l = 0; l < storage_info_before->num_non_empty_levels(); l++) {
    levels_state_before += "\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tLevel-" + std::to_string(l) + ": ";
    auto num_files = storage_info_before->LevelFilesBrief(l).num_files;
    for (size_t file_index = 0; file_index < num_files; file_index++) {
      auto fd = storage_info_before->LevelFilesBrief(l).files[file_index];
      levels_state_before += "[" + std::to_string(fd.fd.GetNumber()) + "(" + fd.file_metadata->smallest.user_key().ToString() + ", " + fd.file_metadata->largest.user_key().ToString() + ")" + "] ";
    }
  }
  ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log, "%s \n", levels_state_before.c_str());
  db_impl_->ContinueBackgroundWork();
  return Status::OK();
}

Status ArenaWrappedDBIter::Refresh() {
  if (cfd_ == nullptr || db_impl_ == nullptr || !allow_refresh_) {
    return Status::NotSupported("Creating renew iterator is not allowed.");
  }
  // std::cout << "[Shubham]: Refreshing ArenaWrappedDBIter: " << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;

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


    std::string levels_state_before = "Before capture of super version:";
    auto storage_info_before = cfd_->current()->storage_info();
    for (int l = 0; l < storage_info_before->num_non_empty_levels(); l++) {
      levels_state_before += "\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tLevel-" + std::to_string(l) + ": ";
      auto num_files = storage_info_before->LevelFilesBrief(l).num_files;
      for (size_t file_index = 0; file_index < num_files; file_index++) {
        auto fd = storage_info_before->LevelFilesBrief(l).files[file_index];
        levels_state_before += "[" + std::to_string(fd.fd.GetNumber()) + "(" + fd.file_metadata->smallest.user_key().ToString() + ", " + fd.file_metadata->largest.user_key().ToString() + ")" + "] ";
      }
    }

    ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log, "%s \n", levels_state_before.c_str());

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

    std::string levels_state_after = "LSM While Refresh:";
    auto storage_info_after = cfd_->current()->storage_info();
    for (int l = 0; l < storage_info_after->num_non_empty_levels(); l++) {
      levels_state_after += "\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tLevel-" + std::to_string(l) + ": ";
      auto num_files = storage_info_after->LevelFilesBrief(l).num_files;
      for (size_t file_index = 0; file_index < num_files; file_index++) {
        auto fd = storage_info_after->LevelFilesBrief(l).files[file_index];
        levels_state_after += "[" + std::to_string(fd.fd.GetNumber()) + "(" + fd.file_metadata->smallest.user_key().ToString() + ", " + fd.file_metadata->largest.user_key().ToString() + ")" + "] ";
      }
    }

    ROCKS_LOG_INFO(db_impl_->immutable_db_options().info_log, "%s \n", levels_state_after.c_str());

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

  // std::cout << "[Shubham]: Creating New Arena Wrapped Db Iterator " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;

  ArenaWrappedDBIter* iter = new ArenaWrappedDBIter();
  iter->Init(env, read_options, ioptions, mutable_cf_options, version, sequence,
             max_sequential_skip_in_iterations, version_number, read_callback,
             db_impl, cfd, expose_blob_index, allow_refresh);

  // std::cout << "[Shubham]: Arena Wrapped DBIter Initialized " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;

  if (db_impl != nullptr && cfd != nullptr && allow_refresh) {
    iter->StoreRefreshInfo(db_impl, cfd, read_callback, expose_blob_index);
  }

  return iter;
}

}  // namespace ROCKSDB_NAMESPACE

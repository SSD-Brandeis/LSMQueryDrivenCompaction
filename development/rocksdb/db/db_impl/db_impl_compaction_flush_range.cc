// This file contain implementation for range query driven flush and compactions
// It would be quite similar to db_impl_compaction_flush.cc

#include "db/builder.h"
#include "db/compaction/compaction_outputs.h"
#include "db/db_impl/db_impl.h"
#include "file/read_write_util.h"
// #include "table/sst_file_dumper.h"

namespace ROCKSDB_NAMESPACE {

// TODO: (Shubham) The keys can be range deletes, the comparator should handle
// that case
//                 Update the Newly created File boundries
//                 Update meta data for the newly created file
//                 Check if any listners have to be notified for new file
//                 creation class SstFileManagerImpl -- Report to SSTFileManager
//                 for the new file creation
// Status DBImpl::FlushPartialSSTFile(IteratorWrapper iter, size_t level,
//                                    const Slice& target,
//                                    const InternalKeyComparator* comparator) {
//   // current output builder and writer
//   std::unique_ptr<TableBuilder> builder_;

//   // open partial file write compaction
//   uint64_t file_number = versions_->NewFileNumber();
//   const std::string fname =
//       TableFileName(immutable_db_options_.db_paths, file_number, 0);
//   ColumnFamilyData* cfd =
//       static_cast<ColumnFamilyHandleImpl*>(default_cf_handle_)->cfd();

//   // TODO: (shubham) Need job_id_ for notifying Table file creation started
//   // EventHelpers::NotifyTableFileCreationStarted(
//   //     cfd->ioptions()->listeners, dbname_, cfd->GetName(), fname, job_id_,
//   //     TableFileCreationReason::kCompaction);

//   // Make the output file
//   std::unique_ptr<FSWritableFile> writable_file;
//   const FileOptions fo_copy = file_options_;

//   IOStatus io_s = NewWritableFile(fs_.get(), fname, &writable_file, fo_copy);

//   Status s;
//   s = io_s;
//   if (!s.ok()) {
//     return s;
//   }

//   FileMetaData meta;
//   // TODO: (shubham) 0, 0 should be updated with path_id and file size
//   meta.fd = FileDescriptor(file_number, 0, 0);
//   assert(!db_id_.empty());
//   assert(!db_session_id_.empty());
//   s = GetSstInternalUniqueId(db_id_, db_session_id_, meta.fd.GetNumber(),
//                              &meta.unique_id);

//   if (!s.ok()) {
//     return s;
//   }

//   if (!iter.Valid()) {
//     iter.SeekToFirst();
//   }

//   int64_t temp_current_time = 0;
//   auto get_time_status =
//       immutable_db_options_.clock->GetCurrentTime(&temp_current_time);
//   uint64_t current_time = static_cast<uint64_t>(temp_current_time);

//   TableBuilderOptions tboptions(
//       *cfd->ioptions(), *(cfd->GetCurrentMutableCFOptions()),
//       cfd->internal_comparator(), cfd->int_tbl_prop_collector_factories(),
//       cfd->GetLatestCFOptions().compression,
//       cfd->GetLatestCFOptions().compression_opts, cfd->GetID(), cfd->GetName(),
//       level, false, TableFileCreationReason::kCompaction,
//       0 /* oldest_key_time */, current_time, db_id_, db_session_id_,
//       cfd->GetLatestCFOptions().target_file_size_base, file_number);

//   WritableFileWriter* file_writer_ =
//       new WritableFileWriter(std::move(writable_file), fname, fo_copy);

//   builder_.reset(NewTableBuilder(tboptions, file_writer_));

//   // TODO: (shubham) Could there be a better way instead
//   // of doing this in while loop (worst would be O(n))
//   int count_ = 0;
//   while (iter.Valid()) {
//     auto val = comparator->Compare(iter.key(), target.data()) > 0;
//     if (val) {
//       break;
//     }
//     ++count_;
//     builder_->Add(iter.key(), iter.value());
//     meta.UpdateBoundaries(iter.key(), iter.value(), versions_->LastSequence(),
//                           ExtractValueType(iter.key()));
//     iter.Next();
//   }

//   // TODO: (shubham) Remove the newly created file if current_entries count is 0
//   // if (s.ok() && current_entries == 0 && tp.num_range_deletions == 0) {
//   //   // If there is nothing to output, no necessary to generate a sst file.
//   //   // This happens when the output level is bottom level, at the same time
//   //   // the sub_compact output nothing.
//   //   std::string fname =
//   //       TableFileName(sub_compact->compaction->immutable_options()->cf_paths,
//   //                     meta->fd.GetNumber(), meta->fd.GetPathId());

//   //   // DeleteFile fails here
//   //   Status ds = env_->DeleteFile(fname);
//   //   if (!ds.ok()) {
//   //     ROCKS_LOG_WARN(
//   //         db_options_.info_log,
//   //         "[%s] [JOB %d] Unable to remove SST file for table #%" PRIu64
//   //         " at bottom level%s",
//   //         cfd->GetName().c_str(), job_id_, output_number,
//   //         meta->marked_for_compaction ? " (need compaction)" : "");
//   //   }

//   //   // Also need to remove the file from outputs, or it will be added to the
//   //   // VersionEdit.
//   //   outputs.RemoveLastOutput();
//   //   meta = nullptr;
//   // }

//   if (count_ > 0) {
//     builder_->Finish();
//     file_writer_->Close();
//     std::cout << "File Saved Successfully "
//               << " " << __FILE__ << ":" << __LINE__ << " File name: " << fname
//               << " "
//               << " " << __FUNCTION__ << std::endl;
//     if (s.ok()) {
//       std::cout << "Adding new file to edits fname: " << fname
//                 << " Level: " << level << " " << __FILE__ << ":" << __LINE__
//                 << " File name: " << fname << " "
//                 << " " << __FUNCTION__ << std::endl;
//       edits_->AddFile(level, meta);

//       // Report new file to SstFileManagerImpl
//       // auto sfm =
//       //     static_cast<SstFileManagerImpl*>(immutable_db_options_.sst_file_manager.get());

//       // if (sfm && meta.fd.GetPathId() == 0) {
//       //   Status add_s = sfm->OnAddFile(fname);
//       //   if (!add_s.ok() && s.ok()) {
//       //     s = add_s;
//       //   }
//       // }
//     }
//   }

//   builder_.reset();

//   // NOTE: For Testing
//   // Options op;
//   // Temperature tmpperature = meta.temperature;
//   // SstFileDumper sst_dump(op, TableFileName(immutable_db_options_.db_paths,
//   // file_number, 0), tmpperature,
//   // cfd->GetLatestCFOptions().target_file_size_base, false, false, false);
//   // sst_dump.DumpTable("dump_of_sst_file");

//   return s;
// }

void DBImpl::ApplyRangeQueryEdits() {
  std::cout << "[####] Calling Add Range Query Edits "
            << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__
            << std::endl;
  mutex()->AssertHeld();

  for (auto deleted_file : edits_->GetDeletedFiles()) {
    std::cout << "[####] Deleted File " << deleted_file.second << " "
              << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__
              << std::endl;
    MarkAsGrabbedForPurge(deleted_file.second);
  }

  auto cfh =
      static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  auto version = GetVersionSet();
  const ReadOptions read_options;
  const MutableCFOptions& cf_opts = *cfd->GetLatestMutableCFOptions();
  version->LogAndApply(cfd, cf_opts, read_options, &(*edits_), mutex(),
                       directories_.GetDbDir());
  SuperVersionContext* sv_context = new SuperVersionContext(true);
  InstallSuperVersionAndScheduleWork(cfd, sv_context, cf_opts);
  mutex()->Unlock();
}

void DBImpl::SetRangeQueryRunningToTrue(Slice* start_key, Slice* end_key) {
  // std::cout << "[####] Setting Range query running to True " << __FILE__ << ":"
  //           << __LINE__ << " " << __FUNCTION__ << std::endl;
  auto cfh =
      static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  cfd->SetRangeQueryRunningToTrue();

  // std::cout << "START_KEY: " << start_key->data() << " SIZE: " << start_key->size() << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
  // std::cout << "END_KEY: " << end_key->data() << " SIZE: " << end_key->size() << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
  // range_start_key_here = new Slice(start_key->data(), start_key->size());
  range_start_key_ = start_key->data();
  // range_end_key_here = new Slice(end_key->data(), end_key->size());
  range_end_key_ = end_key->data();
  read_options_.is_range_query_compaction_enabled = true;
  // std::cout << "START_KEY_: " << range_start_key_here->data() << " SIZE: " << range_start_key_here->size() << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
  // std::cout << "END_KEY_: " << range_end_key_here->data() << " SIZE: " << range_end_key_here->size() << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
  std::cout << std::endl << std::endl << std::endl << std::endl << std::endl << std::endl;
}

void DBImpl::SetRangeQueryRunningToFalse() {
  // std::cout << "[####] Setting Range query running to False " << __FILE__ << ":"
  //           << __LINE__ << " " << __FUNCTION__ << std::endl;
  auto cfh =
      static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  cfd->SetRangeQueryRunningToFalse();
  range_start_key_ = "";
  range_end_key_ = "";
  read_options_.is_range_query_compaction_enabled = false;
  // range_start_key_here = nullptr;
  // range_end_key_here = nullptr;
}

Status DBImpl::WriteLevelNTable(const LevelFilesBrief* flevel_, size_t file_index, int level) {
  std::cout << "[####] Starting Write Level: " << level << " file_index: " << file_index << " " << __FILE__ << ":"
            << __LINE__ << " " << __FUNCTION__ << std::endl;
  std::cout << "[####] File Number : " << flevel_->files[file_index].fd.GetNumber() << " " << __FILE__ << ":"
            << __LINE__ << " " << __FUNCTION__ << std::endl;

  // SystemClock* clock_;
  ColumnFamilyData* cfd_ =
      static_cast<ColumnFamilyHandleImpl*>(default_cf_handle_)->cfd();
  // VersionEdit* edit_;
  Version* base_;
  FileMetaData meta_;
  bool is_bottom_most = false;  // TODO: (shubham) Find this out

  // std::cout << "[####] mutex Asserting held Level: " << level << " file_index: " << file_index << " " << __FILE__ << ":"
  //           << __LINE__ << " " << __FUNCTION__ << std::endl;

  mutex()->AssertHeld();
  // const uint64_t start_micros = clock_->NowMicros();
  // const uint64_t start_cpu_micros = clock_->CPUMicros();
  Status s;
  // skipping part of smallest_seqno ... ** NOT SURE WHERE IT IS USED **

  std::vector<BlobFileAddition> blob_file_additions;

  {
    auto write_hint = cfd_->CalculateSSTWriteHint(0);
    Env::IOPriority io_priority = Env::IO_HIGH;
    FileMetaData* old_file_meta = flevel_->files[file_index].file_metadata;
    Arena arena;
    // RangeDelAggregator* range_del_agg_;
    TruncatedRangeDelIterator* tombstone_iter = nullptr;
    const MutableCFOptions* mutable_cf_options_ =
        cfd_->GetLatestMutableCFOptions();

    // // NOTE: For Testing
    // Options op;
    // Temperature tmpperature = old_file_meta->temperature;
    // SstFileDumper sst_dump(op, TableFileName(immutable_db_options_.db_paths, old_file_meta->fd.GetNumber(), 0), tmpperature,
    // cfd_->GetLatestCFOptions().target_file_size_base, false, false, false);
    // sst_dump.DumpTable("old_file_before_range_query" + std::to_string(old_file_meta->fd.GetNumber()));
    // std::cout << "[Shubham]: Old File Before Range Query range_start_key: " << range_start_key_ << " range_end_key: " << range_end_key_
    //           << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;

    mutex()->Unlock();

    // log buffer->FlushBufferToLog() -- ** NOT SURE WHY **
    // std::cout << "[####] Grabbing new iterator Level: " << level << " file_index: " << file_index << " " << __FILE__ << ":"
    //           << __LINE__ << " " << __FUNCTION__ << std::endl;
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
    
    // if (!file_iter_->Valid()) {
    //   // std::cout << "[####] File_Iter_ is not valid, performing SeekTofirst() " << __FILE__ << ":"
    //   //           << __LINE__ << " " << __FUNCTION__ << std::endl;
    //   file_iter_->SeekToFirst();
    // }

    std::vector<InternalIterator*> partial_file_iter;
    // TODO: (shubham) How to pull only range deletes for before and after range
    // [<<start, end>>]
    std::vector<std::unique_ptr<FragmentedRangeTombstoneIterator>>
        range_del_iters;

    ReadOptions ro;
    ro.total_order_seek = true;  // TODO: (shubham) Why ?
    ro.io_activity = Env::IOActivity::kFlush;
    // Arena arena;  // TODO: (shubham) This might not be required

    partial_file_iter.push_back(file_iter_);

    // std::cout << "[####] Initiating Scoped iterator " << __FILE__ << ":"
    //           << __LINE__ << " " << __FUNCTION__ << std::endl;

    ScopedArenaIterator iter(NewMergingIterator(
        &cfd_->internal_comparator(), partial_file_iter.data(),
        static_cast<int>(partial_file_iter.size()), &arena));
    
    // std::cout << "[####] Done Scoped iterator " << __FILE__ << ":"
    //           << __LINE__ << " " << __FUNCTION__ << std::endl;

    int64_t _current_time = 0;
    auto status = GetSystemClock()->GetCurrentTime(&_current_time);

    // std::cout << "[####] Got current Time " << __FILE__ << ":"
    //           << __LINE__ << " " << __FUNCTION__ << std::endl;

    // TODO: (shubham) WARN ROCKSDB FOR FALIED status.ok() while getting current
    // time

    const uint64_t current_time = static_cast<uint64_t>(_current_time);
    uint64_t oldest_key_time = old_file_meta->file_creation_time;
    uint64_t oldest_ancester_time = std::min(current_time, oldest_key_time);

    // std::cout << "[####] Creating new file " << __FILE__ << ":"
    //           << __LINE__ << " " << __FUNCTION__ << std::endl;

    meta_.fd = FileDescriptor(versions_->NewFileNumber(), 0, 0);
    meta_.epoch_number = cfd_->NewEpochNumber();
    meta_.oldest_ancester_time = oldest_ancester_time;
    meta_.file_creation_time = current_time;

    // std::cout << "[####] New file Number for Level: " << level << " FileNumber: " << meta_.fd.GetNumber() << " " << __FILE__ << ":"
    //           << __LINE__ << " " << __FUNCTION__ << std::endl;

    base_ = cfd_->current();
    base_->Ref();
    edits_->SetColumnFamily(cfd_->GetID());
    edits_->SetPrevLogNumber(0);

    const std::string* const full_history_ts_low = nullptr;
    const std::string db_id = db_id_;
    const std::string db_session_id = db_session_id_;

    // std::cout << "[####] Initiating Table options " << __FILE__ << ":"
    //           << __LINE__ << " " << __FUNCTION__ << std::endl;

    TableBuilderOptions tboptions(
        *cfd_->ioptions(), *mutable_cf_options_, cfd_->internal_comparator(),
        cfd_->int_tbl_prop_collector_factories(),
        GetCompressionFlush(*cfd_->ioptions(), *mutable_cf_options_),
        cfd_->GetCurrentMutableCFOptions()->compression_opts,
        cfd_->GetID(), cfd_->GetName(), level, is_bottom_most,
        TableFileCreationReason::kMisc, oldest_key_time, current_time, db_id,
        db_session_id, 0 /* target_file_size */, meta_.fd.GetNumber());

    uint64_t num_input_entries = 0;
    uint64_t payload_bytes = 0;
    uint64_t garbage_bytes = 0;
    IOStatus io_s;

    // const std::shared_ptr<IOTracer> io_tracer_;
    // const SequenceNumber seq_no = 0;  // TODO: (shubham) Find this out
    const ReadOptions roptions(Env::IOActivity::kFlush);
    std::vector<SequenceNumber> snapshot_seqs;
    SequenceNumber earliest_write_conflict_snapshot_;
    SnapshotChecker* snapshot_checker;
    JobContext job_context(next_job_id_.fetch_add(1), true);
    GetSnapshotContext(&job_context, &snapshot_seqs,
                       &earliest_write_conflict_snapshot_, &snapshot_checker);
    const SequenceNumber job_snapshot_seq_ =
        job_context.GetJobSnapshotSequence();
    SeqnoToTimeMapping seqno_to_time_mapping_;
    // EventLogger* event_logger_;
    TableProperties table_properties_;
    // BlobFileCompletionCallback* blob_callback_;
    // const std::string* const full_history_ts_low = nullptr;

    // std::cout << "[####] Building new table " << __FILE__ << ":"
    //           << __LINE__ << " " << __FUNCTION__ << std::endl;

    s = BuildTable(
        dbname_, GetVersionSet(), immutable_db_options_, tboptions,
        file_options_, roptions, cfd_->table_cache(), iter.get(),
        std::move(range_del_iters), &meta_, &blob_file_additions, snapshot_seqs,
        earliest_write_conflict_snapshot_, job_snapshot_seq_, snapshot_checker,
        cfd_->GetCurrentMutableCFOptions()->paranoid_file_checks,
        cfd_->internal_stats(), &io_s, io_tracer_,
        BlobFileCreationReason::kFlush, seqno_to_time_mapping_, &event_logger_,
        job_context.job_id, io_priority, &table_properties_, write_hint,
        full_history_ts_low, &blob_callback_, base_, &num_input_entries,
        &payload_bytes, &garbage_bytes);

    // TODO: (shubham) may need verification for number of entries flushed
    s = io_s;
    
    // TODO: (shubham) may need to flush log here

    if (s.ok()) {
      s = GetDataDir(cfd_, 0U)->FsyncWithDirOptions(
          IOOptions(), nullptr,
          DirFsyncOptions(DirFsyncOptions::FsyncReason::kNewFileSynced));
    }
    mutex()->Unlock();
  }
  base_->Unref();

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

    // // NOTE: For Testing
    // Options op;
    // Temperature tmpperature = meta_.temperature;
    // SstFileDumper sst_dump(op, TableFileName(immutable_db_options_.db_paths, meta_.fd.GetNumber(), 0), tmpperature,
    // cfd_->GetLatestCFOptions().target_file_size_base, false, false, false);
    // sst_dump.DumpTable("new_file_after_range_query" + std::to_string(meta_.fd.GetNumber()));
    // std::cout << "[Shubham]: New File After Range Query range_start_key: " << range_start_key_ << " range_end_key: " << range_end_key_
    //           << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
  } else {
    return s.Aborted();
  }

  return s;
  // TODO: (shubham) might need to update the column family stats here
}

Status DBImpl::FlushLevelNTable() {
  // TODO: (shubham)
  // Flush the table to level N take reference from Flush_Job::WriteLevel0Table and WriteLevelNTable
  // Modify the common part from the WriteLevelNTable and FlushLevelNTable
}

}  // namespace ROCKSDB_NAMESPACE
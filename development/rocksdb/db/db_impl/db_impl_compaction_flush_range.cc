// This file contain implementation for range query driven flush and compactions
// It would be quite similar to db_impl_compaction_flush.cc

#include "db/builder.h"
#include "db/compaction/compaction_outputs.h"
#include "db/db_impl/db_impl.h"
#include "file/read_write_util.h"

namespace ROCKSDB_NAMESPACE {

// TODO: (Shubham) The keys can be range deletes, the comparator should handle that case
//                 Update the Newly created File boundries
//                 Update meta data for the newly created file
//                 Check if any listners have to be notified for new file creation
//                 class SstFileManagerImpl -- Report to SSTFileManager for the new file creation
Status DBImpl::FlushPartialSSTFile(IteratorWrapper iter, size_t level,
                                   const Slice& target,
                                   const InternalKeyComparator* comparator) {
  // current output builder and writer
  std::unique_ptr<TableBuilder> builder_;

  // open partial file write compaction
  uint64_t file_number = versions_->NewFileNumber();
  const std::string fname =
      TableFileName(immutable_db_options_.db_paths, file_number, 0);
  ColumnFamilyData* cfd =
      static_cast<ColumnFamilyHandleImpl*>(default_cf_handle_)->cfd();

  // TODO: (shubham) Need job_id_ for notifying Table file creation started
  // EventHelpers::NotifyTableFileCreationStarted(
  //     cfd->ioptions()->listeners, dbname_, cfd->GetName(), fname, job_id_,
  //     TableFileCreationReason::kCompaction);

  // Make the output file
  std::unique_ptr<FSWritableFile> writable_file;
  const FileOptions fo_copy = file_options_;

  IOStatus io_s = NewWritableFile(fs_.get(), fname, &writable_file, fo_copy);

  Status s;
  s = io_s;
  if (!s.ok()) {
    return s;
  }

  FileMetaData meta;
  // TODO: (shubham) 0, 0 should be updated with path_id and file size
  meta.fd = FileDescriptor(file_number, 0, 0);
  assert(!db_id_.empty());
  assert(!db_session_id_.empty());
  s = GetSstInternalUniqueId(db_id_, db_session_id_, meta.fd.GetNumber(),
                             &meta.unique_id);

  if (!s.ok()) {
    return s;
  }

  if (!iter.Valid()) {
    iter.SeekToFirst();
  }

  int64_t temp_current_time = 0;
  auto get_time_status =
      immutable_db_options_.clock->GetCurrentTime(&temp_current_time);
  uint64_t current_time = static_cast<uint64_t>(temp_current_time);

  TableBuilderOptions tboptions(
      *cfd->ioptions(), *(cfd->GetCurrentMutableCFOptions()),
      cfd->internal_comparator(), cfd->int_tbl_prop_collector_factories(),
      cfd->GetLatestCFOptions().compression,
      cfd->GetLatestCFOptions().compression_opts, cfd->GetID(), cfd->GetName(),
      level, false, TableFileCreationReason::kCompaction,
      0 /* oldest_key_time */, current_time, db_id_, db_session_id_,
      cfd->GetLatestCFOptions().target_file_size_base, file_number);

  WritableFileWriter* file_writer_ =
      new WritableFileWriter(std::move(writable_file), fname, fo_copy);

  builder_.reset(NewTableBuilder(tboptions, file_writer_));

  // TODO: (shubham) Could there be a better way instead 
  // of doing this in while loop (worst would be O(n))
  int count_ = 0;
  while (iter.Valid()) {
    auto val = comparator->Compare(iter.key(), target.data()) > 0;
    if (val) {
      break;
    }
    ++count_;
    builder_->Add(iter.key(), iter.value());
    meta.UpdateBoundaries(iter.key(), iter.value(), versions_->LastSequence(), ExtractValueType(iter.key()));
    iter.Next();
  }

  // TODO: (shubham) Remove the newly created file if current_entries count is 0
  // if (s.ok() && current_entries == 0 && tp.num_range_deletions == 0) {
  //   // If there is nothing to output, no necessary to generate a sst file.
  //   // This happens when the output level is bottom level, at the same time
  //   // the sub_compact output nothing.
  //   std::string fname =
  //       TableFileName(sub_compact->compaction->immutable_options()->cf_paths,
  //                     meta->fd.GetNumber(), meta->fd.GetPathId());

  //   // DeleteFile fails here
  //   Status ds = env_->DeleteFile(fname);
  //   if (!ds.ok()) {
  //     ROCKS_LOG_WARN(
  //         db_options_.info_log,
  //         "[%s] [JOB %d] Unable to remove SST file for table #%" PRIu64
  //         " at bottom level%s",
  //         cfd->GetName().c_str(), job_id_, output_number,
  //         meta->marked_for_compaction ? " (need compaction)" : "");
  //   }

  //   // Also need to remove the file from outputs, or it will be added to the
  //   // VersionEdit.
  //   outputs.RemoveLastOutput();
  //   meta = nullptr;
  // }

  if (count_ > 0) {
    builder_->Finish();
    file_writer_->Close();
    std::cout << "File Saved Successfully " << " " << __FILE__ << ":" << __LINE__
              << " File name: " << fname << " "
              << " " << __FUNCTION__ << std::endl;
    if (s.ok()){
    std::cout << "Adding new file to edits fname: " << fname << " Level: " << level << " " << __FILE__ << ":" << __LINE__
              << " File name: " << fname << " "
              << " " << __FUNCTION__ << std::endl;
      edits_->AddFile(level, meta);
    }
  }

  // Report new file to SstFileManagerImpl
  // auto sfm =
  //     static_cast<SstFileManagerImpl*>(immutable_db_options_.sst_file_manager.get());
    
  // if (sfm && meta.fd.GetPathId() == 0) {
  //   Status add_s = sfm->OnAddFile(fname);
  //   if (!add_s.ok() && s.ok()) {
  //     s = add_s;
  //   }
  // }

  builder_.reset();

  // NOTE: For Testing
  // Options op;
  // Temperature tmpperature = meta.temperature;
  // SstFileDumper sst_dump(op, TableFileName(immutable_db_options_.db_paths,
  // file_number, 0), tmpperature,
  // cfd->GetLatestCFOptions().target_file_size_base, false, false, false);
  // sst_dump.DumpTable("dump_of_sst_file");

  return s;
}

void DBImpl::ApplyRangeQueryEdits(){
  std::cout << "[####] Calling Add Range Query Edits " << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl; 
  mutex()->AssertHeld();
  
  for (auto deleted_file : edits_->GetDeletedFiles()) {
    std::cout << "[####] Deleted File " << deleted_file.second << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl; 
    MarkAsGrabbedForPurge(deleted_file.second);
  }

  auto cfh = static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  auto version = GetVersionSet();
  const ReadOptions read_options;
  const MutableCFOptions& cf_opts = *cfd->GetLatestMutableCFOptions();
  version->LogAndApply(cfd, cf_opts, read_options, &(*edits_), mutex(), directories_.GetDbDir());
  SuperVersionContext *sv_context = new SuperVersionContext(true);
  InstallSuperVersionAndScheduleWork(cfd, sv_context, cf_opts);
  mutex()->Unlock();
}

void DBImpl::SetRangeQueryRunningToTrue() {
  std::cout << "[####] Setting Range query running to True " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl; 
  auto cfh = static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  cfd->SetRangeQueryRunningToTrue();
}

void DBImpl::SetRangeQueryRunningToFalse() {
  std::cout << "[####] Setting Range query running to False " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl; 
  auto cfh = static_cast_with_check<ColumnFamilyHandleImpl>(DefaultColumnFamily());
  ColumnFamilyData* cfd = cfh->cfd();
  cfd->SetRangeQueryRunningToFalse();
}

}  // namespace ROCKSDB_NAMESPACE
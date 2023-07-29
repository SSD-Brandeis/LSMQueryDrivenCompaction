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
  while (iter.Valid()) {
    auto val = comparator->Compare(iter.key(), target.data()) > 0;
    if (val) {
      break;
    }
    builder_->Add(iter.key(), iter.value());
    // TODO: Update boundaries of the partial file
    // meta.UpdateBoundaries();
    iter.Next();
  }

  builder_->Finish();
  file_writer_->Close();

  // NOTE: For Testing
  // Options op;
  // Temperature tmpperature = meta.temperature;
  // SstFileDumper sst_dump(op, TableFileName(immutable_db_options_.db_paths,
  // file_number, 0), tmpperature,
  // cfd->GetLatestCFOptions().target_file_size_base, false, false, false);
  // sst_dump.DumpTable("dump_of_sst_file");

  return s;
}

}  // namespace ROCKSDB_NAMESPACE
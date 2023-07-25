// This file contain implementation for range query driven flush and compactions
// It would be quite similar to db_impl_compaction_flush.cc

#include <iostream>

#include "db/db_impl/db_impl.h"
#include "file/read_write_util.h"

namespace ROCKSDB_NAMESPACE {

// TODO: (Shubham) The keys can be range deletes, your comparator should handle that case
Status DBImpl::FlushPartialSSTFile(IteratorWrapper iter, size_t level, const Slice &target, const InternalKeyComparator* comparator) {
    uint64_t file_number = versions_->NewFileNumber();
    std::string fname = TableFileName(immutable_db_options_.db_paths, file_number, 0);
    // ColumnFamilyData* cfd = static_cast<ColumnFamilyHandleImpl*>(default_cf_handle_)->cfd();
    std::unique_ptr<FSWritableFile> writable_file;
    FileOptions fo_copy = file_options_;

    std::cout << "[####]: Partial file name: " << fname << " for level: " << level << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;

    IOStatus io_s = NewWritableFile(fs_.get(), fname, &writable_file, fo_copy);

    std::cout << "[####]: NewWritableFile Status: " << io_s.ToString() << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;

    Status s;
    s = io_s;

    FileMetaData meta;
    meta.fd = FileDescriptor(file_number, 0, 0);
    assert(!db_id_.empty());
    assert(!db_session_id_.empty());
    s = GetSstInternalUniqueId(db_id_, db_session_id_, meta.fd.GetNumber(),
                               &meta.unique_id);
    
    std::cout << "[####]: Target key: " << target.data() << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;

    if (!iter.Valid())
    {
        std::cout << "[####]: Iter is not Valid, Performing SeekToFirst" << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
        iter.SeekToFirst();
    }

    while (iter.Valid())
    {
        auto val = comparator->Compare(iter.key(), target.data()) > 0;
        if (val) 
        {
            std::cout << "[####]: Stopping at key: " << iter.key().data() << " level: " << level << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
            break; 
        }
        std::cout << "[####]: Iter key: " << iter.key().data() << " level: " << level << " " << __FILE__ << ":" << __LINE__ << " " << __FUNCTION__ << std::endl;
        // iter.key();
        iter.Next();
    }
    
    // FileTypeSet tmp_set = initial_db_options_.checksum_handoff_file_types;

    return s;
}

}
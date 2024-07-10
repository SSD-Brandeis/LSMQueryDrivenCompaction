#pragma once

#include "db/compaction/compaction_picker.h"

namespace ROCKSDB_NAMESPACE {
// Picking compactions for tiering compaction.
class TieringCompactionPicker : public CompactionPicker {
 public:
  TieringCompactionPicker(const ImmutableOptions& ioptions,
                          const InternalKeyComparator* icmp)
      : CompactionPicker(ioptions, icmp) {}
  virtual Compaction* PickCompaction(const std::string& cf_name,
                                     const MutableCFOptions& mutable_cf_options,
                                     const MutableDBOptions& mutable_db_options,
                                     VersionStorageInfo* vstorage,
                                     LogBuffer* log_buffer) override;

  virtual bool NeedsCompaction(
      const VersionStorageInfo* vstorage) const override;
};
}  // namespace ROCKSDB_NAMESPACE
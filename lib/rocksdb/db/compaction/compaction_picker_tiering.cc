
#include "db/compaction/compaction_picker_tiering.h"

namespace ROCKSDB_NAMESPACE {
bool TieringCompactionPicker::NeedsCompaction(
    const VersionStorageInfo* vstorage) const {
        // NOTE: (shubham) keeping it very simple
        // 
        // just check the tiers for each level and see
        // if any of the level qualifies for compaction
        //
        // WE DON'T SUPPORT BELOW FOR NOW:
        //  - ExpiredTtlFiles
        //  - PeriodicCompaction
        for (int i = 0; i < vstorage->MaxInputLevel(); i++) {
            
        }
    }
}  // namespace ROCKSDB_NAMESPACE
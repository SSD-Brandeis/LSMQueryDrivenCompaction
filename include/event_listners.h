#ifndef EVENT_LISTNER_H_
#define EVENT_LISTNER_H_

#include <rocksdb/db.h>

#include <condition_variable>

using namespace rocksdb;

extern std::mutex mtx;
extern std::condition_variable cv;
extern bool compaction_complete;

/*
 * Wait for compactions that are running (or will run) to make the
 * LSM tree in its shape. Check `CompactionListner` for more details.
 */
void WaitForCompactions(DB *db);

/*
 * The compactions can run in background even after the workload is completely
 * executed so, we have to wait for them to complete. Compaction Listener gets
 * notified by the rocksdb API for every compaction that just finishes off.
 * After every compaction we check, if more compactions are required with
 * `WaitForCompaction` function, if not then it signals to close the db
 */
class CompactionsListner : public EventListener {
public:
  explicit CompactionsListner() {}

  void OnCompactionCompleted(DB *db, const CompactionJobInfo &ci) override {
    std::lock_guard<std::mutex> lock(mtx);
    uint64_t num_running_compactions;
    uint64_t pending_compaction_bytes;
    uint64_t num_pending_compactions;
    db->GetIntProperty("rocksdb.num-running-compactions",
                       &num_running_compactions);
    db->GetIntProperty("rocksdb.estimate-pending-compaction-bytes",
                       &pending_compaction_bytes);
    db->GetIntProperty("rocksdb.compaction-pending", &num_pending_compactions);
    if (num_running_compactions == 0 && pending_compaction_bytes == 0 &&
        num_pending_compactions == 0) {
      compaction_complete = true;
    }
    cv.notify_one();
  }
};

class RangeReduceFlushListner : public EventListener {
public:
  RangeReduceFlushListner()
      : useful_data_blocks_size_(0), useful_file_size_(0), useful_entries_(0),
        un_useful_data_blocks_size_(0), un_useful_file_size_(0),
        un_useful_entries_(0) {}

  void reset() {
    useful_data_blocks_size_ = 0;
    useful_file_size_ = 0;
    useful_entries_ = 0;
    un_useful_data_blocks_size_ = 0;
    un_useful_file_size_ = 0;
    un_useful_entries_ = 0;
  }

  void OnFlushCompleted(DB *db, const FlushJobInfo &flush_job_info) override {
    if (flush_job_info.flush_reason == FlushReason::kRangeFlush) {
      TableProperties tp = flush_job_info.table_properties;
      useful_file_size_ += tp.data_size + tp.index_size + tp.filter_size;
      useful_data_blocks_size_ += tp.data_size;
      useful_entries_ += tp.num_entries;
    } else if (flush_job_info.flush_reason == FlushReason::kPartialFlush) {
      TableProperties tp = flush_job_info.table_properties;
      un_useful_file_size_ += tp.data_size + tp.index_size + tp.filter_size;
      un_useful_data_blocks_size_ += tp.data_size;
      un_useful_entries_ += tp.num_entries;
    }
  }

  uint64_t useful_data_blocks_size_;
  uint64_t useful_file_size_;
  uint64_t useful_entries_;
  uint64_t un_useful_data_blocks_size_;
  uint64_t un_useful_file_size_;
  uint64_t un_useful_entries_;
};

#endif // EVENT_LISTNER_H_
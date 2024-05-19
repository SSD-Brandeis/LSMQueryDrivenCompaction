#include <rocksdb/db.h>
#include <rocksdb/iostats_context.h>
#include <rocksdb/options.h>
#include <rocksdb/perf_context.h>
#include <rocksdb/table.h>

#include <chrono>
#include <condition_variable>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>

#include "config_options.h"
#include "emu_environment.h"
#include "thread"

// #define PROFILE
// #define TIMER

std::string kDBPath = "./db_working_home";
std::mutex mtx;
std::condition_variable cv;
bool compaction_complete = false;

void printExperimentalSetup(EmuEnv* _env);

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

  void OnCompactionCompleted(DB* /*db*/,
                             const CompactionJobInfo& /*ci*/) override {
    std::lock_guard<std::mutex> lock(mtx);
    compaction_complete = true;
    cv.notify_one();
  }
};

/*
 * Wait for compactions that are running (or will run) to make the
 * LSM tree in its shape. Check `CompactionListner` for more details.
 */
void WaitForCompactions(DB* db) {
  std::unique_lock<std::mutex> lock(mtx);
  uint64_t num_running_compactions;
  uint64_t pending_compaction_bytes;
  uint64_t num_pending_compactions;

  while (!compaction_complete) {
    // Check if there are ongoing or pending compactions
    db->GetIntProperty("rocksdb.num-running-compactions",
                       &num_running_compactions);
    db->GetIntProperty("rocksdb.estimate-pending-compaction-bytes",
                       &pending_compaction_bytes);
    db->GetIntProperty("rocksdb.compaction-pending", &num_pending_compactions);
    if (num_running_compactions == 0 && pending_compaction_bytes == 0 &&
        num_pending_compactions == 0) {
      break;
    }
    cv.wait(lock);
  }
}

class PartialAndFullRangeFlushListner : public EventListener {
 public:
  PartialAndFullRangeFlushListner()
      : udata_bytes_written_(0),
        uestimated_total_bytes_written_(0),
        uentries_count_(0),
        undata_bytes_written_(0),
        unestimated_total_bytes_written_(0),
        unentries_count_(0) {}

  void reset() {
    // in-range files
    udata_bytes_written_ = 0;
    uestimated_total_bytes_written_ = 0;
    uentries_count_ = 0;
    // Partial files
    undata_bytes_written_ = 0;
    unestimated_total_bytes_written_ = 0;
    unentries_count_ = 0;
  }

  uint64_t udata_bytes_written() { return udata_bytes_written_; }
  uint64_t utotal_bytes_written() { return uestimated_total_bytes_written_; }
  uint64_t uentries_count() { return uentries_count_; }
  uint64_t undata_bytes_written() { return undata_bytes_written_; }
  uint64_t untotal_bytes_written() { return unestimated_total_bytes_written_; }
  uint64_t unentries_count() { return unentries_count_; }

  void OnFlushCompleted(DB* /*db*/,
                        const FlushJobInfo& flush_job_info) override {
    if (flush_job_info.flush_reason == FlushReason::kRangeFlush) {
      TableProperties tp = flush_job_info.table_properties;
      uestimated_total_bytes_written_ +=
          tp.data_size + tp.index_size + tp.filter_size;
      udata_bytes_written_ += tp.data_size;
      uentries_count_ += tp.num_entries;
    } else if (flush_job_info.flush_reason == FlushReason::kPartialFlush) {
      TableProperties tp = flush_job_info.table_properties;
      unestimated_total_bytes_written_ +=
          tp.data_size + tp.index_size + tp.filter_size;
      undata_bytes_written_ += tp.data_size;
      unentries_count_ += tp.num_entries;
    }
  }

 private:
  // useful (in-range) bytes and entries
  uint64_t udata_bytes_written_;
  uint64_t uestimated_total_bytes_written_;
  uint64_t uentries_count_;
  // partial un-useful bytes and entries
  uint64_t undata_bytes_written_;
  uint64_t unestimated_total_bytes_written_;
  uint64_t unentries_count_;
};

// class FileReadListner : public EventListener {
//   public:
//     FileReadListner(DB* db) : total_bytes_read_(0), db_(db) {}

//   void reset() {
//     total_bytes_read_ = 0;
//   }

//   uint64_t total_bytes_read() {
//     return total_bytes_read_;
//   }

//   void OnFileReadFinish(const FileOperationInfo& file_op_info) override {
//     total_bytes_read_ += file_op_info.length;
//   }

//   bool ShouldBeNotifiedOnFileIO() override {
//     return ;
//   }

//   private:
//     DB* db_;
//     uint64_t total_bytes_read_;
// };

int runWorkload(EmuEnv* _env) {
  DB* db;
  Options options;
  WriteOptions w_options;
  ReadOptions r_options;
  BlockBasedTableOptions table_options;
  FlushOptions f_options;

  configOptions(_env, &options, &table_options, &w_options, &r_options,
                &f_options);

  r_options.range_query_options->initiate();

  if (_env->destroy_database) {
    DestroyDB(kDBPath, options);
    // std::cout << "Destroying database ..." << std::endl;
  }

  // options.info_log_level = InfoLogLevel::DEBUG_LEVEL;
  std::shared_ptr<CompactionsListner> compaction_listener =
      std::make_shared<CompactionsListner>();
  std::shared_ptr<PartialAndFullRangeFlushListner>
      partial_range_flush_listener =
          std::make_shared<PartialAndFullRangeFlushListner>();
  options.listeners.emplace_back(compaction_listener);
  options.listeners.emplace_back(partial_range_flush_listener);

  printExperimentalSetup(_env);  // !YBS-sep07-XX!
  // std::cout << "Maximum #OpenFiles = " << options.max_open_files
  //           << std::endl;  // !YBS-sep07-XX!
  // std::cout << "Maximum #ThreadsUsedToOpenFiles = "
  //           << options.max_file_opening_threads << std::endl;  // !YBS-sep07-XX!

  Status s = DB::Open(options, kDBPath, &db);
  if (!s.ok()) std::cerr << s.ToString() << std::endl;
  assert(s.ok());

  // opening workload file for the first time
  bool lexico_valid = false;
  ifstream workload_file;
  workload_file.open("workload.txt");
  assert(workload_file);

  // doing a first pass to get the workload size
  uint32_t workload_size = 0;
  std::string line;
  while (std::getline(workload_file, line)) ++workload_size;
  workload_file.close();

#ifdef PROFILE
  // number of epochs to run the experiment
  int num_epochs = 1;
  int num_instructions_for_one_epoch =
      (_env->num_updates / num_epochs) + (_env->num_range_queries / num_epochs);
  int num_instructions_executed_for_one_epoch = 0;

  // Print the values of each property
  auto printProperty = [&](const std::string& propertyName) {
    std::string value;
    bool status = db->GetProperty(propertyName, &value);
    if (status) {
      std::cout << propertyName << ": " << value << std::endl;
    } else {
      std::cerr << "Error getting property " << propertyName << ": " << status
                << std::endl;
    }
  };
#endif  // PROFILE

  // Clearing the system cache
  if (_env->clear_system_cache) {
    // std::cout << "Clearing system cache ..." << std::endl;
    // std::cout << system("sudo sh -c 'echo 3 >/proc/sys/vm/drop_caches'")
    //           << std::endl;
  }
  // START stat collection
  if (_env->enable_rocksdb_perf_iostat == 1) {
    // begin perf/iostat code
    rocksdb::SetPerfLevel(
        rocksdb::PerfLevel::kEnableTimeAndCPUTimeExceptForMutex);
    rocksdb::get_perf_context()->Reset();
    rocksdb::get_perf_context()->ClearPerLevelPerfContext();
    rocksdb::get_perf_context()->EnablePerLevelPerfContext();
    rocksdb::get_iostats_context()->Reset();
    // end perf/iostat code
  }

  // re-opening workload file to execute workload
  workload_file.open("workload.txt");
  assert(workload_file);

  Iterator* it = db->NewIterator(r_options);  // for range reads
  uint32_t counter = 0;                       // for progress bar

#ifdef TIMER
  unsigned long operations_execution_time = 0;
  unsigned long workload_execution_time = 0;
  unsigned long all_inserts_time = 0;
  unsigned long all_updates_time = 0;
  unsigned long all_range_queries_time = 0;
  std::chrono::_V2::system_clock::time_point refresh_time;
  unsigned long refresh_duration;
  unsigned long reset_duration = 0;
  unsigned long actual_range_time = 0;

  unsigned long inserts_time_for_one_epoch = 0;
  unsigned long updates_time_for_one_epoch = 0;
  unsigned long range_queries_time_for_one_epoch = 0;

  auto workload_start = std::chrono::high_resolution_clock::now();
  std::vector<
      std::tuple<unsigned long /*total execution time for RQ*/,
                 unsigned long /*useful data bytes flushed to level*/,
                 unsigned long /*useful total bytes (data + index + filter)
                                  flushed to level*/
                 ,
                 unsigned long /*useful entries count flushed to level*/,
                 unsigned long /*total entries read for RQ*/,
                 unsigned long /*un-useful data bytes flushed to level*/,
                 unsigned long /*un-useful total bytes (data + index + filter)
                                  flushed to level*/
                 ,
                 unsigned long /*un-useful entries count flushed to level*/,
                 unsigned long /*refresh time for range query*/,
                 unsigned long /*reset time for range query*/,
                 unsigned long /*actual range query time*/>>
      range_queries_;
#endif  // TIMER

  while (!workload_file.eof()) {
    char instruction;
    long key, start_key, end_key;
    string value;

    std::time_t end_time;

    workload_file >> instruction;
    _env->current_op = instruction;  // !YBS-sep18-XX!
    switch (instruction) {
      case 'I':  // insert
        workload_file >> key >> value;

        {
#ifdef TIMER
          auto start = std::chrono::high_resolution_clock::now();
#endif  // TIMER
          s = db->Put(w_options, to_string(key), value);

#ifdef TIMER
          auto stop = std::chrono::high_resolution_clock::now();
          auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
              stop - start);
          operations_execution_time += duration.count();
          all_inserts_time += duration.count();
          inserts_time_for_one_epoch += duration.count();
#endif  // TIMER
        }

        if (!s.ok()) std::cerr << s.ToString() << std::endl;
        assert(s.ok());
        counter++;
        break;

      case 'U':  // update
        workload_file >> key >> value;

        {
#ifdef TIMER
          auto start = std::chrono::high_resolution_clock::now();
#endif  // TIMER

          s = db->Put(w_options, to_string(key), value);

#ifdef TIMER
          auto stop = std::chrono::high_resolution_clock::now();
          auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
              stop - start);
          operations_execution_time += duration.count();
          all_updates_time += duration.count();
          updates_time_for_one_epoch += duration.count();
#endif  // TIMER
        }

        if (!s.ok()) std::cerr << s.ToString() << std::endl;
        assert(s.ok());
        counter++;
#ifdef PROFILE
        num_instructions_executed_for_one_epoch++;
#endif  // PROFILE
        break;

      case 'D':  // point delete
        workload_file >> key;

        {
#ifdef TIMER
          auto start = std::chrono::high_resolution_clock::now();
#endif  // TIMER

          s = db->Delete(w_options, to_string(key));

#ifdef TIMER
          auto stop = std::chrono::high_resolution_clock::now();
          auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
              stop - start);
          operations_execution_time += duration.count();
#endif  // TIMER
        }

        assert(s.ok());
        counter++;
        break;

      case 'Q':  // probe: point query
        workload_file >> key;

        {
#ifdef TIMER
          auto start = std::chrono::high_resolution_clock::now();
#endif  // TIMER

          s = db->Get(r_options, to_string(key), &value);

#ifdef TIMER
          auto stop = std::chrono::high_resolution_clock::now();
          auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
              stop - start);
          operations_execution_time += duration.count();
#endif  // TIMER
        }

        counter++;
        break;

      case 'S':  // scan: range query
        workload_file >> start_key >> end_key;
        lexico_valid = to_string(start_key).compare(to_string(end_key)) < 0;

        {
          uint64_t entries_count_read = 0;
          uint64_t entries_count_skipped = 0;
          uint64_t entries_read_to_compact = 0;
          uint64_t ideal_entries_count = 0;
          {
#ifdef PROFILE
            ColumnFamilyMetaData metadata;
            db->GetColumnFamilyMetaData(&metadata);
            std::stringstream cfd_details;
            std::stringstream all_level_details;
            unsigned long long total_entries_in_cfd = 0;

            // Print column family metadata
            cfd_details << "Column Family Name: " << metadata.name
                        << ", Size: " << metadata.size
                        << " bytes, Files Count: " << metadata.file_count;

            // Print metadata for each level
            for (const auto& level : metadata.levels) {
              std::stringstream level_details;
              level_details << "\tLevel: " << level.level
                            << ", Size: " << level.size
                            << " bytes, Files Count: " << level.files.size();

              unsigned long long total_entries_in_one_level = 0;
              std::stringstream level_sst_file_details;

              // Print metadata for each file in the level
              for (const auto& file : level.files) {
                total_entries_in_one_level += file.num_entries;
                level_sst_file_details << "[#" << file.file_number << ":"
                                       << file.size << " (" << file.smallestkey
                                       << ", " << file.largestkey << ") "
                                       << file.num_entries << "], ";
              }
              total_entries_in_cfd += total_entries_in_one_level;
              level_details << ", Entries Count: " << total_entries_in_one_level
                            << "\n\t\t";
              all_level_details << level_details.str()
                                << level_sst_file_details.str() << std::endl;
            }

            std::cout << cfd_details.str()
                      << ", Entries Count: " << total_entries_in_cfd
                      << ", Invalid Entries Count: "
                      << total_entries_in_cfd - _env->num_inserts << std::endl
                      << all_level_details.str() << std::endl;

#endif  // PROFILE
          }

  // {
  //   std::cout << "\nwaiting for compactions to finish ..." << std::endl;
  //   std::vector<std::string> live_files;
  //   uint64_t manifest_size;
  //   db->GetLiveFiles(live_files, &manifest_size, true /*flush_memtable*/);
  //   WaitForCompactions(db);
  // }

#ifdef TIMER
          auto start = std::chrono::high_resolution_clock::now();
          // partial_range_flush_listener->reset();
#endif  // TIMER

          if (lexico_valid) {
            // std::cout << "\nrangeQuery startkey: " << start_key
            //           << " endkey: " << end_key << std::endl << std::flush;
            it->Refresh(to_string(start_key), to_string(end_key),
                        entries_count_read,
                        _env->enable_range_query_compaction);
          }
#ifdef TIMER
          refresh_time = std::chrono::high_resolution_clock::now();
          refresh_duration =
              std::chrono::duration_cast<std::chrono::nanoseconds>(
                  refresh_time - start)
                  .count();
          std::cout << "refreshTime: " << refresh_duration << std::endl << std::flush;
#endif  // TIMER

          assert(it->status().ok());
          for (it->Seek(to_string(start_key)); it->Valid(); it->Next()) {
            if (it->key().ToString() >= to_string(end_key)) {
              break;
            }
            ideal_entries_count++;
          }

          if (!it->status().ok()) {
            std::cerr << it->status().ToString() << std::endl << std::flush;
          }

#ifdef TIMER
          r_options.range_query_options->count_of_total_invalid = (r_options.range_query_options->count_of_entries - ideal_entries_count);
          // r_options.range_query_options->count_of_entries_removed = r_options.range_query_options->count_of_entries_to_compact - r_options.range_query_options->count_of_entries_compacted;
          auto reset_start = std::chrono::high_resolution_clock::now();
          std::cout << "entriesCount: " << r_options.range_query_options->count_of_entries << std::endl << std::flush;
          std::cout << "idealEntriesCount: " << ideal_entries_count << std::endl << std::flush;
          std::cout << "invalidEntriesCount: " << r_options.range_query_options->count_of_total_invalid << std::endl << std::flush;
          // std::cout << "entriesToCompactCount: " << r_options.range_query_options->count_of_entries_to_compact << std::endl << std::flush;
          // std::cout << "entriesCompactedCount: " << r_options.range_query_options->count_of_entries_compacted << std::endl << std::flush;
          // std::cout << "entriesRemoved: " << r_options.range_query_options->count_of_entries_removed << std::endl << std::flush;
          // std::cout << "extraEntriesWritten: " << r_options.range_query_options->count_of_extra_write_for_partial << std::endl << std::flush;
#endif  // TIMER
          // if (_env->enable_range_query_compaction && lexico_valid) {
            it->Reset(entries_count_skipped, entries_read_to_compact);
          // }
#ifdef TIMER
          auto reset_end = std::chrono::high_resolution_clock::now();
          actual_range_time =
              std::chrono::duration_cast<std::chrono::nanoseconds>(reset_start -
                                                                   refresh_time)
                  .count();
          reset_duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
                               reset_end - reset_start)
                               .count();
          std::cout << "actualTime: " << actual_range_time << std::endl << std::flush;
          std::cout << "resetTime: " << reset_duration << std::endl << std::flush;
#endif  // TIMER

#ifdef TIMER
          auto stop = std::chrono::high_resolution_clock::now();
          auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
              stop - start);
          std::cout << "totalTime: " << duration.count() << std::endl << std::flush;
          range_queries_time_for_one_epoch += duration.count();
          operations_execution_time += duration.count();
          all_range_queries_time += duration.count();
          range_queries_.emplace_back(std::make_tuple(
              duration.count(),
              partial_range_flush_listener->udata_bytes_written(),
              partial_range_flush_listener->utotal_bytes_written(),
              partial_range_flush_listener->uentries_count(),
              entries_count_read,
              partial_range_flush_listener->undata_bytes_written(),
              partial_range_flush_listener->untotal_bytes_written(),
              partial_range_flush_listener->unentries_count(), refresh_duration,
              reset_duration, actual_range_time));
          partial_range_flush_listener->reset();
#endif  // TIMER

          {
#ifdef PROFILE
            ColumnFamilyMetaData metadata;
            db->GetColumnFamilyMetaData(&metadata);
            std::stringstream cfd_details;
            std::stringstream all_level_details;
            unsigned long long total_entries_in_cfd = 0;

            // Print column family metadata
            cfd_details << "Column Family Name: " << metadata.name
                        << ", Size: " << metadata.size
                        << " bytes, Files Count: " << metadata.file_count;

            // Print metadata for each level
            for (const auto& level : metadata.levels) {
              std::stringstream level_details;
              level_details << "\tLevel: " << level.level
                            << ", Size: " << level.size
                            << " bytes, Files Count: " << level.files.size();

              unsigned long long total_entries_in_one_level = 0;
              std::stringstream level_sst_file_details;

              // Print metadata for each file in the level
              for (const auto& file : level.files) {
                total_entries_in_one_level += file.num_entries;
                level_sst_file_details << "[#" << file.file_number << ":"
                                       << file.size << " (" << file.smallestkey
                                       << ", " << file.largestkey << ") "
                                       << file.num_entries << "], ";
              }
              total_entries_in_cfd += total_entries_in_one_level;
              level_details << ", Entries Count: " << total_entries_in_one_level
                            << "\n\t\t";
              all_level_details << level_details.str()
                                << level_sst_file_details.str() << std::endl;
            }

            std::cout << cfd_details.str()
                      << ", Entries Count: " << total_entries_in_cfd
                      << ", Invalid Entries Count: "
                      << total_entries_in_cfd - _env->num_inserts << std::endl
                      << all_level_details.str() << std::endl;
#endif  // PROFILE
          }
        }

#ifdef PROFILE
        num_instructions_executed_for_one_epoch++;
#endif  // PROFILE
        counter++;
        break;

      default:
        std::cerr << "ERROR: Case match NOT found !!" << std::endl;
        break;
    }

#ifdef PROFILE
    if (counter >= _env->num_inserts) {
      if (counter == _env->num_inserts) {
        std::cout << "=====================" << std::endl;
        std::cout << "Inserts are completed ..." << std::endl;

        {
          std::vector<std::string> live_files;
          uint64_t manifest_size;
          db->GetLiveFiles(live_files, &manifest_size, true /*flush_memtable*/);
          WaitForCompactions(db);
        }

        //  "rocksdb.obsolete-sst-files-size" - returns total size (bytes) of
        //  all
        //      SST files that became obsolete but have not yet been deleted or
        //      scheduled for deletion. SST files can end up in this state when
        //      using `DisableFileDeletions()`, for example.
        //
        //      N.B. Unlike the other "*SstFilesSize" properties, this property
        //      includes SST files that originated in any of the DB's CFs.
        printProperty("rocksdb.obsolete-sst-files-size");
        //  "rocksdb.live-sst-files-size" - returns total size (bytes) of all
        //  SST
        //      files belong to the CF's current version.
        printProperty("rocksdb.live-sst-files-size");
        //  "rocksdb.total-sst-files-size" - returns total size (bytes) of all
        //  SST
        //      files belonging to any of the CF's versions.
        //  WARNING: may slow down online queries if there are too many files.
        printProperty("rocksdb.total-sst-files-size");

        // //  "rocksdb.estimate-live-data-size" - returns an estimate of the
        // //  amount of
        // //      live data in bytes. For BlobDB, it also includes the exact
        // value
        // //      of live bytes in the blob files of the version.
        // printProperty("rocksdb.estimate-live-data-size");
        // //  "rocksdb.estimate-table-readers-mem" - returns estimated memory
        // used
        // //  for
        // //      reading SST tables, excluding memory used in block cache
        // (e.g.,
        // //      filter and index blocks).

        // printProperty("rocksdb.estimate-table-readers-mem");
        //  "rocksdb.estimate-num-keys" - returns estimated number of total keys
        //  in
        //      the active and unflushed immutable memtables and storage.
        printProperty("rocksdb.estimate-num-keys");
        //  "rocksdb.num-entries-active-mem-table" - returns total number of
        //  entries
        //      in the active memtable.
        printProperty("rocksdb.num-entries-active-mem-table");
        //  "rocksdb.num-entries-imm-mem-tables" - returns total number of
        //  entries
        //      in the unflushed immutable memtables.
        printProperty("rocksdb.num-entries-imm-mem-tables");

        // //  "rocksdb.size-all-mem-tables" - returns approximate size of
        // active,
        // //      unflushed immutable, and pinned immutable memtables (bytes).
        // printProperty("rocksdb.size-all-mem-tables");
        // //  "rocksdb.cur-size-all-mem-tables" - returns approximate size of
        // //  active
        // //      and unflushed immutable memtables (bytes).
        // printProperty("rocksdb.cur-size-all-mem-tables");
        // //  "rocksdb.cur-size-active-mem-table" - returns approximate size of
        // //  active
        // //      memtable (bytes).
        // printProperty("rocksdb.cur-size-active-mem-table");
        // //  "rocksdb.levelstats" - returns multi-line string containing the
        // //  number
        // //      of files per level and total size of each level (MB).
        // printProperty("rocksdb.levelstats");
        // //  "rocksdb.sstables" - returns a multi-line string summarizing
        // current
        // //      SST files.
        // printProperty("rocksdb.sstables");
        // //  "rocksdb.stats" - returns a multi-line string containing the data
        // //      described by kCFStats followed by the data described by
        // kDBStats. printProperty("rocksdb.stats");

        std::cout << std::endl;

        ColumnFamilyMetaData metadata;
        db->GetColumnFamilyMetaData(&metadata);
        std::stringstream cfd_details;
        std::stringstream all_level_details;
        unsigned long long total_entries_in_cfd = 0;

        // Print column family metadata
        cfd_details << "Column Family Name: " << metadata.name
                    << ", Size: " << metadata.size
                    << " bytes, Files Count: " << metadata.file_count;

        // Print metadata for each level
        for (const auto& level : metadata.levels) {
          std::stringstream level_details;
          level_details << "\tLevel: " << level.level
                        << ", Size: " << level.size
                        << " bytes, Files Count: " << level.files.size();

          unsigned long long total_entries_in_one_level = 0;
          std::stringstream level_sst_file_details;

          // Print metadata for each file in the level
          for (const auto& file : level.files) {
            total_entries_in_one_level += file.num_entries;
            level_sst_file_details << "[#" << file.file_number << ":"
                                   << file.size << " (" << file.smallestkey
                                   << ", " << file.largestkey << ") "
                                   << file.num_entries << "], ";
          }
          total_entries_in_cfd += total_entries_in_one_level;
          level_details << ", Entries Count: " << total_entries_in_one_level
                        << "\n\t\t";
          all_level_details << level_details.str()
                            << level_sst_file_details.str() << std::endl;
        }

        std::cout << cfd_details.str()
                  << ", Entries Count: " << total_entries_in_cfd
                  << ", Invalid Entries Count: "
                  << total_entries_in_cfd - _env->num_inserts << std::endl
                  << all_level_details.str() << std::endl;

        std::cout << "Rocksdb Statistics: " << std::endl;
        std::cout << "rocksdb.compact.read.bytes: "
                  << options.statistics->getTickerCount(COMPACT_READ_BYTES)
                  << std::endl;
        std::cout << "rocksdb.compact.write.bytes: "
                  << options.statistics->getTickerCount(COMPACT_WRITE_BYTES)
                  << std::endl;
        std::cout << "rocksdb.flush.write.bytes: "
                  << options.statistics->getTickerCount(FLUSH_WRITE_BYTES)
                  << std::endl;
        std::cout << "rocksdb.partial.file.flush.count: "
                  << options.statistics->getTickerCount(
                         PARTIAL_FILE_FLUSH_COUNT)
                  << std::endl;
        std::cout << "rocksdb.partial.file.flush.bytes: "
                  << options.statistics->getTickerCount(
                         PARTIAL_FILE_FLUSH_BYTES)
                  << std::endl;
        std::cout << "rocksdb.full.file.flush.count: "
                  << options.statistics->getTickerCount(FULL_FILE_FLUSH_COUNT)
                  << std::endl;
        std::cout << "rocksdb.full.file.flush.bytes: "
                  << options.statistics->getTickerCount(FULL_FILE_FLUSH_BYTES)
                  << std::endl;
        std::cout << "rocksdb.compaction.times.micros: "
                  << options.statistics->getTickerCount(COMPACTION_TIME)
                  << std::endl;
        // std::cout << "rocksdb.bytes.read: "
        //           << options.statistics->getTickerCount(BYTES_READ)
        //           << std::endl;
        // std::cout << "rocksdb.bytes.written: "
        //           << options.statistics->getTickerCount(BYTES_WRITTEN)
        //           << std::endl;
        // std::cout << "rocksdb.db.iter.bytes.read: "
        //           << options.statistics->getTickerCount(ITER_BYTES_READ)
        //           << std::endl;
        // std::cout << "rocksdb.number.multiget.bytes.read: "
        //           <<
        //           options.statistics->getTickerCount(NUMBER_MULTIGET_BYTES_READ)
        //           << std::endl;

        std::cout << "Time spent in Inserts: " << inserts_time_for_one_epoch
                  << std::endl;
        std::cout << "Time spent in Updates: " << updates_time_for_one_epoch
                  << std::endl;
        std::cout << "Time spent in Range Queries: "
                  << range_queries_time_for_one_epoch << std::endl;
        inserts_time_for_one_epoch = 0;
        updates_time_for_one_epoch = 0;
        range_queries_time_for_one_epoch = 0;

      } else if (num_instructions_executed_for_one_epoch ==
                 num_instructions_for_one_epoch) {
        std::cout << "=====================" << std::endl;
        std::cout << "One Epoch done ... "
                  << num_instructions_executed_for_one_epoch << " instructions"
                  << std::endl;

        {
          std::vector<std::string> live_files;
          uint64_t manifest_size;
          db->GetLiveFiles(live_files, &manifest_size, true /*flush_memtable*/);
          WaitForCompactions(db);
        }

        printProperty("rocksdb.obsolete-sst-files-size");
        printProperty("rocksdb.live-sst-files-size");
        printProperty("rocksdb.total-sst-files-size");
        // printProperty("rocksdb.estimate-live-data-size");
        // printProperty("rocksdb.estimate-table-readers-mem");
        printProperty("rocksdb.estimate-num-keys");
        printProperty("rocksdb.num-entries-active-mem-table");
        printProperty("rocksdb.num-entries-imm-mem-tables");
        // printProperty("rocksdb.size-all-mem-tables");
        // printProperty("rocksdb.cur-size-all-mem-tables");
        // printProperty("rocksdb.cur-size-active-mem-table");
        // printProperty("rocksdb.levelstats");
        // printProperty("rocksdb.sstables");
        // printProperty("rocksdb.stats");

        std::cout << std::endl;

        ColumnFamilyMetaData metadata;
        db->GetColumnFamilyMetaData(&metadata);
        std::stringstream cfd_details;
        std::stringstream all_level_details;
        unsigned long long total_entries_in_cfd = 0;

        // Print column family metadata
        cfd_details << "Column Family Name: " << metadata.name
                    << ", Size: " << metadata.size
                    << " bytes, Files Count: " << metadata.file_count;

        // Print metadata for each level
        for (const auto& level : metadata.levels) {
          std::stringstream level_details;
          level_details << "\tLevel: " << level.level
                        << ", Size: " << level.size
                        << " bytes, Files Count: " << level.files.size();

          unsigned long long total_entries_in_one_level = 0;
          std::stringstream level_sst_file_details;

          // Print metadata for each file in the level
          for (const auto& file : level.files) {
            total_entries_in_one_level += file.num_entries;
            level_sst_file_details << "[#" << file.file_number << ":"
                                   << file.size << " (" << file.smallestkey
                                   << ", " << file.largestkey << ") "
                                   << file.num_entries << "], ";
          }
          total_entries_in_cfd += total_entries_in_one_level;
          level_details << ", Entries Count: " << total_entries_in_one_level
                        << "\n\t\t";
          all_level_details << level_details.str()
                            << level_sst_file_details.str() << std::endl;
        }

        std::cout << cfd_details.str()
                  << ", Entries Count: " << total_entries_in_cfd
                  << ", Invalid Entries Count: "
                  << total_entries_in_cfd - _env->num_inserts << std::endl
                  << all_level_details.str() << std::endl;

        std::cout << "Rocksdb Statistics: " << std::endl;
        std::cout << "rocksdb.compact.read.bytes: "
                  << options.statistics->getTickerCount(COMPACT_READ_BYTES)
                  << std::endl;
        std::cout << "rocksdb.compact.write.bytes: "
                  << options.statistics->getTickerCount(COMPACT_WRITE_BYTES)
                  << std::endl;
        std::cout << "rocksdb.flush.write.bytes: "
                  << options.statistics->getTickerCount(FLUSH_WRITE_BYTES)
                  << std::endl;
        std::cout << "rocksdb.partial.file.flush.count: "
                  << options.statistics->getTickerCount(
                         PARTIAL_FILE_FLUSH_COUNT)
                  << std::endl;
        std::cout << "rocksdb.partial.file.flush.bytes: "
                  << options.statistics->getTickerCount(
                         PARTIAL_FILE_FLUSH_BYTES)
                  << std::endl;
        std::cout << "rocksdb.full.file.flush.count: "
                  << options.statistics->getTickerCount(FULL_FILE_FLUSH_COUNT)
                  << std::endl;
        std::cout << "rocksdb.full.file.flush.bytes: "
                  << options.statistics->getTickerCount(FULL_FILE_FLUSH_BYTES)
                  << std::endl;
        std::cout << "rocksdb.compaction.times.micros: "
                  << options.statistics->getTickerCount(COMPACTION_TIME)
                  << std::endl;
        // std::cout << "rocksdb.bytes.read: "
        //           << options.statistics->getTickerCount(BYTES_READ)
        //           << std::endl;
        // std::cout << "rocksdb.bytes.written: "
        //           << options.statistics->getTickerCount(BYTES_WRITTEN)
        //           << std::endl;
        // std::cout << "rocksdb.db.iter.bytes.read: "
        //           << options.statistics->getTickerCount(ITER_BYTES_READ)
        //           << std::endl;
        // std::cout << "rocksdb.number.multiget.bytes.read: "
        //           <<
        //           options.statistics->getTickerCount(NUMBER_MULTIGET_BYTES_READ)
        //           << std::endl;

        std::cout << "Time spent in Inserts: " << inserts_time_for_one_epoch
                  << std::endl;
        std::cout << "Time spent in Updates: " << updates_time_for_one_epoch
                  << std::endl;
        std::cout << "Time spent in Range Queries: "
                  << range_queries_time_for_one_epoch << std::endl;
        inserts_time_for_one_epoch = 0;
        updates_time_for_one_epoch = 0;
        range_queries_time_for_one_epoch = 0;

        num_instructions_executed_for_one_epoch = 0;
      }
    }
#endif  // PROFILE
  }

  workload_file.close();

  {
    std::vector<std::string> live_files;
    uint64_t manifest_size;
    db->GetLiveFiles(live_files, &manifest_size, true /*flush_memtable*/);
    WaitForCompactions(db);
  }

#ifdef PROFILE
  std::cout << "=====================" << std::endl;
  std::cout << "Inserts epoch in last ..." << std::endl;
  printProperty("rocksdb.obsolete-sst-files-size");
  printProperty("rocksdb.live-sst-files-size");
  printProperty("rocksdb.total-sst-files-size");
  // printProperty("rocksdb.estimate-live-data-size");
  // printProperty("rocksdb.estimate-table-readers-mem");
  printProperty("rocksdb.estimate-num-keys");
  printProperty("rocksdb.num-entries-active-mem-table");
  printProperty("rocksdb.num-entries-imm-mem-tables");
  // printProperty("rocksdb.size-all-mem-tables");
  // printProperty("rocksdb.cur-size-all-mem-tables");
  // printProperty("rocksdb.cur-size-active-mem-table");
  // printProperty("rocksdb.levelstats");
  // printProperty("rocksdb.sstables");
  // printProperty("rocksdb.stats");

  std::cout << std::endl;

  ColumnFamilyMetaData metadata;
  db->GetColumnFamilyMetaData(&metadata);
  std::stringstream cfd_details;
  std::stringstream all_level_details;
  unsigned long long total_entries_in_cfd = 0;

  // Print column family metadata
  cfd_details << "Column Family Name: " << metadata.name
              << ", Size: " << metadata.size
              << " bytes, Files Count: " << metadata.file_count;

  // Print metadata for each level
  for (const auto& level : metadata.levels) {
    std::stringstream level_details;
    level_details << "\tLevel: " << level.level << ", Size: " << level.size
                  << " bytes, Files Count: " << level.files.size();

    unsigned long long total_entries_in_one_level = 0;
    std::stringstream level_sst_file_details;

    // Print metadata for each file in the level
    for (const auto& file : level.files) {
      total_entries_in_one_level += file.num_entries;
      level_sst_file_details << "[#" << file.file_number << ":" << file.size
                             << " (" << file.smallestkey << ", "
                             << file.largestkey << ") " << file.num_entries
                             << "], ";
    }
    total_entries_in_cfd += total_entries_in_one_level;
    level_details << ", Entries Count: " << total_entries_in_one_level
                  << "\n\t\t";
    all_level_details << level_details.str() << level_sst_file_details.str()
                      << std::endl;
  }

  std::cout << cfd_details.str() << ", Entries Count: " << total_entries_in_cfd
            << ", Invalid Entries Count: "
            << total_entries_in_cfd - _env->num_inserts << std::endl
            << all_level_details.str() << std::endl;

  std::cout << "Rocksdb Statistics: " << std::endl;
  std::cout << "rocksdb.compact.read.bytes: "
            << options.statistics->getTickerCount(COMPACT_READ_BYTES)
            << std::endl;
  std::cout << "rocksdb.compact.write.bytes: "
            << options.statistics->getTickerCount(COMPACT_WRITE_BYTES)
            << std::endl;
  std::cout << "rocksdb.flush.write.bytes: "
            << options.statistics->getTickerCount(FLUSH_WRITE_BYTES)
            << std::endl;
  std::cout << "rocksdb.partial.file.flush.count: "
            << options.statistics->getTickerCount(PARTIAL_FILE_FLUSH_COUNT)
            << std::endl;
  std::cout << "rocksdb.partial.file.flush.bytes: "
            << options.statistics->getTickerCount(PARTIAL_FILE_FLUSH_BYTES)
            << std::endl;
  std::cout << "rocksdb.full.file.flush.count: "
            << options.statistics->getTickerCount(FULL_FILE_FLUSH_COUNT)
            << std::endl;
  std::cout << "rocksdb.full.file.flush.bytes: "
            << options.statistics->getTickerCount(FULL_FILE_FLUSH_BYTES)
            << std::endl;
  std::cout << "rocksdb.compaction.times.micros: "
            << options.statistics->getTickerCount(COMPACTION_TIME) << std::endl;
  // std::cout << "rocksdb.bytes.read: "
  //           << options.statistics->getTickerCount(BYTES_READ)
  //           << std::endl;
  // std::cout << "rocksdb.bytes.written: "
  //           << options.statistics->getTickerCount(BYTES_WRITTEN)
  //           << std::endl;
  // std::cout << "rocksdb.db.iter.bytes.read: "
  //           << options.statistics->getTickerCount(ITER_BYTES_READ)
  //           << std::endl;
  // std::cout << "rocksdb.number.multiget.bytes.read: "
  //           << options.statistics->getTickerCount(NUMBER_MULTIGET_BYTES_READ)
  //           << std::endl;

  std::cout << "Time spent in Inserts: " << inserts_time_for_one_epoch
            << std::endl;
  std::cout << "Time spent in Updates: " << updates_time_for_one_epoch
            << std::endl;
  std::cout << "Time spent in Range Queries: "
            << range_queries_time_for_one_epoch << std::endl;
  inserts_time_for_one_epoch = 0;
  updates_time_for_one_epoch = 0;
  range_queries_time_for_one_epoch = 0;

#endif  // PROFILE

  {
#ifdef TIMER
    auto workload_stop = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
        workload_stop - workload_start);
    workload_execution_time += duration.count();
#endif  // TIMER
  }

  if (!s.ok()) std::cerr << s.ToString() << std::endl;
  assert(s.ok());
  s = db->Close();
  if (!s.ok()) std::cerr << s.ToString() << std::endl;
  assert(s.ok());

  std::cout << "End of experiment - TEST !!\n";

#ifdef TIMER
  std::cout << "=====================" << std::endl;
  std::cout << "Workload Execution Time: " << workload_execution_time
            << std::endl;
  std::cout << "Operations Execution Time: " << operations_execution_time
            << std::endl;
  std::cout << "All Inserts Time: " << all_inserts_time << std::endl;
  std::cout << "All Updates Time: " << all_updates_time << std::endl;
  std::cout << "All Range Queries Time: " << all_range_queries_time
            << std::endl;

  std::cout << std::endl;

  std::cout << "Rocksdb Statistics: " << std::endl;
  std::cout << "rocksdb.compact.read.bytes: "
            << options.statistics->getTickerCount(COMPACT_READ_BYTES)
            << std::endl;
  std::cout << "rocksdb.compact.write.bytes: "
            << options.statistics->getTickerCount(COMPACT_WRITE_BYTES)
            << std::endl;
  std::cout << "rocksdb.flush.write.bytes: "
            << options.statistics->getTickerCount(FLUSH_WRITE_BYTES)
            << std::endl;
  std::cout << "rocksdb.partial.file.flush.count: "
            << options.statistics->getTickerCount(PARTIAL_FILE_FLUSH_COUNT)
            << std::endl;
  std::cout << "rocksdb.partial.file.flush.bytes: "
            << options.statistics->getTickerCount(PARTIAL_FILE_FLUSH_BYTES)
            << std::endl;
  std::cout << "rocksdb.full.file.flush.count: "
            << options.statistics->getTickerCount(FULL_FILE_FLUSH_COUNT)
            << std::endl;
  std::cout << "rocksdb.full.file.flush.bytes: "
            << options.statistics->getTickerCount(FULL_FILE_FLUSH_BYTES)
            << std::endl;
  std::cout << "rocksdb.compaction.times.micros: "
            << options.statistics->getTickerCount(COMPACTION_TIME) << std::endl;

  // Open a CSV file to write
  std::ofstream rq_time_file("range_queries.csv");

  // Write header
  rq_time_file
      << "RQ Number, RQ Total Time, Data uBytes Written Back, Total "
         "uBytes Written Back, uEntries Count Written Back, Total "
         "Entries Read, Data unBytes Written Back, Total unBytes "
         "Written Back, unEntries Count Written Back, RQ Refresh Time, "
         "RQ Reset Time, Actual RQ Time"
      << std::endl;

  // Write data from range_queries_time to CSV
  for (int i = 0; i < range_queries_.size(); ++i) {
    std::tuple<unsigned long, unsigned long, unsigned long, unsigned long,
               unsigned long, unsigned long, unsigned long, unsigned long,
               unsigned long, unsigned long, unsigned long>
        rq = range_queries_[i];
    rq_time_file << i + 1 << ", " << std::get<0>(rq) << ", " << std::get<1>(rq)
                 << ", " << std::get<2>(rq) << ", " << std::get<3>(rq) << ", "
                 << std::get<4>(rq) << ", " << std::get<5>(rq) << ", "
                 << std::get<6>(rq) << ", " << std::get<7>(rq) << ", "
                 << std::get<8>(rq) << ", " << std::get<9>(rq) << ", "
                 << std::get<10>(rq) << std::endl;
  }

  // Close the file
  rq_time_file.close();
#endif  // TIMER

  if (_env->enable_rocksdb_perf_iostat == 1) {
    rocksdb::SetPerfLevel(rocksdb::PerfLevel::kDisable);
    std::cout << "RocksDB Perf Context : " << std::endl;
    std::cout << rocksdb::get_perf_context()->ToString() << std::endl;
    std::cout << "RocksDB Iostats Context : " << std::endl;
    std::cout << rocksdb::get_iostats_context()->ToString() << std::endl;
    // END ROCKS PROFILE
    // Print Full RocksDB stats
    std::cout << "----------------------------------------" << std::endl;
    // std::string tr_mem;
    // db->GetProperty("rocksdb.estimate-table-readers-mem", &tr_mem);
    // // Print Full RocksDB stats
    // std::cout << "RocksDB Estimated Table Readers Memory (index, filters) : "
    // << tr_mem << std::endl;
  }

  return 1;
}

void printExperimentalSetup(EmuEnv* _env) {
  int l = 10;

  std::cout << std::setfill(' ') << std::setw(l)
            << "cmpt_sty"  // !YBS-sep07-XX!
            << std::setfill(' ') << std::setw(l) << "cmpt_pri"
            << std::setfill(' ') << std::setw(4) << "T" << std::setfill(' ')
            << std::setw(l) << "P" << std::setfill(' ') << std::setw(l) << "B"
            << std::setfill(' ') << std::setw(l) << "E" << std::setfill(' ')
            << std::setw(l)
            << "M"
            // << std::setfill(' ') << std::setw(l)  << "f"
            << std::setfill(' ') << std::setw(l) << "file_size"
            << std::setfill(' ') << std::setw(l) << "L1_size"
            << std::setfill(' ') << std::setw(l) << "blk_cch"  // !YBS-sep09-XX!
            << std::setfill(' ') << std::setw(l) << "BPK"
            << "\n";
  std::cout << std::setfill(' ') << std::setw(l)
            << _env->compaction_style;  // !YBS-sep07-XX!
  std::cout << std::setfill(' ') << std::setw(l) << _env->compaction_pri;
  std::cout << std::setfill(' ') << std::setw(4) << _env->size_ratio;
  std::cout << std::setfill(' ') << std::setw(l) << _env->buffer_size_in_pages;
  std::cout << std::setfill(' ') << std::setw(l) << _env->entries_per_page;
  std::cout << std::setfill(' ') << std::setw(l) << _env->entry_size;
  std::cout << std::setfill(' ') << std::setw(l) << _env->buffer_size;
  // std::cout << std::setfill(' ') << std::setw(l) <<
  // _env->file_to_memtable_size_ratio;
  std::cout << std::setfill(' ') << std::setw(l) << _env->file_size;
  std::cout << std::setfill(' ') << std::setw(l)
            << _env->max_bytes_for_level_base;
  std::cout << std::setfill(' ') << std::setw(l)
            << _env->block_cache;  // !YBS-sep09-XX!
  std::cout << std::setfill(' ') << std::setw(l) << _env->bits_per_key;
  // std::cout << std::setfill(' ') << std::setw(l) <<
  // _env->delete_persistence_latency; // !YBS-feb15-XXI!

  std::cout << std::endl;
}
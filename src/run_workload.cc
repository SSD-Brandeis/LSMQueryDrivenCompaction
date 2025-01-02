#include "run_workload.h"

#include <chrono>
#include <fstream>

#include "config_options.h"
#include "utils.h"

std::string kDBPath = "./db";
std::string buffer_file = "workload.log";
std::string rqstats_file = "range_queries.csv";

int runWorkload(DBEnv *env) {
  DB *db;
  Options options;
  WriteOptions write_options;
  ReadOptions read_options;
  BlockBasedTableOptions table_options;
  FlushOptions flush_options;

  configOptions(env, &options, &table_options, &write_options, &read_options,
                &flush_options);

  // Add custom listners
  std::shared_ptr<CompactionsListner> compaction_listener =
      std::make_shared<CompactionsListner>();
  std::shared_ptr<RangeReduceFlushListner> range_reduce_listener =
      std::make_shared<RangeReduceFlushListner>();
  options.listeners.emplace_back(compaction_listener);
  options.listeners.emplace_back(range_reduce_listener);

  if (env->IsDestroyDatabaseEnabled()) {
    DestroyDB(kDBPath, options);
    std::cout << "Destroying database ... done" << std::endl;
  }

  Buffer *buffer = new Buffer(buffer_file);
  PrintExperimentalSetup(env, buffer);

  Status s = DB::Open(options, kDBPath, &db);
  if (!s.ok())
    std::cerr << s.ToString() << std::endl;
  assert(s.ok());
  Iterator *it = db->NewIterator(read_options);

#ifdef DOSTO
  if (env->debugging) {
    tree->SetDebugMode(env->debugging);
    tree->PrintFluidLSM(db);
  }
#endif // DOSTO

  // Clearing the system cache
  if (env->clear_system_cache) {
#ifdef __linux__
    std::cout << "Clearing system cache ...";
    std::cout << system("sudo sh -c 'echo 3 >/proc/sys/vm/drop_caches'")
              << "done" << std::endl;
#endif
  }

  std::ifstream workload_file;
  workload_file.open("workload.txt");
  assert(workload_file);

  size_t total_operations = 0;
  if (env->IsShowProgressEnabled()) {
    std::string line;
    while (std::getline(workload_file, line)) {
      ++total_operations;
    }
  }

  workload_file.clear();
  workload_file.seekg(0, std::ios::beg);

#ifdef PROFILE
  unsigned long num_epochs = 11;
  unsigned long op_in_epoch =
      (env->num_updates / num_epochs) + (env->num_range_queries / num_epochs);
#endif // PROFILE

#ifdef TIMER
  unsigned long inserts_exec_time = 0, updates_exec_time = 0, pq_exec_time = 0,
                pdelete_exec_time = 0, rq_exec_time = 0;
  Buffer rqstats(rqstats_file);
  rqstats // adds a header
      << "RQ Number, RQ Total Time, Data uBytes Written Back, Total "
         "uBytes Written Back, uEntries Count Written Back, Total "
         "Entries Read, Data unBytes Written Back, Total unBytes "
         "Written Back, unEntries Count Written Back, Skipped Entries Count, "
         "Entries Qualified For Compaction Count, RQ Refresh Time, "
         "RQ Reset Time, Actual RQ Time"
      << std::endl;
  unsigned long rqnumber = 0;
#endif // TIMER
  auto exec_start = std::chrono::high_resolution_clock::now();

  std::string line;
  unsigned long ith_op = 0;
  while (std::getline(workload_file, line)) {
    if (line.empty())
      break;
    bool is_last_line = (workload_file.peek() == EOF);

    std::istringstream stream(line);
    char operation;
    stream >> operation;

    switch (operation) {
      // [Insert]
    case 'I': {
      std::string key, value;
      stream >> key >> value;
#ifdef TIMER
      auto start = std::chrono::high_resolution_clock::now();
#endif // TIMER
      s = db->Put(write_options, key, value);
#ifdef TIMER
      auto stop = std::chrono::high_resolution_clock::now();
      inserts_exec_time +=
          std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start)
              .count();
#endif // TIMER
      break;
    }
      // [Update]
    case 'U': {
      std::string key, value;
      stream >> key >> value;
#ifdef TIMER
      auto start = std::chrono::high_resolution_clock::now();
#endif // TIMER
      s = db->Put(write_options, key, value);
#ifdef TIMER
      auto stop = std::chrono::high_resolution_clock::now();
      updates_exec_time +=
          std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start)
              .count();
#endif // TIMER
      break;
    }
      // [PointDelete]
    case 'D': {
      std::string key;
      stream >> key;
#ifdef TIMER
      auto start = std::chrono::high_resolution_clock::now();
#endif // TIMER
      s = db->Delete(write_options, key);
#ifdef TIMER
      auto stop = std::chrono::high_resolution_clock::now();
      pdelete_exec_time +=
          std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start)
              .count();
#endif // TIMER
      break;
    }
      // [ProbePointQuery]
    case 'Q': {
      std::string key, value;
      stream >> key;
#ifdef TIMER
      auto start = std::chrono::high_resolution_clock::now();
#endif // TIMER
      s = db->Get(read_options, key, &value);
#ifdef TIMER
      auto stop = std::chrono::high_resolution_clock::now();
      pq_exec_time +=
          std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start)
              .count();
#endif // TIMER
      break;
    }
      // [ScanRangeQuery]
    case 'S': {
      std::string start_key, end_key;
      stream >> start_key >> end_key;

      uint64_t keys_returned = 0, keys_skipped = 0, keys_compacted = 0, keys_read = 0;
#ifdef TIMER
      auto start = std::chrono::high_resolution_clock::now();
      range_reduce_listener->reset();
#endif // TIMER

      it->Refresh(start_key, end_key, keys_read,
                  env->enable_range_query_compaction);
#ifdef TIMER
      auto refresh_time = std::chrono::high_resolution_clock::now();
      auto refresh_duration =
          std::chrono::duration_cast<std::chrono::nanoseconds>(refresh_time -
                                                               start)
              .count();
#endif // TIMER
      assert(it->status().ok());
      for (it->Seek(start_key); it->Valid(); it->Next()) {
        if (it->key().ToString() >= end_key) {
          break;
        }
        keys_returned++;
      }
      if (!it->status().ok()) {
        (*buffer) << it->status().ToString() << std::endl << std::flush;
      }
#ifdef TIMER
      read_options.range_query_stat->count_of_total_invalid =
          (read_options.range_query_stat->count_of_entries - keys_returned);
      auto reset_start = std::chrono::high_resolution_clock::now();
      auto total_entries_read = read_options.range_query_stat->count_of_entries;
#endif // TIMER
      it->Reset(keys_skipped, keys_compacted);
#ifdef TIMER
      auto reset_end = std::chrono::high_resolution_clock::now();
      auto actual_range_time =
          std::chrono::duration_cast<std::chrono::nanoseconds>(reset_start -
                                                               refresh_time)
              .count();
      auto reset_duration =
          std::chrono::duration_cast<std::chrono::nanoseconds>(reset_end -
                                                               reset_start)
              .count();
      auto stop = std::chrono::high_resolution_clock::now();
      auto duration =
          std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start);
      rq_exec_time += duration.count();
      rqstats << ++rqnumber << ", " << duration.count() << ", "
              << range_reduce_listener->useful_data_blocks_size_ << ", "
              << range_reduce_listener->useful_file_size_ << ", "
              << range_reduce_listener->useful_entries_ << ", "
              << total_entries_read << ", "
              << range_reduce_listener->un_useful_data_blocks_size_ << ", "
              << range_reduce_listener->un_useful_file_size_ << ", "
              << range_reduce_listener->un_useful_entries_ << ", "
              << keys_skipped << keys_compacted << ", " << refresh_duration
              << ", " << reset_duration << ", " << actual_range_time
              << std::endl;
      range_reduce_listener->reset();
#endif // TIMER
      break;
    }
    default:
      (*buffer) << "ERROR: Case match NOT found !!" << std::endl;
      break;
    }

    ith_op += 1;
    UpdateProgressBar(env, ith_op, total_operations);
#ifdef PROFILE
    if (ith_op == env->num_inserts) {
      (*buffer) << "=====================" << std::endl;
      (*buffer) << "Inserts are completed ..." << std::endl;
      LogTreeState(db, buffer);
      LogRocksDBStatistics(db, options, buffer);
    }
    // else if (ith_op == op_in_epoch) {
    //     (*buffer) << "=====================" << std::endl;
    //     (*buffer) << "One Epoch done ... " << ith_op << " operation" <<
    //     std::endl; LogTreeState(db, buffer); LogRocksDBStatistics(db,
    //     options, buffer);
    // }
#endif // PROFILE

    if (is_last_line)
      break;
  }

#ifdef PROFILE
  (*buffer) << "===========END HERE=========" << std::endl;
  LogTreeState(db, buffer);
  LogRocksDBStatistics(db, options, buffer);
#endif // PROFILE

  auto total_exec_time =
      std::chrono::duration_cast<std::chrono::nanoseconds>(
          std::chrono::high_resolution_clock::now() - exec_start)
          .count();
#ifdef TIMER
  (*buffer) << "=====================" << std::endl;
  (*buffer) << "Workload Execution Time: " << total_exec_time << std::endl;
  (*buffer) << "Inserts Execution Time: " << inserts_exec_time << std::endl;
  (*buffer) << "Updates Execution Time: " << updates_exec_time << std::endl;
  (*buffer) << "PointQuery Execution Time: " << pq_exec_time << std::endl;
  (*buffer) << "PointDelete Execution Time: " << pdelete_exec_time << std::endl;
  (*buffer) << "RangeQuery Execution Time: " << rq_exec_time << std::endl;
#endif // TIMER

  // delete iterator and close db
  delete it;
  if (!s.ok())
    std::cerr << s.ToString() << std::endl;
  assert(s.ok());
  s = db->Close();
  if (!s.ok())
    std::cerr << s.ToString() << std::endl;
  assert(s.ok());

  PrintRocksDBPerfStats(env, buffer, options);

  // flush final stats and delete ptr
  buffer->flush();
  delete buffer;
  buffer = nullptr;

  long long total_seconds = total_exec_time / 1e9;
  std::cout << "Experiment completed in " << total_seconds / 3600 << "h "
            << (total_seconds % 3600) / 60 << "m " << total_seconds % 60 << "s "
            << std::endl;
  return 0;
}
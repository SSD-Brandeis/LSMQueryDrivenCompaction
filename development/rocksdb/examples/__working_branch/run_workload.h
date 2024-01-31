#include <rocksdb/db.h>
#include <rocksdb/iostats_context.h>
#include <rocksdb/options.h>
#include <rocksdb/perf_context.h>
#include <rocksdb/table.h>

#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>

#include "config_options.h"
#include "emu_environment.h"
#include "thread"

std::string kDBPath = "./db_working_home";

struct operation_tracker {
  long _inserts_completed = 0;
  long _updates_completed = 0;
  long _point_deletes_completed = 0;
  long _range_deletes_completed = 0;
  long _point_queries_completed = 0;
  long _range_queries_completed = 0;
} op_track;

inline void sleep_for_ms(uint32_t ms) {
  std::this_thread::sleep_for(std::chrono::milliseconds(ms));
}

// Need to select timeout carefully
// Completion not guaranteed
bool CompactionMayAllComplete(DB *db) {
  uint64_t pending_compact;
  uint64_t pending_compact_bytes;
  uint64_t running_compact;
  bool success =
      db->GetIntProperty("rocksdb.compaction-pending", &pending_compact) &&
      db->GetIntProperty("rocksdb.estimate-pending-compaction-bytes",
                         &pending_compact_bytes) &&
      db->GetIntProperty("rocksdb.num-running-compactions", &running_compact);
  while ((pending_compact && pending_compact_bytes != 0) || running_compact ||
         !success) {
    sleep_for_ms(200);
    success =
        db->GetIntProperty("rocksdb.compaction-pending", &pending_compact) &&
        db->GetIntProperty("rocksdb.estimate-pending-compaction-bytes",
                           &pending_compact_bytes) &&
        db->GetIntProperty("rocksdb.num-running-compactions", &running_compact);
  }
  // sleep_for_ms(60000);
  return true;
}

int runWorkload(EmuEnv *_env) {
  DB *db;
  Options options;
  WriteOptions w_options;
  ReadOptions r_options;
  BlockBasedTableOptions table_options;
  FlushOptions f_options;

  // number of epochs to run the experiment
  int num_epochs = 10;

  int num_inserts_count = 0;
  int num_updates_count = 0;

  configOptions(_env, &options, &table_options, &w_options, &r_options,
                &f_options);

  if (_env->destroy_database) {
    DestroyDB(kDBPath, options);
    std::cout << "Destroying database ..." << std::endl;
  }

  // options.info_log_level = InfoLogLevel::DEBUG_LEVEL;
  options.level_compaction_dynamic_file_size = false;
  options.ignore_max_compaction_bytes_for_input = false;
  options.max_compaction_bytes = _env->buffer_size;

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

  // Clearing the system cache
  if (_env->clear_system_cache) {
    std::cout << "Clearing system cache ..." << std::endl;
    system("sudo sh -c 'echo 3 >/proc/sys/vm/drop_caches'");
  }
  // START stat collection
  if (_env->enable_rocksdb_perf_iostat == 1) {  // !YBS-feb15-XXI!
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

  Iterator *it = db->NewIterator(r_options);  // for range reads
  uint32_t counter = 0;                       // for progress bar

  // for (int i = 0; i < 20; ++i) {
  //   _env->level_delete_persistence_latency[i] = -1;
  //   _env->RR_level_last_file_selected[i] = -1;  // !YBS-sep06-XX!
  // }
  // !YBS-sep09-XX!

  // std::chrono::time_point<std::chrono::system_clock> starting_time,
  // ending_time; auto workload_start_time = std::chrono::system_clock::now();

  while (!workload_file.eof()) {
    char instruction;
    long long keys_returned_count;
    long key, start_key, end_key;
    string value;

    std::time_t end_time;

    workload_file >> instruction;
    _env->current_op = instruction;  // !YBS-sep18-XX!
    switch (instruction) {
      case 'I':  // insert
        num_inserts_count++;
        workload_file >> key >> value;
        // starting_time = std::chrono::system_clock::now();
        s = db->Put(w_options, to_string(key), value);
        // ending_time = std::chrono::system_clock::now();
        if (!s.ok()) std::cerr << s.ToString() << std::endl;
        assert(s.ok());
        op_track._inserts_completed++;
        counter++;
        break;

      case 'U':  // update
        num_updates_count++;
        workload_file >> key >> value;
        // starting_time = std::chrono::system_clock::now();
        s = db->Put(w_options, to_string(key), value);
        // ending_time = std::chrono::system_clock::now();
        if (!s.ok()) std::cerr << s.ToString() << std::endl;
        assert(s.ok());
        op_track._updates_completed++;
        counter++;
        break;

      case 'D':  // point delete
        workload_file >> key;
        // starting_time = std::chrono::system_clock::now();
        s = db->Delete(w_options, to_string(key));
        // ending_time = std::chrono::system_clock::now();
        assert(s.ok());
        op_track._point_deletes_completed++;
        counter++;
        break;

      case 'Q':  // probe: point query
        workload_file >> key;
        // starting_time = std::chrono::system_clock::now();
        s = db->Get(r_options, to_string(key), &value);
        // ending_time = std::chrono::system_clock::now();
        // if (!s.ok()) std::cerr << s.ToString() << "key = " << key <<
        // std::endl;
        //  assert(s.ok());
        op_track._point_queries_completed++;
        counter++;
        break;

      case 'S':  // scan: range query
        workload_file >> start_key >> end_key;
        lexico_valid = to_string(start_key).compare(to_string(end_key)) < 0;

        {
          auto now_time = std::chrono::high_resolution_clock::now();

          // Get the time since epoch in microseconds
          auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
              now_time.time_since_epoch());

          // Extract seconds and microseconds
          auto seconds =
              std::chrono::duration_cast<std::chrono::seconds>(duration);
          auto microseconds =
              std::chrono::duration_cast<std::chrono::microseconds>(duration -
                                                                    seconds);

          end_time = std::chrono::system_clock::to_time_t(
              std::chrono::system_clock::now());
          std::cout << "Starting new range query at: " << std::ctime(&end_time)
                    << "Seconds: " << seconds.count()
                    << " microseconds: " << microseconds.count() << std::endl
                    << std::flush;
        }

        if (_env->enable_range_query_compaction && lexico_valid) {
          it->Refresh(to_string(start_key), to_string(end_key));
        } else {
          it->Refresh();
        }

        assert(it->status().ok());
        keys_returned_count = 0;
        for (it->Seek(to_string(start_key)); it->Valid(); it->Next()) {
          if (it->key().ToString() > to_string(end_key)) {
            break;
          }
          keys_returned_count++;
          // std::cout << "found key = " << it->key().ToString() << std::endl;
        }
        {
          std::string each_level_stats;
          std::string sst_file_size;

          bool result =
              db->GetProperty("rocksdb.levelstats", &each_level_stats);
          bool live_sst_file_size =
              db->GetProperty("rocksdb.live-sst-files-size", &sst_file_size);

          std::cout << std::endl;
          std::cout << "Level Statistics" << std::endl << std::flush;

          if (result) {
            std::cout << each_level_stats << std::endl << std::flush;  // printing level stats
          }
          if (live_sst_file_size) {
            std::cout << "Total SST Files Size : " << sst_file_size
                      << std::endl << std::flush;  // printing sst file size
          }
        }

        if (!it->status().ok()) {
          std::cerr << it->status().ToString() << std::endl << std::flush;
        }

        // if (db_impl_->was_decision_true) {
        //   qstats->decision = true;
        // }
        {
          std::string each_level_stats;
          std::string sst_file_size;

          bool result =
              db->GetProperty("rocksdb.levelstats", &each_level_stats);
          bool live_sst_file_size =
              db->GetProperty("rocksdb.live-sst-files-size", &sst_file_size);

          std::cout << std::endl;
          std::cout << "Level Statistics" << std::endl << std::flush;

          if (result) {
            std::cout << each_level_stats << std::endl << std::flush;  // printing level stats
          }
          if (live_sst_file_size) {
            std::cout << "Total SST Files Size : " << sst_file_size
                      << std::endl << std::flush;  // printing sst file size
          }
        }

        if (_env->enable_range_query_compaction && lexico_valid) {
          it->Reset();
        }
        // ending_time = std::chrono::system_clock::now();

        op_track._range_queries_completed++;
        counter++;
        break;

      default:
        std::cerr << "ERROR: Case match NOT found !!" << std::endl;
        break;
    }

    // if (isOneEpochComplete(num_epochs, num_inserts_count, num_updates_count,
    //                        _env)) {
    //   stats_file << "=============== One epoch complete =============== "
    //                 "(Recording Stats ...)"
    //              << std::endl;
    //   stats_file << options.statistics->ToString();
    // }
  }

  workload_file.close();
  db->WaitForCompact(WaitForCompactOptions());
  CompactionMayAllComplete(db);
  // auto cfh = static_cast_with_check<ColumnFamilyHandleImpl>(
  //     db_impl_->DefaultColumnFamily());
  // ColumnFamilyData *cfd = cfh->cfd();

  // std::vector<std::tuple<std::string /*level number*/, int /*number of
  // files*/,
  //                        int /*number of entries*/>>
  //     levels_info;
  // int total_files = 0;
  // int total_entries = 0;

  // auto storage_info_before = cfd->current()->storage_info();
  // for (int l = 0; l < storage_info_before->num_non_empty_levels(); l++) {
  //   int num_entries = 0;
  //   auto num_files = storage_info_before->LevelFilesBrief(l).num_files;
  //   for (size_t file_index = 0; file_index < num_files; file_index++) {
  //     auto fd = storage_info_before->LevelFilesBrief(l).files[file_index];
  //     num_entries += storage_info_before->LevelFilesBrief(l)
  //                        .files[file_index]
  //                        .file_metadata->num_entries;
  //   }
  //   total_files += num_files;
  //   total_entries += num_entries;
  //   levels_info.push_back(
  //       std::make_tuple("Level-" + to_string(l), num_files, num_entries));
  // }
  // levels_info.push_back(std::make_tuple("Total: ", total_files,
  // total_entries));

  // stats_file << "\n\n"
  //             << std::setw(20) << "Level" << std::setw(20) << "Num Files"
  //             << std::setw(20) << "Num Entries" << std::endl;

  // for (auto level_info : levels_info) {
  //   stats_file << std::setw(20) << std::get<0>(level_info) << std::setw(20)
  //               << std::get<1>(level_info) << std::setw(20)
  //               << std::get<2>(level_info) << std::endl;
  // }

  // auto workload_end_time = std::chrono::system_clock::now();
  // auto workload_duration =
  //     std::chrono::duration_cast<std::chrono::duration<double>>(
  //         workload_end_time - workload_start_time);

  // auto total_info = levels_info.back();
  std::string each_level_stats;
  std::string sst_file_size;

  bool result = db->GetProperty("rocksdb.levelstats", &each_level_stats);
  bool live_sst_file_size =
      db->GetProperty("rocksdb.live-sst-files-size", &sst_file_size);

  std::cout << std::endl;
  std::cout << "Level Statistics" << std::endl;

  if (result) {
    std::cout << each_level_stats << std::endl;  // printing level stats
  }
  if (live_sst_file_size) {
    std::cout << "Total SST Files Size : " << sst_file_size
              << std::endl;  // printing sst file size
  }

  s = db->Close();
  if (!s.ok()) std::cerr << s.ToString() << std::endl;
  assert(s.ok());
  delete db;
  std::cout << "\n----------------------Closing DB-----------------------"
            // << " completion_status = " << fade_stats->completion_status
            << std::endl;

  // sleep(5);

  // reopening (and closing the DB to flush LOG to .sst file)
  // _env->compaction_pri = kMinOverlappingRatio;
  std::cout << "Re-opening DB -- Re-setting compaction style to: "
            << _env->compaction_pri << "\n";
  s = DB::Open(options, kDBPath, &db);

  result = db->GetProperty("rocksdb.levelstats", &each_level_stats);
  live_sst_file_size =
      db->GetProperty("rocksdb.live-sst-files-size", &sst_file_size);

  std::cout << std::endl;
  std::cout << "Level Statistics" << std::endl;

  if (result) {
    std::cout << each_level_stats << std::endl;  // printing level stats
  }
  if (live_sst_file_size) {
    std::cout << "Total SST Files Size : " << sst_file_size
              << std::endl;  // printing sst file size
  }
  std::cout << "----------------------------------------" << std::endl;

  if (!s.ok()) std::cerr << s.ToString() << std::endl;
  assert(s.ok());
  s = db->Close();
  if (!s.ok()) std::cerr << s.ToString() << std::endl;
  assert(s.ok());

  std::cout << "End of experiment - TEST !!\n";

  // fade_stats->exp_runtime = getclock_diff_ns(start_time, end_time);
  // !END

  // !YBS-sep01-XX
  // STOP stat collection & PRINT stat
  if (_env->enable_rocksdb_perf_iostat == 1) {  // !YBS-feb15-XXI!
    // sleep(5);
    rocksdb::SetPerfLevel(rocksdb::PerfLevel::kDisable);
    std::cout << "RocksDB Perf Context : " << std::endl;
    std::cout << rocksdb::get_perf_context()->ToString() << std::endl;
    std::cout << "RocksDB Iostats Context : " << std::endl;
    std::cout << rocksdb::get_iostats_context()->ToString() << std::endl;
    // END ROCKS PROFILE
    // Print Full RocksDB stats
    std::cout << "RocksDB Statistics : " << std::endl;
    std::cout << options.statistics->ToString() << std::endl;
    std::cout << "----------------------------------------" << std::endl;
    // std::string tr_mem;
    // db->GetProperty("rocksdb.estimate-table-readers-mem", &tr_mem);
    // // Print Full RocksDB stats
    // std::cout << "RocksDB Estimated Table Readers Memory (index, filters) : "
    // << tr_mem << std::endl;
  }
  // !END

  // printWorkloadStatistics(op_track);

  return 1;
}

// void printWorkloadStatistics(operation_tracker op_track) {
//   int l = 10;

//   std::cout << std::setfill(' ') << std::setfill(' ') << std::setw(l) << "#I"
//             << std::setfill(' ') << std::setw(l) << "#U" << std::setfill(' ')
//             << std::setw(l) << "#PD" << std::setfill(' ') << std::setw(l)
//             << "#RD" << std::setfill(' ') << std::setw(l) << "#PQ"
//             << std::setfill(' ') << std::setw(l) << "#RQ"
//             << "\n";

//   std::cout << std::setfill(' ') << std::setw(l) <<
//   op_track._inserts_completed; std::cout << std::setfill(' ') << std::setw(l)
//   << op_track._updates_completed; std::cout << std::setfill(' ') <<
//   std::setw(l)
//             << op_track._point_deletes_completed;
//   std::cout << std::setfill(' ') << std::setw(l)
//             << op_track._range_deletes_completed;
//   std::cout << std::setfill(' ') << std::setw(l)
//             << op_track._point_queries_completed;
//   std::cout << std::setfill(' ') << std::setw(l)
//             << op_track._range_queries_completed;

//   std::cout << std::endl;
// }

// void printExperimentalSetup(EmuEnv *_env) {
//   int l = 10;

//   std::cout << std::setfill(' ') << std::setw(l)
//             << "cmpt_sty"  // !YBS-sep07-XX!
//             << std::setfill(' ') << std::setw(l) << "cmpt_pri"
//             << std::setfill(' ') << std::setw(4) << "T" << std::setfill(' ')
//             << std::setw(l) << "P" << std::setfill(' ') << std::setw(l) <<
//             "B"
//             << std::setfill(' ') << std::setw(l) << "E" << std::setfill(' ')
//             << std::setw(l)
//             << "M"
//             // << std::setfill(' ') << std::setw(l)  << "f"
//             << std::setfill(' ') << std::setw(l) << "file_size"
//             << std::setfill(' ') << std::setw(l) << "L1_size"
//             << std::setfill(' ') << std::setw(l) << "blk_cch"  //
//             !YBS-sep09-XX!
//             << std::setfill(' ') << std::setw(l) << "BPK"
//             << "\n";
//   std::cout << std::setfill(' ') << std::setw(l)
//             << _env->compaction_style;  // !YBS-sep07-XX!
//   std::cout << std::setfill(' ') << std::setw(l) << _env->compaction_pri;
//   std::cout << std::setfill(' ') << std::setw(4) << _env->size_ratio;
//   std::cout << std::setfill(' ') << std::setw(l) <<
//   _env->buffer_size_in_pages; std::cout << std::setfill(' ') << std::setw(l)
//   << _env->entries_per_page; std::cout << std::setfill(' ') << std::setw(l)
//   << _env->entry_size; std::cout << std::setfill(' ') << std::setw(l) <<
//   _env->buffer_size;
//   // std::cout << std::setfill(' ') << std::setw(l) <<
//   // _env->file_to_memtable_size_ratio;
//   std::cout << std::setfill(' ') << std::setw(l) << _env->file_size;
//   std::cout << std::setfill(' ') << std::setw(l)
//             << _env->max_bytes_for_level_base;
//   std::cout << std::setfill(' ') << std::setw(l)
//             << _env->block_cache;  // !YBS-sep09-XX!
//   std::cout << std::setfill(' ') << std::setw(l) << _env->bits_per_key;
//   // std::cout << std::setfill(' ') << std::setw(l) <<
//   // _env->delete_persistence_latency; // !YBS-feb15-XXI!

//   std::cout << std::endl;
// }

bool isOneEpochComplete(const int num_epochs, int &num_inserts,
                        int &num_updates, EmuEnv *_env) {
  if (num_inserts == _env->num_inserts && num_updates == 0) {
    return true;
  } else if (num_updates == _env->num_updates / num_epochs) {
    num_updates = 0;
    return true;
  }
  return false;
}

inline void showProgress(const uint32_t &workload_size,
                         const uint32_t &counter) {
  // std::cout << "flag = " << flag << std::endl;
  // std::cout<<"2----";

  if (counter / (workload_size / 100) >= 1) {
    for (int i = 0; i < 104; i++) {
      std::cout << "\b";
      fflush(stdout);
    }
  }
  for (int i = 0; i < counter / (workload_size / 100); i++) {
    std::cout << "=";
    fflush(stdout);
  }
  std::cout << std::setfill(' ')
            << std::setw(101 - counter / (workload_size / 100));
  std::cout << counter * 100 / workload_size << "%";
  fflush(stdout);

  if (counter == workload_size) {
    std::cout << "\n";
    return;
  }
}

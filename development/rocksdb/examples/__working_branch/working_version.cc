/*
 *  Created on: May 13, 2019
 *  Author: Subhadeep
 */

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>

#include "aux_time.h"  // !YBS-sep09-XX!
// #include "chrono"      // !YBS-sep09-XX!
#include "emu_environment.h"
#include "parse_arguments.h"
#include "run_workload.h"

using namespace rocksdb;

/*
  Stats collector for each query
*/
enum QueryType { POINT, INSERT, UPDATE, DELETE, RANGE, INVALID };

std::string getQueryType(QueryType qtype);

class QueryStats {
  friend std::ostream &operator<<(std::ostream &os, const QueryStats &qstats) {
    os << qstats.query_number << ", " << getQueryType(qstats.query_type) << ", "
       << qstats.key << ", " << qstats.total_time_taken << ", "
       << qstats.decision << std::endl;
    return os;
  }

 private:
  static QueryStats *_instance;

  QueryStats() = default;

 public:
  long long query_number;
  QueryType query_type;
  std::string key;

  // number of files after query completion
  long long num_files_before;
  long long num_files_after;

  // number of entries after query completion
  long long num_entries_before;
  long long num_entries_after;

  // number of levels afte query completion
  long long num_levels_before;
  long long num_levels_after;

  double total_time_taken;

  bool decision = false;

  static QueryStats *getQueryStats() {
    if (QueryStats::_instance == nullptr) {
      QueryStats::_instance = new QueryStats();
    }
    return QueryStats::_instance;
  }
  void reset() {
    query_number = -1;
    query_type = QueryType::INVALID;
    key = "";
    num_levels_before = 0;
    num_levels_after = 0;
    num_files_before = 0;
    num_files_after = 0;
    num_entries_before = 0;
    num_entries_after = 0;
    total_time_taken = 0;
    decision = false;
  }
};

std::string getQueryType(QueryType qtype) {
  switch (qtype) {
    case POINT:
      return "Point";
      break;
    case RANGE:
      return "Range";
      break;
    case INSERT:
      return "Insert";
      break;
    case DELETE:
      return "Delete";
      break;
    case UPDATE:
      return "Update";
      break;
    default:
      return "Invalid";
      break;
  }
}

QueryStats *QueryStats::_instance = nullptr;

int main(int argc, char *argv[]) {
  // check emu_environment.h for the contents of EmuEnv and also the definitions
  // of the singleton experimental environment
  EmuEnv *_env = EmuEnv::getInstance();
  // parse the command line arguments
  if (parse_arguments2(argc, argv, _env)) {
    exit(1);
  }

  // if (_env->verbosity >= 4) {
  //   std::cout << "printing del_per_lat" << std::endl;
  //   for (int i = 0; i < 2; ++i) {
  //     std::cout << i << ": "
  //               << EmuEnv::GetLevelDeletePersistenceLatency(i, _env)
  //               << std::endl;
  //   }
  // }

  int s = runWorkload(_env);
  return 0;
}

/*
 *  Created on: May 13, 2019
 *  Author: Subhadeep, Papon
 */

#include <sstream>
#include <iostream>
#include <cstdio>
#include <sys/time.h>
#include <cmath>
#include <unistd.h>
#include <assert.h>
#include <fstream>
#include <stdlib.h>
#include <cstdlib>
#include <iomanip>
#include <cstring>

#include "args.hxx"
#include "load_gen.h"
#include "emu_environment.h"
#include "tree_builder.h"
#include "workload_executor.h"
#include "workload_generator.h"
#include "query_runner.h"

using namespace std;
using namespace tree_builder;
using namespace workload_exec;

/*
 * DECLARATIONS
 */
int Query::delete_key;
int Query::range_start_key;
int Query::range_end_key;
int Query::sec_range_start_key;
int Query::sec_range_end_key;
int Query::iterations_point_query;

// long inserts(EmuEnv* _env);
int parse_arguments2(int argc, char *argvx[], EmuEnv *_env);
void printEmulationOutput(EmuEnv *_env);
void calculateDeleteTileSize(EmuEnv *_env);

// int run_workload(read, pread, rread, write, update, delete, skew, others);
int runWorkload(EmuEnv *_env);

inline void showProgress(const uint32_t &workload_size, const uint32_t &counter)
{

  // std::cout << "counter = " << counter << std::endl;
  if (counter / (workload_size / 100) >= 1)
  {
    for (int i = 0; i < 104; i++)
    {
      std::cout << "\b";
      fflush(stdout);
    }
  }
  for (int i = 0; i < counter / (workload_size / 100); i++)
  {
    std::cout << "=";
    fflush(stdout);
  }
  std::cout << std::setfill(' ') << std::setw(101 - counter / (workload_size / 100));
  std::cout << counter * 100 / workload_size << "%";
  fflush(stdout);

  if (counter == workload_size)
  {
    std::cout << "\n";
    return;
  }
}

int main(int argc, char *argvx[])
{

  EmuEnv *_env = EmuEnv::getInstance();

  // parse the command line arguments
  if (parse_arguments2(argc, argvx, _env))
  {
    exit(1);
  }

  // Issuing INSERTS
  if (_env->num_inserts > 0)
  {
    generate_workload(argc, argvx);

    std::cout << "Workload Generated!" << std::endl;

    std::cerr << "Issuing inserts ... " << std::endl
              << std::flush;

    int only_file_meta_data = 0;

    if (_env->delete_tile_size_in_pages > 0 && _env->lethe_new == 0)
    {
      int s = runWorkload(_env);
      std::cout << "Insert complete ... " << std::endl
                << std::flush;
      DiskMetaFile::printAllEntries(only_file_meta_data);
      MemoryBuffer::getCurrentBufferStatistics();
      DiskMetaFile::getMetaStatistics();

      if (MemoryBuffer::verbosity == 1 || MemoryBuffer::verbosity == 2 || MemoryBuffer::verbosity == 3)
      {
        DiskMetaFile::printAllEntries(only_file_meta_data);
        MemoryBuffer::getCurrentBufferStatistics();
        DiskMetaFile::getMetaStatistics();
      }

      // Query::checkDeleteCount(Query::delete_key);
      // Query::rangeQuery(Query::range_start_key, Query::range_end_key);
      // Query::secondaryRangeQuery(Query::sec_range_start_key, Query::sec_range_end_key);
      // Query::pointQueryRunner(Query::iterations_point_query);

      // cout << "H" << "\t"
      //   << "DKey" << "\t"
      //   << "Full_Drop" << "\t"
      //   << "Partial_Drop" << "\t"
      //   << "No_Drop" << "\t\t"
      //   << "RKEYs" << "\t"
      //   << "Occurance" << "\t"
      //   << "SRKEYs" << "\t"
      //   << "Occurance" << "\t"
      //   << "P_iter" << "\t\t"
      //   << "Sumpid" << "\t\t"
      //   << "Avgpid" << "\t\t"
      //   << "Found" << "\t\t"
      //   << "NtFound" << "\n";

      // cout << _env->delete_tile_size_in_pages;
      // cout.setf(ios::right);
      // cout.precision(4);
      // cout.width(10);
      // cout << Query::delete_key;
      // cout.width(11);
      // cout << Query::complete_delete_count;
      // cout.width(18);
      // cout << Query::partial_delete_count;
      // cout.width(12);
      // cout << Query::not_possible_delete_count;
      // cout.width(12);
      // cout << Query::range_start_key << " " << Query::range_end_key;
      // cout.width(9);
      // cout << Query::range_occurances;
      // cout.width(11);
      // cout << Query::sec_range_start_key << " " << Query::sec_range_end_key;
      // cout.width(9);
      // cout << Query::secondary_range_occurances;
      // cout.width(15);
      // cout << Query::iterations_point_query;
      // cout.width(16);
      // cout << Query::sum_page_id;
      // cout.width(16);
      // cout << Query::sum_page_id/(Query::found_count * 1.0);
      // cout.width(15);
      // cout << Query::found_count;
      // cout.width(17);
      // cout << Query::not_found_count << "\n";

      if (MemoryBuffer::verbosity == 1 || MemoryBuffer::verbosity == 2 || MemoryBuffer::verbosity == 3)
        printEmulationOutput(_env);
    }
    else if (_env->delete_tile_size_in_pages == -1 && _env->lethe_new == 0)
    {
      for (int i = 1; i <= _env->buffer_size_in_pages; i = i * 2)
      {
        cout << "Running for delete tile size: " << i << " ..." << endl;
        _env->delete_tile_size_in_pages = i;
        int s = runWorkload(_env);
        if (MemoryBuffer::verbosity == 1 || MemoryBuffer::verbosity == 2 || MemoryBuffer::verbosity == 3)
        {
          DiskMetaFile::printAllEntries(only_file_meta_data);
          MemoryBuffer::getCurrentBufferStatistics();
          DiskMetaFile::getMetaStatistics();
        }

        // cout << "Running Delete Query..." << endl;
        // Query::delete_query_experiment();
        // cout << "Running Range Query..." << endl;
        // Query::range_query_experiment();
        // cout << "Running Secondary Range Query..." << endl;
        // Query::sec_range_query_experiment();
        // cout << "Running Point Query..." << endl;
        // Query::point_query_experiment();

        DiskMetaFile::clearAllEntries();
        WorkloadExecutor::counter = 0;

        if (MemoryBuffer::verbosity == 1 || MemoryBuffer::verbosity == 2 || MemoryBuffer::verbosity == 3)
          printEmulationOutput(_env);
      }
    }
    else if (_env->lethe_new == 1 || _env->lethe_new == 2)
    {
      int s = runWorkload(_env);
      // DiskMetaFile::printAllEntries(only_file_meta_data);
      MemoryBuffer::getCurrentBufferStatistics();
      DiskMetaFile::getMetaStatistics();
      if (MemoryBuffer::verbosity == 1 || MemoryBuffer::verbosity == 2 || MemoryBuffer::verbosity == 3)
      {
        DiskMetaFile::printAllEntries(only_file_meta_data);
        MemoryBuffer::getCurrentBufferStatistics();
        DiskMetaFile::getMetaStatistics();
      }

      // cout << "Running Delete Query..." << endl;
      // Query::delete_query_experiment();
      // cout << "Running Range Query..." << endl;
      // Query::range_query_experiment();
      // cout << "Running Secondary Range Query..." << endl;
      // Query::sec_range_query_experiment();
      // cout << "Running Point Query..." << endl;
      // Query::new_point_query_experiment();

      DiskMetaFile::clearAllEntries();
      WorkloadExecutor::counter = 0;
      printEmulationOutput(_env);

      if (MemoryBuffer::verbosity == 1 || MemoryBuffer::verbosity == 2 || MemoryBuffer::verbosity == 3)
        printEmulationOutput(_env);
    }

    // srand(time(0));
    // WorkloadExecutor::getWorkloadStatictics(_env);
    // assert(_env->num_inserts == inserted);
  }
  return 0;
}

int runWorkload(EmuEnv *_env)
{

  MemoryBuffer *buffer_instance = MemoryBuffer::getBufferInstance(_env);
  WorkloadExecutor workload_executer;
  // reading from file
  ifstream workload_file;
  workload_file.open("workload.txt");
  assert(workload_file);
  int counter = 0;
  while (!workload_file.eof())
  {
    char instruction;
    std::string sortkey;
    std::string value;
    std::string result;        // Result of Get Query
    std::string start_sortkey; // Start of Range Query (inclusive)
    std::string end_sortkey;   // End of Range Query (inclusive)
    workload_file >> instruction;
    switch (instruction)
    {
    case 'I':
    case 'U':
      workload_file >> sortkey >> value;
      workload_executer.insert(sortkey, value);
      break;
    case 'D':
      workload_file >> sortkey;
      workload_executer.remove(sortkey);
      break;
    case 'Q':
      workload_file >> sortkey;
      result = workload_executer.get(sortkey);
      std::cout << "Point Query for Key : " << sortkey
                << "\n Value : " << result << std::endl;
      break;
    case 'S':
      workload_file >> start_sortkey >> end_sortkey;
      std::cout << "Range Query from Start Key : " << start_sortkey
                << " End Key : " << end_sortkey << std::endl;
      RangeIterator range_iterator = workload_executer.getRange(start_sortkey, end_sortkey);

      for (auto it = range_iterator.begin(); it != range_iterator.end(); ++it)
      {
        Entry entry = *it;
        if (entry.getKey().compare(end_sortkey) > 0)
        {
          break;
        }
        std::cout << "Key: " << entry.getKey() << " Value: " << entry.getValue() << std::endl;
      }
      break;
    }
    instruction = '\0';
    counter++;
    if (!(counter % (_env->num_inserts / 100)))
    {
      showProgress(_env->num_inserts, counter);
    }
  }

  return 1;
}

int parse_arguments2(int argc, char *argvx[], EmuEnv *_env)
{
  args::ArgumentParser parser("KIWI Emulator", "");

  args::Group group1(parser, "This group is all exclusive:", args::Group::Validators::DontCare);

  args::ValueFlag<long> range_query_cmd(group1, "S", "Number of range queries [def: 0]", {'S', "range_query"});
  args::ValueFlag<int> size_ratio_cmd(group1, "T", "The size ratio of the tree [def: 2]", {'T', "size_ratio"});
  args::ValueFlag<int> buffer_size_in_pages_cmd(group1, "P", "Size of the memory buffer in terms of pages [def: 128]", {'P', "buffer_size_in_pages"});
  args::ValueFlag<int> entries_per_page_cmd(group1, "B", "No of entries in one page [def: 128]", {'B', "entries_per_page"});
  args::ValueFlag<int> entry_size_cmd(group1, "E", "Entry size in bytes [def: 128 B]", {'E', "entry_size"});
  args::ValueFlag<long> buffer_size_cmd(group1, "M", "Memory size (PBE) [def: 2 MB]", {'M', "memory_size"});
  args::ValueFlag<int> delete_tile_size_in_pages_cmd(group1, "delete_tile_size_in_pages", "Size of a delete tile in terms of pages [def: -1]", {'h', "delete_tile_size_in_pages"});
  args::ValueFlag<long> file_size_cmd(group1, "file_size", "file size [def: 256 KB]", {"file_size"});
  args::ValueFlag<long> num_inserts_cmd(group1, "#inserts", "The number of unique inserts to issue in the experiment [def: 0]", {'I', "num_inserts"});
  args::ValueFlag<long> num_updates_cmd(group1, "#updates", "The number of updates to issue in the experiment [def: 0]", {'U', "num_updates"});
  args::ValueFlag<long> num_point_deletes_cmd(group1, "#point_deletes", "The number of point deletes to issue in the experiment [def: 0]", {'D', "num_point_deletes"});
  args::ValueFlag<long> num_point_queries_cmd(group1, "#point_queries", "The number of point queries to issue in the experiment [def: 0]", {'Q', "num_point_queries"});
  args::ValueFlag<long> num_range_queries_cmd(group1, "#range_queries", "The number of range queries to issue in the experiment [def: 0]", {'S', "num_range_queries"});
  args::ValueFlag<float> range_query_selectivity_cmd(group1, "#selectivity", "The range query selectivity to issue range queries [def: 0]", {'Y', "range_query_selectivity"});
  args::ValueFlag<int> cor_cmd(group1, "#correlation", "Correlation between sort key and delete key [def: 0]", {'c', "correlation"});
  args::ValueFlag<int> verbosity_cmd(group1, "verbosity", "The verbosity level of execution [0,1,2; def:0]", {'V', "verbosity"});
  args::ValueFlag<int> lethe_new_cmd(group1, "lethe_new", "Specific h across tree(0), Optimal h across tree(1) or different optimal h in each levels(2) [0, 1, 2; def:0]", {'X', "lethe_new"});
  args::ValueFlag<int> SRD_cmd(group1, "SRD", "Count of secondary range delete [def:1]", {'I', "SRD"});
  args::ValueFlag<int> EPQ_cmd(group1, "EPQ", "Count of empty point queries [def:1000000]", {'J', "EPQ"});
  args::ValueFlag<int> PQ_cmd(group1, "PQ", "Count of non-empty point queries [def:1000000]", {'K', "PQ"});
  args::ValueFlag<int> SRQ_cmd(group1, "SRQ", "Count of short range queries [def:1]", {'L', "SRQ"});

  args::ValueFlag<int> delete_key_cmd(group1, "delete_key", "Delete all keys less than DK [def:700]", {'D', "delete_key"});
  args::ValueFlag<int> range_start_key_cmd(group1, "range_start_key", "Starting key of the range query [def:2000]", {'S', "range_start_key"});
  args::ValueFlag<int> range_end_key_cmd(group1, "range_end_key", "Ending key of the range query [def:5000]", {'F', "range_end_key"});
  args::ValueFlag<int> sec_range_start_key_cmd(group1, "sec_range_start_key", "Starting key of the secondary range query [def:200]", {'s', "sec_range_start_key"});
  args::ValueFlag<int> sec_range_end_key_cmd(group1, "sec_range_end_key", "Ending key of the secondary range query [def:500]", {'f', "sec_range_end_key"});
  args::ValueFlag<int> iterations_point_query_cmd(group1, "iterations_point_query", "Number of point queries to be performed [def:100000]", {'N', "iterations_point_query"});

  try
  {
    parser.ParseCLI(argc, argvx);
  }
  catch (args::Help &)
  {
    std::cout << parser;
    exit(0);
    // return 0;
  }
  catch (args::ParseError &e)
  {
    std::cerr << e.what() << std::endl;
    std::cerr << parser;
    return 1;
  }
  catch (args::ValidationError &e)
  {
    std::cerr << e.what() << std::endl;
    std::cerr << parser;
    return 1;
  }

  _env->size_ratio = size_ratio_cmd ? args::get(size_ratio_cmd) : 2;
  _env->buffer_size_in_pages = buffer_size_in_pages_cmd ? args::get(buffer_size_in_pages_cmd) : 128;
  _env->entries_per_page = entries_per_page_cmd ? args::get(entries_per_page_cmd) : 128;
  _env->entry_size = entry_size_cmd ? args::get(entry_size_cmd) : 128;
  _env->buffer_size = buffer_size_cmd ? args::get(buffer_size_cmd) : _env->buffer_size_in_pages * _env->entries_per_page * _env->entry_size;
  _env->delete_tile_size_in_pages = delete_tile_size_in_pages_cmd ? args::get(delete_tile_size_in_pages_cmd) : -1;
  _env->file_size = file_size_cmd ? args::get(file_size_cmd) : _env->buffer_size;
  _env->num_inserts = num_inserts_cmd ? args::get(num_inserts_cmd) : 0;
  _env->num_updates = num_updates_cmd ? args::get(num_updates_cmd) : 0;
  _env->num_point_deletes = num_point_deletes_cmd ? args::get(num_point_deletes_cmd) : 0;
  _env->num_point_queries = num_point_queries_cmd ? args::get(num_point_queries_cmd) : 0;
  _env->num_range_queries = num_range_queries_cmd ? args::get(num_range_queries_cmd) : 0;
  _env->range_query_selectivity = range_query_selectivity_cmd ? args::get(range_query_selectivity_cmd) : 0;
  _env->verbosity = verbosity_cmd ? args::get(verbosity_cmd) : 0;
  _env->correlation = cor_cmd ? args::get(cor_cmd) : 0;
  _env->lethe_new = lethe_new_cmd ? args::get(lethe_new_cmd) : 0;

  _env->srd_count = SRD_cmd ? args::get(SRD_cmd) : 1;
  _env->epq_count = EPQ_cmd ? args::get(EPQ_cmd) : 1000000;
  _env->pq_count = PQ_cmd ? args::get(PQ_cmd) : 1000000;
  _env->srq_count = SRQ_cmd ? args::get(SRQ_cmd) : 10000;
  calculateDeleteTileSize(_env);

  Query::delete_key = delete_key_cmd ? args::get(delete_key_cmd) : 700;
  Query::range_start_key = range_start_key_cmd ? args::get(range_start_key_cmd) : 2000;
  Query::range_end_key = range_end_key_cmd ? args::get(range_end_key_cmd) : 5000;
  Query::sec_range_start_key = sec_range_start_key_cmd ? args::get(sec_range_start_key_cmd) : 200;
  Query::sec_range_end_key = sec_range_end_key_cmd ? args::get(sec_range_end_key_cmd) : 500;
  Query::iterations_point_query = iterations_point_query_cmd ? args::get(iterations_point_query_cmd) : 100000;

  return 0;
}

void calculateDeleteTileSize(EmuEnv *_env)
{
  // calculation of Kiwi++ (following desmos)
  float num = (_env->num_inserts * (_env->size_ratio - 1) * 1.0);
  float denum = (_env->buffer_size_in_pages * _env->entries_per_page * _env->size_ratio * 1.0);
  _env->level_count = ceil(log(num / denum) / log(_env->size_ratio));
  float E[20] = {-1};
  float F[20] = {-1};
  float G[20] = {-1};
  float R[20] = {-1};
  float temp_sum = 0;

  for (int j = 1; j <= _env->level_count; j++)
  {
    temp_sum += pow(_env->size_ratio, j);
  }
  for (int i = 1; i <= _env->level_count; i++)
  {
    E[i] = pow(_env->size_ratio, i) / (temp_sum * 1.0);
  }
  for (int i = 1; i <= _env->level_count; i++)
  {
    float tempsum2 = 0;
    for (int j = 1; j <= i - 1; j++)
    {
      tempsum2 += pow(_env->size_ratio, j);
    }
    F[i] = (tempsum2 * 1.0) / temp_sum;
  }
  for (int i = 1; i <= _env->level_count; i++)
  {
    G[i] = 1 - E[i] - F[i];
  }
  float phi = 0.0081925;
  for (int i = 1; i <= _env->level_count; i++)
  {
    R[i] = (pow((_env->size_ratio * 1.0), ((_env->size_ratio * 1.0) / (_env->size_ratio - 1))) * phi) / (pow(_env->size_ratio, _env->level_count + 1 - i));
  }

  for (int i = 1; i <= _env->level_count; i++)
  {
    float num2 = _env->buffer_size_in_pages * pow(_env->size_ratio, i) * _env->srd_count;
    float denum2 = ((_env->epq_count + (_env->pq_count * G[i])) * R[i]) + ((R[i] * _env->pq_count * E[i]) / 2) + _env->srq_count;
    _env->variable_delete_tile_size_in_pages[i] = round(pow(num2 / denum2, 0.5));
    if (_env->variable_delete_tile_size_in_pages[i] == 0)
      _env->variable_delete_tile_size_in_pages[i] = 1;
    if (_env->variable_delete_tile_size_in_pages[i] > _env->buffer_size_in_pages)
      _env->variable_delete_tile_size_in_pages[i] = _env->buffer_size_in_pages;
    // cout << _env->variable_delete_tile_size_in_pages[i] << " " << endl;
  }
  if (_env->lethe_new == 1)
  {
    // Optimal h for Kiwi
    float phi_opt = ((pow(_env->size_ratio, (_env->size_ratio * 1.0 / (_env->size_ratio - 1) * 1.0))) / _env->size_ratio) * phi;
    float num_opt = (_env->srd_count * _env->num_inserts * 1.0) / _env->entries_per_page;
    float denum_opt = ((_env->epq_count + _env->pq_count) * phi_opt * _env->level_count) + (_env->level_count * _env->srq_count);
    _env->delete_tile_size_in_pages = round(pow(num_opt / denum_opt, 0.5));
    if (_env->delete_tile_size_in_pages == 0)
      _env->delete_tile_size_in_pages = 1;
    if (_env->delete_tile_size_in_pages > _env->buffer_size_in_pages)
      _env->delete_tile_size_in_pages = _env->buffer_size_in_pages;
    std::cout << "Optimal Delete Tile Size: " << _env->delete_tile_size_in_pages << std::endl;
  }
}

void printEmulationOutput(EmuEnv *_env)
{
  // double percentage_non_zero_result_queries = ceil((100 * _env->nonzero_to_zero_ratio) / (_env->nonzero_to_zero_ratio + 1.0));
  // if (_env->verbosity >= 1)
  std::cout << "T, P, B, E, M, h, file_size, #I \n";
  std::cout << _env->size_ratio << ", ";
  std::cout << _env->buffer_size_in_pages << ", ";
  std::cout << _env->entries_per_page << ", ";
  std::cout << _env->entry_size << ", ";
  std::cout << _env->buffer_size << ", ";
  std::cout << _env->delete_tile_size_in_pages << ", ";
  std::cout << _env->file_size << ", ";
  std::cout << _env->num_inserts;

  std::cout << std::endl;

  std::cout << "Kiwi++,\tSRD,\tEPQ,\tPQ,\tSRQ\n";
  std::cout << _env->lethe_new << "\t";
  std::cout << _env->srd_count << "\t";
  std::cout << _env->epq_count << "\t";
  std::cout << _env->pq_count << "\t";
  std::cout << _env->srq_count << "\t";

  std::cout << std::endl;

  if (_env->lethe_new == 2)
  {
    std::cout << "Delete tiles size : " << std::endl;
    for (int i = 1; i <= _env->level_count; i++)
    {
      std::cout << _env->variable_delete_tile_size_in_pages[i] << "\t";
    }
    std::cout << std::endl;
  }
}

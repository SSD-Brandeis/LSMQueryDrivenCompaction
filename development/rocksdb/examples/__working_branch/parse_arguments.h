#include "args.hxx"
#include "emu_environment.h"

int parse_arguments2(int argc, char *argv[], EmuEnv *_env) {
  args::ArgumentParser parser("RocksDB_parser.", "");
  args::Group group1(parser, "This group is all exclusive:",
                     args::Group::Validators::DontCare);

  args::ValueFlag<int> destroy_database_cmd(
      group1, "d", "Destroy and recreate the database [def: 1]",
      {'d', "destroy"});
  args::ValueFlag<int> clear_system_cache_cmd(
      group1, "cc", "Clear system cache [def: 1]", {"cc"});

  args::ValueFlag<int> size_ratio_cmd(
      group1, "T",
      "The number of unique inserts to issue in the experiment [def: 10]",
      {'T', "size_ratio"});
  args::ValueFlag<int> buffer_size_in_pages_cmd(
      group1, "P",
      "The number of unique inserts to issue in the experiment [def: 512]",
      {'P', "buffer_size_in_pages"});
  args::ValueFlag<int> entries_per_page_cmd(
      group1, "B",
      "The number of unique inserts to issue in the experiment [def: 4]",
      {'B', "entries_per_page"});
  args::ValueFlag<int> entry_size_cmd(
      group1, "E",
      "The number of unique inserts to issue in the experiment [def: 1024 B]",
      {'E', "entry_size"});
  args::ValueFlag<long> buffer_size_cmd(
      group1, "M",
      "The number of unique inserts to issue in the experiment [def: 16 MB]",
      {'M', "memory_size"});
  args::ValueFlag<int> file_to_memtable_size_ratio_cmd(
      group1, "file_to_memtable_size_ratio",
      "The number of unique inserts to issue in the experiment [def: 1]",
      {'f', "file_to_memtable_size_ratio"});
  args::ValueFlag<long> file_size_cmd(
      group1, "file_size",
      "The number of unique inserts to issue in the experiment [def: 256 KB]",
      {'F', "file_size"});
  args::ValueFlag<int> verbosity_cmd(
      group1, "verbosity", "The verbosity level of execution [0,1,2; def: 0]",
      {'V', "verbosity"});
  args::ValueFlag<int> compaction_pri_cmd(
      group1, "compaction_pri",
      "[Compaction priority: 1 for kMinOverlappingRatio, 2 for "
      "kByCompensatedSize, 3 for kOldestLargestSeqFirst, 4 for "
      "kOldestSmallestSeqFirst; def: 1]",
      {'c', "compaction_pri"});
  args::ValueFlag<int> compaction_style_cmd(
      group1, "compaction_style",
      "[Compaction priority: 1 for kCompactionStyleLevel, 2 for "
      "kCompactionStyleUniversal, 3 for kCompactionStyleFIFO, 4 for "
      "kCompactionStyleNone; def: 1]",
      {'C', "compaction_style"});
  args::ValueFlag<int> bits_per_key_cmd(
      group1, "bits_per_key",
      "The number of bits per key assigned to Bloom filter [def: 10]",
      {'b', "bits_per_key"});
  args::ValueFlag<int> block_cache_cmd(
      group1, "bb", "Block cache size in MB [def: 8 MB]", {"bb"});
  args::ValueFlag<int> show_progress_cmd(group1, "show_progress",
                                         "Show progress [def: 0]", {'s', "sp"});
  args::ValueFlag<double> del_per_th_cmd(
      group1, "del_per_th", "Delete persistence threshold [def: -1]",
      {'t', "dpth"});
  args::ValueFlag<int> enable_rocksdb_perf_iostat_cmd(
      group1, "enable_rocksdb_perf_iostat",
      "Enable RocksDB's internal Perf and IOstat [def: 0]", {"stat"});

  args::ValueFlag<long> num_inserts_cmd(
      group1, "inserts",
      "The number of unique inserts to issue in the experiment [def: 1]",
      {'I', "inserts"});
  args::ValueFlag<long> num_updates_cmd(
      group1, "updates",
      "The number of unique updates to issue in the experiment [def: 0]",
      {'U', "updates"});
  args::ValueFlag<long> num_range_queries_cmd(
      group1, "range_queries",
      "The number of unique range queries to issue in the experiment [def: 0]",
      {'S', "range_queries"});

  args::ValueFlag<int> enable_range_query_compaction_cmd(
      group1, "enable_range_query_compaction",
      "Enable range query comapaction [def: 0]",
      {"rq", "range_query_compaction"});

  args::ValueFlag<int> level_renaming_enabled_cmd(
      group1, "level_renaming_enabled",
      "Enable level renaming when to add new level", {"re", "renaming_level"});

  args::ValueFlag<float> upper_threshold_cmd(
      group1, "higher_bound",
      "Higher threshold between adjancent levels to perform compaction [def: "
      "inf]",
      {"ub", "upper_threshold"});
  args::ValueFlag<float> lower_threshold_cmd(
      group1, "lower_bound",
      "Lower threshold between adjacent levels to perform compaction [def: 0]",
      {"lb", "lower_threshold"});
  args::ValueFlag<float> range_query_selectivity_cmd(
      group1, "Y", "Range query selectivity [def: 0]",
      {'Y', "range_query_selectivity"});

  // Fluid LSM parameters
  args::ValueFlag<float> smaller_lvl_runs_count_cmd(
      group1, "K", "Number of run in smaller levels", {'K', "k"});
  args::ValueFlag<float> larger_lvl_runs_count_cmd(
      group1, "Z", "Number of run in larger levels", {'Z', "z"});

  try {
    parser.ParseCLI(argc, argv);
  } catch (args::Help &) {
    std::cout << parser;
    exit(0);
    // return 0;
  } catch (args::ParseError &e) {
    std::cerr << e.what() << std::endl;
    std::cerr << parser;
    return 1;
  } catch (args::ValidationError &e) {
    std::cerr << e.what() << std::endl;
    std::cerr << parser;
    return 1;
  }

  _env->destroy_database =
      destroy_database_cmd ? args::get(destroy_database_cmd) : 1;
  _env->clear_system_cache =
      clear_system_cache_cmd ? args::get(clear_system_cache_cmd) : 1;
  _env->size_ratio = size_ratio_cmd ? args::get(size_ratio_cmd) : 2;

  // change to 128 or 256 [Added by Subhadeep]
  _env->buffer_size_in_pages =
      buffer_size_in_pages_cmd ? args::get(buffer_size_in_pages_cmd) : 128;

  // change to 128 [Added by Subhadeep]
  _env->entries_per_page =
      entries_per_page_cmd ? args::get(entries_per_page_cmd) : 128;

  // change to 32 [Added by Subhadeep]
  _env->entry_size = entry_size_cmd ? args::get(entry_size_cmd) : 32;

  _env->buffer_size = buffer_size_cmd
                          ? args::get(buffer_size_cmd)
                          : _env->buffer_size_in_pages *
                                _env->entries_per_page * _env->entry_size;
  _env->file_to_memtable_size_ratio =
      file_to_memtable_size_ratio_cmd
          ? args::get(file_to_memtable_size_ratio_cmd)
          : 1;
  _env->file_size =
      file_size_cmd ? args::get(file_size_cmd) : _env->buffer_size;
  _env->verbosity = verbosity_cmd ? args::get(verbosity_cmd) : 0;
  _env->compaction_pri = compaction_pri_cmd ? args::get(compaction_pri_cmd) : 1;
  _env->compaction_style =
      compaction_style_cmd ? args::get(compaction_style_cmd) : 1;
  _env->bits_per_key = bits_per_key_cmd ? args::get(bits_per_key_cmd) : 10;
  _env->block_cache = block_cache_cmd ? args::get(block_cache_cmd) : 8;
  _env->show_progress = show_progress_cmd ? args::get(show_progress_cmd) : 0;
  _env->delete_persistence_latency =
      del_per_th_cmd ? args::get(del_per_th_cmd) : 0;
  _env->enable_rocksdb_perf_iostat =
      enable_rocksdb_perf_iostat_cmd ? args::get(enable_rocksdb_perf_iostat_cmd)
                                     : 0;
  _env->max_background_jobs = 0;
  _env->target_file_size_base = _env->buffer_size;
  _env->max_bytes_for_level_base = _env->buffer_size * _env->size_ratio;

  _env->num_inserts = num_inserts_cmd ? args::get(num_inserts_cmd) : 0;
  _env->num_updates = num_updates_cmd ? args::get(num_updates_cmd) : 0;
  _env->num_range_queries =
      num_range_queries_cmd ? args::get(num_range_queries_cmd) : 0;

  // Range Query Driven Compaction Options
  _env->enable_range_query_compaction =
      enable_range_query_compaction_cmd
          ? args::get(enable_range_query_compaction_cmd)
          : 0;
  _env->level_renaming_enabled =
      level_renaming_enabled_cmd ? args::get(level_renaming_enabled_cmd) : 0;

  _env->lower_threshold =
      lower_threshold_cmd ? args::get(lower_threshold_cmd) : 0;
  _env->upper_threshold = upper_threshold_cmd
                              ? args::get(upper_threshold_cmd)
                              : std::numeric_limits<float>::max();

  // Fluid LSM parameters
  _env->smaller_lvl_runs_count =
      smaller_lvl_runs_count_cmd ? args::get(smaller_lvl_runs_count_cmd) : 1;
  _env->larger_lvl_runs_count =
      larger_lvl_runs_count_cmd ? args::get(larger_lvl_runs_count_cmd) : 1;

  return 0;
}

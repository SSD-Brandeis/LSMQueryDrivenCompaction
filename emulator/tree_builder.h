/*
 *  Created on: May 14, 2019
 *  Author: Subhadeep, Papon
 */

#include "emu_environment.h"
#include "memtable.h"
#include "sstfile.h"

#include <iostream>
#include <vector>

using namespace std;

namespace tree_builder
{
  class MemoryBuffer
  {
  private:
    MemoryBuffer(EmuEnv *_env);
    static MemoryBuffer *buffer_instance;
    static long max_buffer_size;

  public:
    static float buffer_flush_threshold;
    static long current_buffer_entry_count;
    static long current_buffer_size;
    static float current_buffer_saturation;
    static int buffer_flush_count;
    static MemTable *buffer;
    static int verbosity;

    static MemoryBuffer *getBufferInstance(EmuEnv *_env);
    static int getCurrentBufferStatistics();
    static int setCurrentBufferStatistics(int entry_count_change, int buffer_flush_threshold);
    static int initiateBufferFlush(int level_to_flush_in);
    static int printBufferEntries();
    // long getBufferSize();
  };

  class DiskMetaFile
  {
  private:
    static pair<long, long> getMatchingKeyFile(long min_key, long max_key, int key_level); //??? Definition change hobe

  public:
    // static SSTFile* head_level_1;
    static int checkAndAdjustLevelSaturation(int level);
    static long getLevelEntryCount(int level);
    static int getLevelFileCount(int level);
    static int getTotalLevelCount();
    static int checkOverlapping(SSTFile *file, int level);

    static int setSSTFileHead(SSTFile *arg, int level);
    static SSTFile *getSSTFileHead(int level);

    static void getMetaStatistics();
    static int printAllEntries(int only_file_meta_data);
    static int getTotalPageCount();
    static int clearAllEntries();

    static SSTFile *level_head[32];

    static long level_min_key[32];
    static long level_max_key[32];
    static long level_file_count[32];
    static long level_entry_count[32];
    static long level_current_size[32];

    static long level_max_size[32];
    static long level_max_file_count[32];
    static long global_level_file_counter[32];
    static float disk_run_flush_threshold[32];

    static int compaction_counter[32];
    static int compaction_through_sortmerge_counter[32];
    static int compaction_through_point_manipulation_counter[32];
    static int compaction_file_counter[32];

    ////static disk_run_flush_threshold;
  };

} // namespace

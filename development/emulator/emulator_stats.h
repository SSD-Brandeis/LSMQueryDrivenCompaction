#ifndef _EMULATOR_STATS_H_
#define _EMULATOR_STATS_H_

#include <vector>
#include <chrono>

namespace emulator
{
    class EmuStats
    {
        // number of compactions
        static int num_compaction;

        // number of buffer flush
        static int num_buffer_flush;

        // number of page flush
        static int num_page_flushed;

        // number of trivial files moves
        static int num_trivial_file_moves;

        // number of files written during range query
        static int num_files_flush_range_query;

        // number of entries in Tree before and after range query
        static std::vector<std::pair<int /* before */, int /* after */>> num_entries_before_after_range_query;

        // time taken by each range query
        static std::vector<std::chrono::duration<double>> time_duration_for_range_query;

        // total size of data written
        static int total_entries_written;

    public:
        static void recordBufferFlush();
        static void recordTrivialFileMove();
        static void recordCompaction(int page_count, int entries_count);
        static void recordFileFlushRangeQuery(int page_count, int entries_count);

        static void recordRangeQueryStats(std::pair<int /* before */, int /* after */> entries_counts, std::chrono::duration<double> time_taken);

        static void print();
    };
}

#endif // _EMULATOR_STATS_H_
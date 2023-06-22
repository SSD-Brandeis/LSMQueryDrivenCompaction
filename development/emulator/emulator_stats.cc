#include <iostream>
#include <fstream>

#include "emulator_stats.h"
#include "emu_environment.h"

namespace emulator
{
    // std::string rq_path = "/Users/shubham/LSMQueryDrivenCompaction/development/emulator/";
    std::string rq_path = "";

    int EmuStats::num_buffer_flush = 0;
    int EmuStats::num_trivial_file_moves = 0;
    int EmuStats::num_compaction = 0;
    int EmuStats::num_page_flushed = 0;
    int EmuStats::total_entries_written = 0;
    int EmuStats::num_files_flush_range_query = 0;
    int EmuStats::total_vanilla_compaction = 0;
    int EmuStats::total_rqd_compaction = 0;
    std::vector<std::pair<int /* before */, int /* after */>> EmuStats::num_entries_before_after_range_query;
    std::vector<std::chrono::duration<double>> EmuStats::time_duration_for_range_query;

    void EmuStats::recordBufferFlush()
    {
        EmuStats::num_buffer_flush++;
    }

    void EmuStats::recordTrivialFileMove()
    {
        EmuStats::num_trivial_file_moves++;
    }

    void EmuStats::recordCompaction(int page_count, int entries_count)
    {
        EmuStats::num_compaction++;
        EmuStats::num_page_flushed += page_count;
        EmuStats::total_entries_written += entries_count;
    }

    void EmuStats::recordFileFlushRangeQuery(int page_count, int entries_count)
    {
        EmuStats::num_files_flush_range_query++;
        EmuStats::num_page_flushed += page_count;
        EmuStats::total_entries_written += entries_count;
    }

    void EmuStats::recordRangeQueryStats(std::pair<int /* before */, int /* after */> entries_counts, std::chrono::duration<double> time_taken)
    {
        EmuStats::num_entries_before_after_range_query.push_back(entries_counts);
        EmuStats::time_duration_for_range_query.push_back(time_taken);
    }

    void EmuStats::recordVanillaCompaction()
    {
        EmuStats::total_vanilla_compaction += 1;
    }

    void EmuStats::recordRQDCompaction()
    {
        EmuStats::total_rqd_compaction += 1;
    }

    void EmuStats::print()
    {
        EmuEnv *_env = EmuEnv::getInstance();

        std::cout << std::endl
                  << std::endl
                  << std::endl
                  << std::endl;
        std::cout << " ================ Print Stats Emulator ================ " << std::endl;
        std::cout << " Buffer Flush Count : " << EmuStats::num_buffer_flush << std::endl;
        std::cout << " Num Trivial File Moves : " << EmuStats::num_trivial_file_moves << std::endl;
        std::cout << " Num Compaction : " << EmuStats::num_compaction << std::endl;
        std::cout << " Total Page Flushed : " << EmuStats::num_page_flushed << std::endl;
        std::cout << " Total Entries Written : " << EmuStats::total_entries_written << std::endl;
        std::cout << " Total # of Vanilla Compaction : " << EmuStats::total_vanilla_compaction << std::endl;
        std::cout << " Total # of RQD Compaction : " << EmuStats::total_rqd_compaction << std::endl
                  << std::endl
                  << std::endl
                  << std::endl;

        // std::cout << "  ================ Total Entries (Before/After) & Time Taken for Range Query ================ " << std::endl
        //           << std::endl
        //           << std::endl;
        // std::cout << "\t\tBefore Entries\t\t"
        //           << "\tAfter Entries\t\t"
        //           << "\tTime Taken" << std::endl;

        std::ofstream outputFile;
        if (_env->enable_rq_compaction)
        {
            outputFile.open(rq_path + "newRQTime.csv");
        }
        else
        {
            outputFile.open(rq_path + "oldRQTime.csv");
        }

        for (int i = 0; i < EmuStats::num_entries_before_after_range_query.size(); i++)
        {
            auto entries_pair = EmuStats::num_entries_before_after_range_query[i];
            auto time_taken = EmuStats::time_duration_for_range_query[i];

            // std::cout << "\t\t" << entries_pair.first << "\t\t\t\t\t\t" << entries_pair.second << "\t\t\t\t\t\t" << time_taken.count() << std::endl;
            outputFile << entries_pair.first << "," << entries_pair.second << "," << time_taken.count() << std::endl;
        }
        outputFile << std::endl;

        // close the file
        outputFile.close();
    }
}
#include <algorithm>
#include <cmath>

#include "emu_environment.h"
#include "page.h"
#include "sstfile.h"
#include "tree_builder.h"
#include "workload_executor.h"

using namespace workload_exec;

namespace tree_builder
{
    SSTFile *SSTFile::createNewSSTFile(int level_to_flush_in)
    {
        EmuEnv *_env = EmuEnv::getInstance();

        SSTFile *new_file = new SSTFile();
        new_file->max_sort_key = "";
        new_file->min_sort_key = "";

        new_file->pages = Page::createNewPages(ceil((_env->buffer_size_in_pages * 1.0) / (_env->entries_per_page)));  // TODO: Validate this buffer_size_in_pages / entries_per_page ???

        new_file->file_level = level_to_flush_in;
        new_file->next_file_ptr = NULL;
        DiskMetaFile::global_level_file_counter[level_to_flush_in]++;
        new_file->file_id = "L" + std::to_string(level_to_flush_in) + "F" + std::to_string(DiskMetaFile::global_level_file_counter[level_to_flush_in]);
        std::cout << "Creating new file !!" << std::endl;

        return new_file;
    }

    int SSTFile::PopulateFile(SSTFile *file, std::vector<Entry *> vector_to_populate_file, int level_to_flush_in)
    {
        EmuEnv *_env = EmuEnv::getInstance();

        int page_count = file->pages.size();

        if (MemoryBuffer::verbosity == 2)
            std::cout << "In PopulateFile() ... " << std::endl;

        for (int i = 0; i < page_count; i++)
        {
            std::vector<Entry *> vector_to_populate_tile;
            int entries_per_page = Utility::minInt(_env->entries_per_page, vector_to_populate_file.size());
            for (int j = 0; j < entries_per_page; ++j)
            {
                vector_to_populate_tile.push_back(vector_to_populate_file[j]);
            }
            std::sort(vector_to_populate_tile.begin(), vector_to_populate_tile.end(), Utility::sortbysortkey);

            vector_to_populate_file.erase(vector_to_populate_file.begin(), vector_to_populate_file.begin() + entries_per_page);

            std::cout << "\nprinting after trimming " << std::endl;
            for (int j = 0; j < vector_to_populate_file.size(); ++j)
                std::cout << "< " << vector_to_populate_file[j]->getKey() << ",  " << vector_to_populate_file[j]->getValue() << " >"
                          << "\t";

            if (MemoryBuffer::verbosity == 2)
                std::cout << "populating delete tile ... \n";

            int status = SSTFile::PopulatePage(file, vector_to_populate_tile, i, level_to_flush_in);
            vector_to_populate_tile.clear();
        }
        return 1;
    }

    int SSTFile::PopulatePage(SSTFile *file, std::vector<Entry *> entries_to_write, int index, int level_to_flush_in)
    {
        if (MemoryBuffer::verbosity == 2)
        {
            std::cout << "In PopulatePage() ..." << std::endl;
        }

        EmuEnv *_env = EmuEnv::getInstance();
        Page page = file->pages[index];
        std::vector<Entry> entries_to_populate;

        for (int i = 0; i < entries_to_write.size(); i++)
        {
            entries_to_populate.push_back(*entries_to_write[i]);
        }

        page.entries_vector = entries_to_populate;

        if (MemoryBuffer::verbosity == 2)
            std::cout << "populated page : " << index << " at Level : " << level_to_flush_in << std::endl;
        
        entries_to_populate.clear();
        return 1;
    }

}
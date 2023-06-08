#include <string>
#include <vector>

#include "entry.h"
#include "page.h"

#ifndef _SSTFILE_H_
#define _SSTFILE_H_

namespace tree_builder
{
    class SSTFile
    {
    public:
        int file_level;
        std::string file_id;
        std::string min_sort_key;
        std::string max_sort_key;

        std::vector<Page> pages;
        struct SSTFile *next_file_ptr;

        static struct SSTFile *createNewSSTFile(int level_to_flush_in);
        static int PopulateFile(SSTFile *file, std::vector<Entry *> vector_to_populate_file, int level_to_flush_in);
        static int PopulatePage(SSTFile *file, std::vector<Entry*> entries_to_write, int index, int level_to_flush_in);
    };
}

#endif // _SSTFILE_H_
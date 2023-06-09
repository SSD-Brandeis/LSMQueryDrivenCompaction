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

        std::vector<Page *> pages;
        struct SSTFile *next_file_ptr;

        static struct SSTFile *createNewSSTFile(int total_entries, int level_to_flush_in);
        static int PopulateFile(SSTFile *file, std::vector<Entry *> vector_to_populate_file, int level_to_flush_in);
        static int PopulatePage(SSTFile *file, std::vector<Entry *> entries_to_write, int index, int level_to_flush_in);
    };

    class EntryIterator
    {
    private:
        const SSTFile *endSSTFile_;
        SSTFile *start;
        SSTFile *sstFile_;
        int pageIndex_;
        int entryIndex_;

    public:
        EntryIterator(SSTFile *sstFile, const SSTFile *endSSTFile)
            : start(sstFile), sstFile_(sstFile), endSSTFile_(endSSTFile), pageIndex_(0), entryIndex_(0) {}

        // Dereference operator
        const Entry &operator*() const
        {
            return sstFile_->pages[pageIndex_]->entries_vector[entryIndex_];
        }

        // Pre-increment operator
        EntryIterator &operator++()
        {
            // Move to the next entry
            ++entryIndex_;

            // Check if we reached the end of the current page
            if (entryIndex_ >= sstFile_->pages[pageIndex_]->entries_vector.size())
            {
                // Move to the next page
                if (pageIndex_ + 1 < sstFile_->pages.size())
                {
                    pageIndex_++;
                }
                else if (pageIndex_ + 1 >= sstFile_->pages.size() && sstFile_->next_file_ptr != endSSTFile_)
                {
                    sstFile_ = sstFile_->next_file_ptr;
                    pageIndex_ = 0;
                }
                else
                {
                    *this = EntryIterator(nullptr, endSSTFile_);
                }
                entryIndex_ = 0;
            }

            return *this;
        }

        // Equality operator
        bool operator==(const EntryIterator &other) const
        {
            return (sstFile_ == other.sstFile_) &&
                   (endSSTFile_ == other.endSSTFile_);
        }

        // Inequality operator
        bool operator!=(const EntryIterator &other) const
        {
            return !(*this == other);
        }

        // Iterator methods
        EntryIterator begin() const
        {
            if (sstFile_)
            {
                return EntryIterator(start, endSSTFile_);
            }
            return end();
        }

        EntryIterator end() const
        {
            return EntryIterator(nullptr, endSSTFile_);
        }
    };

}

#endif // _SSTFILE_H_
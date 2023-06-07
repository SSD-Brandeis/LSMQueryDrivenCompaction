#include <algorithm>
#include <iostream>

#include "memtable.h"

class VectorMemTable : public MemTable
{
public:
    VectorMemTable() {}

    bool virtual insert(Entry &entry)
    {
        if (entry.getType() != EntryType::POINT_ENTRY) {
            std::cout << "ERROR: Entry should be Point Entry" << std::endl;
            exit(1);
        }
        std::vector<Entry *>::iterator it;
        it = std::find(entries.begin(), entries.end(), entry);

        // Check if entry already exists & UPDATE
        if (it != entries.end())
        {
            entries[it - entries.begin()] = &entry;
        }
        else
        {
            entries.push_back(&entry);
        }

        // TODO: check if needs to flush based on threshold
    }

    bool virtual remove(Entry &entry)
    {
        if (entry.getType() != EntryType::POINT_TOMBSTONE) {
            std::cout << "ERROR: Entry should be Point Tombstone" << std::endl;
            exit(1);
        }
        std::vector<Entry *>::iterator it;
        it = std::find(entries.begin(), entries.end(), entry);

        // Check if entry already exists in MemTable
        if (it != entries.end()) {
            entries.erase(it);
        }
        entries.push_back(&entry);
    }
};

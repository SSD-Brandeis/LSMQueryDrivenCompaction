#include <vector>

#include "entry.h"

#ifndef _MEMTABLE_H_
#define _MEMTABLE_H_

class VectorMemTable;

class MemTable
{
protected:
    void virtual checkMemTableFull();

public:
    std::vector<Entry *> entries{}; // Change this to generic container
    MemTable();
    ~MemTable();

    /*
     * Insert or Update an entry into Memtable (The update would work only in-memory)
     * The implementation coud be different based on type of memetable
     * Type can be skiplist, vector, linklist any
     */
    bool virtual insert(Entry &entry);

    /*
     * Delete an entry from the Memtable (If the entry exists in-memory remove
     * and add tombstone for older, otherwise just add tombstone for older)
     */
    bool virtual remove(Entry &entry);

    /*
     * Get the key index and value if exists in MemTable
     */
    std::pair<int, std::string> virtual get(Entry &entry);

    Entry &operator[](int index);
};

#endif // _MEMTABLE_H_
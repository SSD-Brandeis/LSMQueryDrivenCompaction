#include <vector>

#include "entry.h"

#ifndef _MEMTABLE_H_
#define _MEMTABLE_H_

class MemTable
{
private:
    std::vector<Entry *> entries;

public:
    MemTable();
    /*
     * Insert or Update an entry into Memtable (The update would work only in-memory)
     * The implementation coud be different based on type of memetable
     * Type can be skiplist, vector, linklist any
     */
    bool insert(Entry &entry);
    /*
     * Delete an entry from the Memtable (If the entry exists in-memory remove
     * and add tombstone for older, otherwise just add tombstone for older)
     */
    bool remove(Entry &entry);
    Entry &operator[](int index);

    std::vector<Entry *>::const_iterator begin()
    {
        return entries.begin();
    }

    std::vector<Entry *>::const_iterator end()
    {
        return entries.end();
    }

    int size()
    {
        return entries.size();
    }

    /*
     * Clear memtable buffer entries
     */
    bool clear()
    {
        entries.clear();
        return true;
    }
};

#endif // _MEMTABLE_H_
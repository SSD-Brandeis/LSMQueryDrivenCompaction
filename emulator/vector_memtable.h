#include "memtable.h"

#ifndef _VECTOR_MEMTABLE_H_
#define _VECTOR_MEMTABLE_H_

class VectorMemTable : public MemTable
{
    protected:
        void virtual checkMemTableFull() override;
    public:
        VectorMemTable();
        ~VectorMemTable();
        bool virtual insert(Entry &entry) override;
        bool virtual remove(Entry &entry) override;
};

#endif // _VECTOR_MEMTABLE_H_
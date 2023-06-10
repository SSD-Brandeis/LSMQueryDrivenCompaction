#include "memtable.h"

MemTable::MemTable() {}

MemTable::~MemTable() {}

void MemTable::checkMemTableFull() {}

bool MemTable::insert(Entry &entry) { return 0; }

bool MemTable::remove(Entry &entry) { return 0; }

std::pair<int, std::string> MemTable::get(Entry &entry) { return std::make_pair(-1, "Invalid Call"); }

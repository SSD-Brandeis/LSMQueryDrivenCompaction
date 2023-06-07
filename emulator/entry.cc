#include "entry.h"

Entry::Entry(std::string key, std::string value) : key{key}, value{value}, entry_type{EntryType::POINT_ENTRY} {}

Entry::Entry(std::string key, std::string value, EntryType entry_type): Entry{key, value, entry_type} {}

Entry::Entry(const Entry &other): Entry{other.key, other.value, other.entry_type} {
    this->timetag = other.timetag;    
}

Entry::Entry(Entry &&other): key{other.key}, value{other.value}, entry_type{other.entry_type}, timetag{other.timetag} {
    other.key = nullptr;
    other.value = nullptr;
    other.entry_type = NO_TYPE;
    other.timetag = 0;
}

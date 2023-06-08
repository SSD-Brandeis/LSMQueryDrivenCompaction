#include "entry.h"

Entry::Entry(std::string key, std::string value) : key{key}, value{value}, entry_type{EntryType::POINT_ENTRY} {}

Entry::Entry(std::string key, std::string value, EntryType entry_type) : key{key}, value{value}, entry_type{entry_type} {}

Entry::Entry(const Entry &other) : Entry{other.key, other.value, other.entry_type}
{
    this->timetag = other.timetag;
}

bool Entry::operator==(const Entry &other)
{
    if (this == &other)
    {
        return true;
    }
    else if (this->key == other.key && this->entry_type == other.entry_type && this->value == other.value)
    {
        return true;
    }
    return false;
}

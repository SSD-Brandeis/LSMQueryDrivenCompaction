#include <string>

#ifndef _ENTRY_H_
#define _ENTRY_H_

/*
 * Enum for PointEntry and PointTombston
 */
enum EntryType;

/*
 * Entry could be point entry, point delete(tombstone)
 * Each entry will have:
 *  - enum type [PointEntry, PointTombston]
 *  - string key
 *  - string value
 *  - long timetag
 */
class Entry
{
private:
    EntryType entry_type;
    std::string key;
    std::string value;
    long timetag;

public:
    Entry(std::string key, std::string value);
    Entry(std::string key, std::string value, EntryType entry_type); // Constructor
    Entry(const Entry &other);                 // copy constructor
    Entry(Entry &&other);                      // move constructor
    bool operator==(const Entry &other);       // comparison operator
};

/*
 * Enum for PointEntry and PointTombston
 */
enum EntryType
{
    NO_TYPE = 0,
    POINT_ENTRY = 1,
    POINT_TOMBSTONE = 2
};

#endif // _ENTRY_H_

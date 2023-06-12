/*
 *  Created on: May 14, 2019
 *  Author: Subhadeep, Papon
 */

#include "emu_environment.h"
#include "memtable.h"
#include "sstfile.h"

#include <iostream>
#include <vector>
#include <queue>

using namespace std;

namespace tree_builder
{
  class MemoryBuffer
  {
  private:
    MemoryBuffer(EmuEnv *_env);
    static MemoryBuffer *buffer_instance;
    static long max_buffer_size;

  public:
    static float buffer_flush_threshold;
    static long current_buffer_entry_count;
    static long current_buffer_size;
    static float current_buffer_saturation;
    static int buffer_flush_count;
    static MemTable *buffer;
    static int verbosity;

    static MemoryBuffer *getBufferInstance(EmuEnv *_env);
    static int getCurrentBufferStatistics();
    static int setCurrentBufferStatistics(int entry_count_change, int buffer_flush_threshold);
    static int initiateBufferFlush(int level_to_flush_in);
    static int printBufferEntries();
  };

  class DiskMetaFile
  {
  private:
    static pair<long, long> getMatchingKeyFile(long min_key, long max_key, int key_level); //??? Definition change hobe

  public:
    // static SSTFile* head_level_1;
    static int checkAndAdjustLevelSaturation(int level);
    static long getLevelEntryCount(int level);
    static int getLevelFileCount(int level);
    static int getTotalLevelCount();
    static std::vector<int> getNonEmptyLevels();
    static int checkOverlapping(SSTFile *file, int level);

    static int setSSTFileHead(SSTFile *arg, int level);
    static SSTFile *getSSTFileHead(int level);

    static void getMetaStatistics();
    static int printAllEntries(int only_file_meta_data);
    static int getTotalPageCount();
    static int clearAllEntries();

    static SSTFile *level_head[32];

    static long level_min_key[32];
    static long level_max_key[32];
    static long level_file_count[32];
    static long level_entry_count[32];
    static long level_current_size[32];

    static long level_max_size[32];
    static long level_max_file_count[32];
    static long global_level_file_counter[32];
    static float disk_run_flush_threshold[32];

    static int compaction_counter[32];
    static int compaction_through_sortmerge_counter[32];
    static int compaction_through_point_manipulation_counter[32];
    static int compaction_file_counter[32];

    ////static disk_run_flush_threshold;
  };

  class LevelIterator
  {
  private:
    int level_;
    std::string target_;
    EntryIterator entry_iterator;

  public:
    LevelIterator(int level, std::string target)
        : level_(level), target_(target), entry_iterator(DiskMetaFile::level_head[level], nullptr) {}

    // Dereference operator
    const Entry &operator*() const
    {
      return *entry_iterator;
    }

    // Pre-increment operator
    LevelIterator &operator++()
    {
      ++entry_iterator;
      return *this;
    }

    // Equality operator
    bool operator==(const LevelIterator &other) const
    {
      return (level_ == other.level_) &&
             (target_ == other.target_) &&
             (entry_iterator == other.entry_iterator);
    }

    // Inequality operator
    bool operator!=(const LevelIterator &other) const
    {
      return !(*this == other);
    }

    // Assignment operator
    LevelIterator &operator=(const LevelIterator &other)
    {
      // Perform member-wise assignment
      if (this != &other)
      {
        this->level_ = other.level_;
        this->target_ = other.target_;
        this->entry_iterator = other.entry_iterator;
        return *this;
      }
      return *this;
    }

    int getLevel()
    {
      return this->level_;
    }

    // Iterator methods
    LevelIterator begin()
    {
      if (entry_iterator != entry_iterator.end())
      {
        this->entry_iterator.seek(target_);
        return *this;
      }
      return end();
    }

    LevelIterator end() const
    {
      auto level_end = LevelIterator(level_, target_);
      level_end.entry_iterator = level_end.entry_iterator.end();
      return level_end;
    }
  };

  class RangeIterator
  {
  private:
    std::string target_;
    std::vector<LevelIterator> level_iterators;
    Entry *current_entry;

    struct IteratorComparator
    {
      bool operator()(const LevelIterator &lhs, const LevelIterator &rhs) const
      {
        // Compare the current entries pointed by the iterators
        if ((*lhs).getKey().compare((*rhs).getKey()) == 0)
        {
          return (*lhs).getTimeTag() < (*rhs).getTimeTag();
        }
        return (*lhs).getKey().compare((*rhs).getKey()) > 0;
      }
    };

    priority_queue<LevelIterator, std::vector<LevelIterator>, IteratorComparator> level_iterators_queue;

  public:
    RangeIterator(std::vector<LevelIterator> level_iterators, std::string target)
        : level_iterators(level_iterators), current_entry(nullptr), target_(target) {}
    RangeIterator() : level_iterators(), target_(), current_entry(nullptr) {}

    // Dereference operator
    const Entry &operator*() const
    {
      return *current_entry;
    }

    // Pre-increment operator
    RangeIterator &operator++()
    {
      if (!level_iterators_queue.empty())
      {
        LevelIterator level_itr = level_iterators_queue.top();
        Entry level_entry = *level_itr;

        // increment the level iterator and push back if still valid
        ++level_itr;
        level_iterators_queue.pop();
        if (level_itr != level_itr.end())
        {
          level_iterators_queue.push(level_itr);
        }

        // if not tombstone just return and increment the required iterator
        while (!level_iterators_queue.empty() && level_entry.getKey().compare((*level_iterators_queue.top()).getKey()) == 0)
        {
          if (MemoryBuffer::verbosity == 2)
          {
            auto level_ = level_iterators_queue.top();
            std::cout << "May skip older entries from lower level ... " << std::endl;
            std::cout << "Skipping ... Key: " << (*level_iterators_queue.top()).getKey() << " from Level: " << level_.getLevel() << std::endl;
          }
          level_itr = level_iterators_queue.top();
          ++level_itr;
          level_iterators_queue.pop();
          if (level_itr != level_itr.end())
          {
            level_iterators_queue.push(level_itr);
          }
        }

        if (level_entry.getType() != EntryType::POINT_TOMBSTONE)
        {
          current_entry = new Entry(level_entry);
          return *this;
        }
        else
        {
          if (MemoryBuffer::verbosity == 2)
          {
            std::cout << "Found Tombstone for Key : " << level_entry.getKey() << std::endl;
          }
          // level entry is tombstone
          return ++(*this);
        }
      }
      else
      {
        *this = RangeIterator();
      }
      return *this;
    }

    // Equality operator
    bool operator==(const RangeIterator &other) const
    {
      return (target_ == other.target_) && (((!level_iterators_queue.empty() && !other.level_iterators_queue.empty()) &&
                                             (level_iterators_queue.top() == other.level_iterators_queue.top())) ||
                                            (level_iterators_queue.empty() & other.level_iterators_queue.empty()));
    }

    RangeIterator &operator=(const RangeIterator &other)
    {
      if (this != &other)
      {
        target_ = other.target_;
        level_iterators = other.level_iterators;
        level_iterators_queue = other.level_iterators_queue;
        current_entry = other.current_entry;
      }
      return *this;
    }

    // Inequality operator
    bool operator!=(const RangeIterator &other) const
    {
      return !(*this == other);
    }

    // Iterator methods
    RangeIterator begin()
    {
      if (level_iterators.size() > 0)
      {
        while (!this->level_iterators_queue.empty())
        {
          this->level_iterators_queue.pop();
        }

        for (auto level_itr : this->level_iterators)
        {
          this->level_iterators_queue.push(level_itr);
        }

        return ++(*this);
      }
      return end();
    }

    RangeIterator end() const
    {
      return RangeIterator();
    }
  };

} // namespace

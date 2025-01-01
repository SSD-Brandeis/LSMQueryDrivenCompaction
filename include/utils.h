#ifndef UTILS_H_
#define UTILS_H_

void PrintExperimentalSetup(DBEnv *env, Buffer *buffer);
void PrintRocksDBPerfStats(DBEnv *env, Buffer *buffer, Options options);
void UpdateProgressBar(DBEnv *env, size_t current, size_t total,
                       size_t update_interval = 1000, size_t bar_width = 50);

#ifdef PROFILE
void LogTreeState(rocksdb::DB *db, Buffer *buffer);
void LogRocksDBStatistics(rocksdb::DB *db, const rocksdb::Options &options,
                          Buffer *buffer);
#endif // PROFILE
#endif // UTILS_H_
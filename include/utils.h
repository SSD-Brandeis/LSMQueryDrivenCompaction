#ifndef UTILS_H_
#define UTILS_H_

void PrintExperimentalSetup(DBEnv *env, Buffer *buffer);
void PrintRocksDBPerfStats(DBEnv *env, Buffer *buffer);

#ifdef PROFILE
void LogTreeState(rocksdb::DB *db, Buffer *buffer);
void LogRocksDBStatistics(rocksdb::DB *db, const rocksdb::Options &options,
                          Buffer *buffer);
#endif // PROFILE
#endif // UTILS_H_
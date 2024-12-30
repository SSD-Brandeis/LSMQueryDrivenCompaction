#ifndef RUN_WORKLOAD_H_
#define RUN_WORKLOAD_H_

#include "db_env.h"

extern std::string kDBPath;
extern std::string buffer_file;

int runWorkload(DBEnv *env);

#endif // RUN_WORKLOAD_H_
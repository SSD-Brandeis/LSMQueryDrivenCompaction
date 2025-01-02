#include "db_env.h"

std::unique_ptr<DBEnv> DBEnv::instance_ = nullptr;
std::mutex DBEnv::mutex_;
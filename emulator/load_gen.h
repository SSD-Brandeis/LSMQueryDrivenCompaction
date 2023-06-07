#ifndef _LOAD_GEN_H_
#define _LOAD_GEN_H_

void generate_workload(int argc, char *argv[], long num_inserts, long num_updates, long num_point_deletes, long num_point_queries, long num_range_queries, float range_query_selectivity);

#endif // _LOAD_GEN_H_

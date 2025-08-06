#!/bin/bash

ENTRY_SIZE=128
LAMBDA=0.125

INSERTS=8388608
UPDATES=8388608
POINT_QUERIES=0
POINT_DELETES=0
RANGE_QUERIES=9000
SELECTIVITY=0.1
RANGE_DELETES=100
RANGE_DELETES_SEL=0.01

LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO})" | bc)

# ./bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}

rm -f load_gen_massif.out load_gen_report.txt
echo ./bin/load_gen -I ${INSERTS} -U ${UPDATES} -Q ${POINT_QUERIES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -R ${RANGE_DELETES} -y ${RANGE_DELETES_SEL} -E ${ENTRY_SIZE} -L ${LAMBDA}
valgrind --tool=massif --pages-as-heap=yes --massif-out-file=load_gen_massif.out ./bin/load_gen -I ${INSERTS} -U ${UPDATES} -Q ${POINT_QUERIES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -R ${RANGE_DELETES} -y ${RANGE_DELETES_SEL} -E ${ENTRY_SIZE} -L ${LAMBDA}
ms_print load_gen_massif.out > load_gen_report.txt

# rm -rf db
# rm -f vanilla_massif.out vanilla_report.txt
# valgrind --tool=massif --pages-as-heap=yes --massif-out-file=vanilla_massif.out ./bin/working_version -E ${ENTRY_SIZE} -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -T ${SIZE_RATIO} --progress 1
# ms_print vanilla_massif.out > vanilla_report.txt

# rm -rf db
# rm -f rr_massif.out rr_report.txt
# valgrind --tool=massif --pages-as-heap=yes --massif-out-file=rr_massif.out ./bin/working_version -E ${ENTRY_SIZE} -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --progress 1
# ms_print rr_massif.out > rr_report.txt
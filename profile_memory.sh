#!/bin/bash

ENTRY_SIZE=1024
LAMBDA=0.125
ENTRIES_PER_PAGE=4
PAGES_PER_FILE=1024
SIZE_RATIO=2

INSERTS=80000
UPDATES=80000
RANGE_QUERIES=100
SELECTIVITY=0.1
LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO})" | bc)

# ./bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}

rm -rf db
rm -f vanilla_massif.out vanilla_report.txt
valgrind --tool=massif --pages-as-heap=yes --massif-out-file=vanilla_massif.out ./bin/working_version -E ${ENTRY_SIZE} -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -T ${SIZE_RATIO} --progress 1
ms_print vanilla_massif.out > vanilla_report.txt

rm -rf db
rm -f rr_massif.out rr_report.txt
valgrind --tool=massif --pages-as-heap=yes --massif-out-file=rr_massif.out ./bin/working_version -E ${ENTRY_SIZE} -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --progress 1
ms_print rr_massif.out > rr_report.txt
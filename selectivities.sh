#!/bin/bash

TAG=selectivityplots
ENTRY_SIZE=128
LAMBDA=0.125
ENTRIES_PER_PAGE=32
PAGES_PER_FILE=1024
SIZE_RATIO=6

INSERTS=8388608
RANGE_QUERY_PERCENT=(0.00048828125 0.0009765625 0.001953125) # 0.00390625 0.0078125 0.015625 0.03125 0.0625 0.125 0.25 0.5)
SELECTIVITY=0.1

SHOW_PROGRESS=1
VERSION=0
SANITY_CHECK=0
USE_DB=0
SNAP=0
MAX_TRIVIAL_MOVE=1

echo "Starting experiments with TAG=${TAG}, ENTRY_SIZE=${ENTRY_SIZE}"

LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO})" | bc)

for RQ_PERCENT in "${RANGE_QUERY_PERCENT[@]}"
do
    RANGE_QUERIES=$(echo "(${INSERTS} * ${RQ_PERCENT}) + 0.5" | bc | awk '{printf "%d\n", $0}')
    UPDATES=$(echo "${INSERTS} - ${RANGE_QUERIES}" | bc)

    echo "Debug: INSERTS=${INSERTS}, UPDATES=${UPDATES}, RANGE_QUERIES=${RANGE_QUERIES}"
    EXP_DIR="experiments-${TAG}-U${UPDATES}-E${ENTRY_SIZE}-B${ENTRIES_PER_PAGE}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${SIZE_RATIO}"
    echo "Debug: EXP_DIR=${EXP_DIR}"

    cd .vstats
    mkdir -p $EXP_DIR
    cd $EXP_DIR

    mkdir -p RocksDB RangeReduce[lb=T^-1ANDre=1] # RocksDBTuned RangeReduce[lb=0] RangeReduce[lb=T^-1] 

    echo "Generating workload..."
    cd RocksDB
    echo "../../../bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}"
    ../../../bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}

    # echo "Copying workload to RocksDBTuned..."
    # cd ../RocksDBTuned
    # if [ -f "../RocksDB/workload.txt" ]; then
    #     cp ../RocksDB/workload.txt ./workload.txt
    #     echo "workload.txt copied successfully"
    # else
    #     echo "Error: workload.txt not found in RocksDB"
    #     exit 1
    # fi

    # echo "Copying workload to RangeReduce[lb=T^-1]..."
    # cd ../RangeReduce[lb=T^-1]
    # if [ -f "../RocksDB/workload.txt" ]; then
    #     cp ../RocksDB/workload.txt ./workload.txt
    #     echo "workload.txt copied successfully"
    # else
    #     echo "Error: workload.txt not found in RocksDB"
    #     exit 1
    # fi

    echo "Copying workload to RangeReduce[lb=T^-1ANDre=1]..."
    cd ../RangeReduce[lb=T^-1ANDre=1]
    if [ -f "../RocksDB/workload.txt" ]; then
        cp ../RocksDB/workload.txt ./workload.txt
        echo "workload.txt copied successfully"
    else
        echo "Error: workload.txt not found in RocksDB"
        exit 1
    fi

    # echo "Copying workload to RangeReduce[lb=0]..."
    # cd ../RangeReduce[lb=0]
    # if [ -f "../RocksDB/workload.txt" ]; then
    #     cp ../RocksDB/workload.txt ./workload.txt
    #     echo "workload.txt copied successfully"
    # else
    #     echo "Error: workload.txt not found in RocksDB"
    #     exit 1
    # fi

    echo "Running RocksDB workload..."
    cd ../RocksDB
    ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 0 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb 0 --snap ${SNAP} --tmv ${MAX_TRIVIAL_MOVE}
    rm -rf db

    # echo "Running RocksDBTuned workload..."
    # cd ../RocksDBTuned
    # ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 0 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb ${USE_DB} --snap ${SNAP}
    # rm -rf db

    # echo "Running RangeReduce[lb=T^-1] workload [with lb=${LOWER_BOUND}]..."
    # cd ../RangeReduce[lb=T^-1]
    # ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --re 0 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb ${USE_DB} --snap ${SNAP}
    # rm -rf db

    echo "Running RangeReduce[lb=T^-1ANDre=1] workload [with lb=${LOWER_BOUND} && re=1]..."
    cd ../RangeReduce[lb=T^-1ANDre=1]
    ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --re 1 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb 0 --snap ${SNAP}
    rm -rf db

    # echo "Running RangeReduce[lb=0] workload [with lb=0 && re=0]..."
    # cd ../RangeReduce[lb=0]
    # ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb 0 --re 0 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb ${USE_DB} --snap ${SNAP}
    # rm -rf db

    cd ../../..
done
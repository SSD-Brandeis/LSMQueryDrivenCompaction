#!/bin/bash

TAG=rangereduceratio
ENTRY_SIZE=128
LAMBDA=0.125
ENTRIES_PER_PAGE=32
PAGES_PER_FILE=1024
SIZE_RATIO=6

INSERTS=8388608
UPDATES=8388608
RANGE_QUERIES=9000
SELECTIVITY=0.1
# SELECTIVITIES=(0.1 0.05 0.01 0.001 0.0001 0.00001)
EPSILONS=(1 2 4 8 0.5 0.25 0.125)
# SELECTIVITY=0.1
RANGE_QUERY_OVERLAPPING_COUNT=100
RANGE_QUERY_OVERLAPPING_PERCENT=1

SHOW_PROGRESS=1
VERSION=0
SANITY_CHECK=0
USE_DB=0
SNAP=0
MAX_TRIVIAL_MOVE=1

echo "Starting experiments with TAG=${TAG}, ENTRY_SIZE=${ENTRY_SIZE}"
echo "Debug: INSERTS=${INSERTS}, UPDATES=${UPDATES}, RANGE_QUERIES=${RANGE_QUERIES}"

# for SELECTIVITY in "${SELECTIVITIES[@]}"; do
    # LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO}*${EPSILON})" | bc)
    EXP_DIR="experiments-${TAG}-U${UPDATES}-E${ENTRY_SIZE}-B${ENTRIES_PER_PAGE}-P${PAGES_PER_FILE}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${SIZE_RATIO}"
    echo "Debug: EXP_DIR=${EXP_DIR}"

    cd .vstats || exit
    mkdir -p $EXP_DIR
    cd $EXP_DIR || exit

#     mkdir -p RocksDB  # RangeReduce[lb=T^-1ANDre=1] RangeReduce[lb=0] RangeReduce[lb=0ANDsmlck=0] RocksDBTuned RangeReduce[lb=T^-1]

# for EPSILON in "${EPSILONS[@]}"; do
#     mkdir -p "RangeReduce[lb=T^-1]${EPSILON}"
# done

    echo "Generating workload..."
    cd RocksDB || exit
    # echo "../../../bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}"  # -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}"
    # ../../../bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}  # -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}

    # echo "Copying workload to RocksDBTuned..."
    # cd ../RocksDBTuned || exit
    # if [ -f "../RocksDB/workload.txt" ]; then
    #     cp ../RocksDB/workload.txt ./workload.txt
    #     echo "workload.txt copied successfully"
    # else
    #     echo "Error: workload.txt not found in RocksDB"
    #     exit 1
    # fi

# for EPSILON in "${EPSILONS[@]}"; do
#     echo "Copying workload to RangeReduce[lb=T^-1]..."
#     cd "../RangeReduce[lb=T^-1]${EPSILON}" || exit
#     if [ -f "../RocksDB/workload.txt" ]; then
#         cp ../RocksDB/workload.txt ./workload.txt
#         echo "workload.txt copied successfully"
#     else
#         echo "Error: workload.txt not found in RocksDB"
#         exit 1
#     fi
# done

    # echo "Copying workload to RangeReduce[lb=T^-1ANDre=1]..."
    # cd ../RangeReduce[lb=T^-1ANDre=1] || exit
    # if [ -f "../RocksDB/workload.txt" ]; then
    #     cp ../RocksDB/workload.txt ./workload.txt
    #     echo "workload.txt copied successfully"
    # else
    #     echo "Error: workload.txt not found in RocksDB"
    #     exit 1
    # fi

    # echo "Copying workload to RangeReduce[lb=0]..."
    # cd ../RangeReduce[lb=0] || exit
    # if [ -f "../RocksDB/workload.txt" ]; then
    #     cp ../RocksDB/workload.txt ./workload.txt
    #     echo "workload.txt copied successfully"
    # else
    #     echo "Error: workload.txt not found in RocksDB"
    #     exit 1
    # fi

    # echo "Copying workload to RangeReduce[lb=0ANDsmlck=0]..."
    # cd ../RangeReduce[lb=0ANDsmlck=0] || exit
    # if [ -f "../RocksDB/workload.txt" ]; then
    #     cp ../RocksDB/workload.txt ./workload.txt
    #     echo "workload.txt copied successfully"
    # else
    #     echo "Error: workload.txt not found in RocksDB"
    #     exit 1
    # fi

    echo "Running RocksDB workload..."
    cd ../RocksDB || exit
    ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 0 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb 0 --snap ${SNAP} --tmv ${MAX_TRIVIAL_MOVE}
    rm -rf db

    # echo "Running RocksDBTuned workload..."
    # cd ../RocksDBTuned || exit
    # ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 0 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb ${USE_DB} --snap ${SNAP}
    # rm -rf db

for EPSILON in "${EPSILONS[@]}"; do
    LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO}*${EPSILON})" | bc)
    echo "Running RangeReduce[lb=T^-1] workload [with lb=${LOWER_BOUND}]..."
    cd "../RangeReduce[lb=T^-1]${EPSILON}" || exit
    # echo "Moving saveddb from RocksDBTuned to RangeReduce[lb=T^-1]"
    # mv ../RocksDBTuned/saveddb ./
    ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --re 0 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb ${USE_DB} --snap ${SNAP}
    rm -rf db
done

    # echo "Running RangeReduce[lb=T^-1ANDre=1] workload [with lb=${LOWER_BOUND} && re=1]..."
    # cd ../RangeReduce[lb=T^-1ANDre=1]
    # ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --re 1 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb ${USE_DB} --snap ${SNAP}
    # rm -rf db

    # echo "Running RangeReduce[lb=0] workload [with lb=0 && re=0]..."
    # cd ../RangeReduce[lb=0] || exit
    # # echo "Moving saveddb from RangeReduce[lb=T^-1] RangeReduce[lb=0]"
    # # mv ../RangeReduce[lb=T^-1]/saveddb ./
    # ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb 0 --re 0 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb ${USE_DB} --snap ${SNAP}
    # rm -rf db

    # echo "Running RangeReduce[lb=0ANDsmlck=0] workload [with lb=0 && re=0 && smlck=0]..."
    # cd ../RangeReduce[lb=0ANDsmlck=0] || exit
    # # echo "Moving saveddb from RangeReduce[lb=T^-1] RangeReduce[lb=0ANDsmlck=0]"
    # # mv ../RangeReduce[lb=T^-1]/saveddb ./
    # ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb 0 --re 0 --progress ${SHOW_PROGRESS} -V ${VERSION} --sanity ${SANITY_CHECK} --usedb ${USE_DB} --snap ${SNAP} --epl 0
    # rm -rf db

    # cd ../RocksDBTuned
    # echo "Moving saveddb back to RocksDBTuned"
    # mv ../RangeReduce[lb=0ANDsmlck=0]/saveddb ./

    cd ../../..
done
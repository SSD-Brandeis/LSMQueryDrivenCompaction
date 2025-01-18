#!/bin/bash

TAG=paperplots2
ENTRY_SIZE=1024
LAMBDA=0.125
ENTRIES_PER_PAGE=4
PAGES_PER_FILE=16
SIZE_RATIO=6

INSERTS=1048576
UPDATES=262144
RANGE_QUERIES=900
SELECTIVITY=0.1

SHOW_PROGRESS=1

echo "Starting experiments with TAG=${TAG}, ENTRY_SIZE=${ENTRY_SIZE}"
echo "Debug: INSERTS=${INSERTS}, UPDATES=${UPDATES}, RANGE_QUERIES=${RANGE_QUERIES}"

LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO})" | bc)

EXP_DIR="experiments-${TAG}-U${UPDATES}-E${ENTRY_SIZE}-B${ENTRIES_PER_PAGE}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${SIZE_RATIO}"
echo "Debug: EXP_DIR=${EXP_DIR}"

cd .vstats
mkdir -p $EXP_DIR
cd $EXP_DIR

mkdir -p VanillaRandom "RangeReduceRandom" RangeReduceRandomRE1 # RangeReduceRandom0

echo "Generating workload..."
cd VanillaRandom
echo "../../../bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}"
../../../bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}

# echo "Copying workload to RangeReduceRandom0..."
# cd ../RangeReduceRandom0
# if [ -f "../VanillaRandom/workload.txt" ]; then
#     cp ../VanillaRandom/workload.txt ./workload.txt
#     echo "workload.txt copied successfully"
# else
#     echo "Error: workload.txt not found in VanillaRandom"
#     exit 1
# fi

echo "Copying workload to RangeReduceRandom..."
cd ../RangeReduceRandom
if [ -f "../VanillaRandom/workload.txt" ]; then
    cp ../VanillaRandom/workload.txt ./workload.txt
    echo "workload.txt copied successfully"
else
    echo "Error: workload.txt not found in VanillaRandom"
    exit 1
fi

echo "Copying workload to RangeReduceRandomRE1..."
cd ../RangeReduceRandomRE1
if [ -f "../VanillaRandom/workload.txt" ]; then
    cp ../VanillaRandom/workload.txt ./workload.txt
    echo "workload.txt copied successfully"
else
    echo "Error: workload.txt not found in VanillaRandom"
    exit 1
fi

echo "Running VanillaRandom workload..."
cd ../VanillaRandom
../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 0 --progress ${SHOW_PROGRESS}
rm -rf db

# echo "Running RangeReduceRandom workload [with lb=0]..."
# cd ../RangeReduceRandom0
# ../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb 0 --re 0
# rm -rf db

echo "Running RangeReduceRandom workload [with lb=${LOWER_BOUND}]..."
cd ../RangeReduceRandom
../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --re 0 --progress ${SHOW_PROGRESS}
rm -rf db

echo "Running RangeReduceRandomRE1 workload [with lb=${LOWER_BOUND} && re=1]..."
cd ../RangeReduceRandomRE1
../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --re 1 --progress ${SHOW_PROGRESS}
rm -rf db

cd ../../..
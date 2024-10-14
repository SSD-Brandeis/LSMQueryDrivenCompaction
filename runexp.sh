#!/bin/bash

TAG=heatmap4
ENTRY_SIZE=16
ENTRIES_PER_PAGE=64
PAGES_PER_FILE=64
SIZE_RATIO=6

INSERTS=4500000
UPDATES=1125000
RANGE_QUERIES=9000
SELECTIVITY=0.1
OVERLAPPING_RANGE_QUERIES=100
OVERLAPPING_PERCENTAGE=0.98

LOWER_BOUND=$(echo "scale=9; ${SIZE_RATIO}/(2^6)" | bc)
UPPER_BOUND=$(echo "scale=9; ${SIZE_RATIO}/(2^5)" | bc)

EXP_DIR="experiments-${TAG}-E${ENTRY_SIZE}-B${ENTRIES_PER_PAGE}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${SIZE_RATIO}"

cd .vstats
mkdir -p $EXP_DIR
cd $EXP_DIR

mkdir -p VanillaRandom RangeReduceRandom VanillaOverlappingFull RangeReduceOverlappingFull VanillaOverlappingPartial RangeReduceOverlappingPartial

echo "Generating VanillaRandom workload..."
cd VanillaRandom
../../../bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE}

echo "Copying VanillaRandom workload to RangeReduceRandom..."
cd ../RangeReduceRandom
if [ -f "../VanillaRandom/workload.txt" ]; then
    cp ../VanillaRandom/workload.txt ./workload.txt
else
    echo "Error: workload.txt not found in VanillaRandom"
    exit 1
fi

echo "Generating VanillaOverlappingFull workload..."
cd ../VanillaOverlappingFull
../../../bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -O ${OVERLAPPING_RANGE_QUERIES}

echo "Copying VanillaOverlappingFull workload to RangeReduceOverlappingFull..."
cd ../RangeReduceOverlappingFull
if [ -f "../VanillaOverlappingFull/workload.txt" ]; then
    cp ../VanillaOverlappingFull/workload.txt ./workload.txt
else
    echo "Error: workload.txt not found in VanillaOverlappingFull"
    exit 1
fi

echo "Generating VanillaOverlappingPartial workload..."
cd ../VanillaOverlappingPartial
../../../bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -O ${OVERLAPPING_RANGE_QUERIES} --PO ${OVERLAPPING_PERCENTAGE}

echo "Copying VanillaOverlappingPartial workload to RangeReduceOverlappingPartial..."
cd ../RangeReduceOverlappingPartial
if [ -f "../VanillaOverlappingPartial/workload.txt" ]; then
    cp ../VanillaOverlappingPartial/workload.txt ./workload.txt
else
    echo "Error: workload.txt not found in VanillaOverlappingPartial"
    exit 1
fi

echo "Workload generation completed successfully."

echo "Running VanillaRandom workload..."
cd ../VanillaRandom
../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 0 > workload.log
rm -rf db

echo "Running RangeReduceRandom workload..."
cd ../RangeReduceRandom
../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --ub ${UPPER_BOUND} > workload.log
rm -rf db

echo "Running VanillaOverlappingFull workload..."
cd ../VanillaOverlappingFull
../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 0 > workload.log
rm -rf db

echo "Running RangeReduceOverlappingFull workload..."
cd ../RangeReduceOverlappingFull
../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --ub ${UPPER_BOUND} > workload.log
rm -rf db

echo "Running VanillaOverlappingPartial workload..."
cd ../VanillaOverlappingPartial
../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 0 > workload.log
rm -rf db

echo "Running RangeReduceOverlappingPartial workload..."
cd ../RangeReduceOverlappingPartial
../../../bin/working_version -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} -P ${PAGES_PER_FILE} -T ${SIZE_RATIO} --rq 1 --lb ${LOWER_BOUND} --ub ${UPPER_BOUND} > workload.log
rm -rf db
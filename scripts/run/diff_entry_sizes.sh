#!/bin/bash
set -e

bash ./scripts/rebuild.sh
ROOT_DIR=~/LSMQueryDrivenCompaction

TAG=different-entry-sizes
ENTRY_SIZES=(1024 512 256 128 64 32)
LAMBDA=0.125
ENTRIES_PER_PAGE=(4 8 16 32 64 128)
PAGES_PER_FILE=1024
SIZE_RATIO=6

INSERTS=(1048576 2097152 4194304 8388608 16777216 33554432)
# UPDATES=8388608
RANGE_QUERIES=9000
SELECTIVITY=0.1

SHOW_PROGRESS=1
VERSION=0
SANITY_CHECK=0
USE_DB=0
SNAP=0

echo "Starting experiments with TAG=${TAG}"


for i in "${!ENTRY_SIZES[@]}"; do
    inserts=$(( ${INSERTS[$i]} / 2))
    UPDATES=$(( ${INSERTS[$i]} / 2))
    entry_size=${ENTRY_SIZES[$i]}
    entries_per_page=${ENTRIES_PER_PAGE[$i]}

    LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO})" | bc)
    
    echo "Debug: INSERTS=${inserts}, UPDATES=${UPDATES}, RANGE_QUERIES=${RANGE_QUERIES}"
    EXP_DIR="experiments-${TAG}-U${UPDATES}-E${entry_size}-B${entries_per_page}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${SIZE_RATIO}"
    echo "Debug: EXP_DIR=${EXP_DIR}"

    mkdir -p .vstats
    cd .vstats || exit
    mkdir -p "$EXP_DIR"
    cd "$EXP_DIR" || exit

    mkdir -p RocksDB RangeReduce[lb=0] RangeReduce[lb=T^-1] RangeReduce[lb=T^-1ANDre=1]

    # echo "Generating specs for Tectonic..."
    # python3 ../../generate_specs.py -I ${inserts} -U ${UPDATES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${entry_size} -L ${LAMBDA} # -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}"
    # echo "Specs generated for -I ${inserts} -U ${UPDATES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${entry_size} -L ${LAMBDA}"

    echo "Generating workload..."
    cd RocksDB || exit
    # ../../../bin/tectonic-cli generate -w ../workload.specs.json

    echo "${ROOT_DIR}/bin/load_gen -I ${inserts} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${entry_size} -L ${LAMBDA}" # -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}"
    ${ROOT_DIR}/bin/load_gen \
            -I ${inserts} \
            -U "${UPDATES}" \
            -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} \
            -E ${entry_size} \
            -L ${LAMBDA} #\
            # -O ${RANGE_QUERY_OVERLAPPING_COUNT} \
            # --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}

    echo "Copying workload to RangeReduce[lb=0]..."
    cd ../RangeReduce[lb=0]
    if [ -f "../RocksDB/workload.txt" ]; then
        cp ../RocksDB/workload.txt ./workload.txt
        echo "workload.txt copied successfully"
    else
        echo "Error: workload.txt not found in RocksDB"
        exit 1
    fi

    echo "Copying workload to RangeReduce[lb=T^-1]..."
    cd ../RangeReduce[lb=T^-1]
    if [ -f "../RocksDB/workload.txt" ]; then
        cp ../RocksDB/workload.txt ./workload.txt
        echo "workload.txt copied successfully"
    else
        echo "Error: workload.txt not found in RocksDB"
        exit 1
    fi

    echo "Copying workload to RangeReduce[lb=T^-1ANDre=1]..."
    cd ../RangeReduce[lb=T^-1ANDre=1]
    if [ -f "../RocksDB/workload.txt" ]; then
        cp ../RocksDB/workload.txt ./workload.txt
        echo "workload.txt copied successfully"
    else
        echo "Error: workload.txt not found in RocksDB"
        exit 1
    fi

    echo "Running RocksDB workload..."
    cd ../RocksDB
    ${ROOT_DIR}/bin/working_version \
            -I ${inserts} \
            -U "${UPDATES}" \
            -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} \
            -E ${entry_size} \
            -B ${entries_per_page} \
            -P ${PAGES_PER_FILE} \
            -T "${SIZE_RATIO}" \
            --rq 0 \
            --lb 0 \
            --re 0 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} \
            --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} \
            --snap ${SNAP} \
            --succinctkv 0
    mv db/LOG LOG
    rm -rf db
    rm workload.txt

    echo "Running RangeReduce[lb=0] workload [with lb=0 && re=0]..."
    cd ../RangeReduce[lb=0]
    ${ROOT_DIR}/bin/working_version \
            -I ${inserts} \
            -U "${UPDATES}" \
            -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} \
            -E ${entry_size} \
            -B ${entries_per_page} \
            -P ${PAGES_PER_FILE} \
            -T "${SIZE_RATIO}" \
            --rq 1 \
            --lb 0 \
            --re 0 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} \
            --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} \
            --snap ${SNAP} \
            --succinctkv 1
    mv db/LOG LOG
    rm -rf db
    rm workload.txt

    echo "Running RangeReduce[lb=T^-1] workload [with lb=T^-1 && re=0]..."
    cd ../RangeReduce[lb=T^-1]
    ${ROOT_DIR}/bin/working_version \
            -I ${inserts} \
            -U "${UPDATES}" \
            -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} \
            -E ${entry_size} \
            -B ${entries_per_page} \
            -P ${PAGES_PER_FILE} \
            -T "${SIZE_RATIO}" \
            --rq 1 \
            --lb ${LOWER_BOUND} \
            --re 0 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} \
            --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} \
            --snap ${SNAP} \
            --succinctkv 0
    mv db/LOG LOG
    rm -rf db
    rm workload.txt

    echo "Running RangeReduce[lb=T^-1ANDre=1] workload [with lb=T^-1 && re=1]..."
    cd ../RangeReduce[lb=T^-1ANDre=1]
    ${ROOT_DIR}/bin/working_version \
            -I ${inserts} \
            -U "${UPDATES}" \
            -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} \
            -E ${entry_size} \
            -B ${entries_per_page} \
            -P ${PAGES_PER_FILE} \
            -T "${SIZE_RATIO}" \
            --rq 1 \
            --lb ${LOWER_BOUND} \
            --re 1 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} \
            --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} \
            --snap ${SNAP} \
            --succinctkv 0
    mv db/LOG LOG
    rm -rf db 
    rm workload.txt

    cd ../../..
done

source .env

# ------------- Slack Notification -------------
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
HOSTNAME=$(hostname)

MESSAGE="SuccinctKV Experiments Completed on ${HOSTNAME} TAG=${TAG}:"
PAYLOAD="{
    \"text\": \"${MESSAGE}\"
}"

curl -X POST -H 'Content-type: application/json' --data "${PAYLOAD}" ${SLACK_WEBHOOK_URL}
# ------------- End Slack Notification -------------
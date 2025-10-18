#!/bin/bash
set -e

bash ./scripts/rebuild.sh

TAG=figure9-random-rq
ENTRY_SIZE=128
LAMBDA=0.125
ENTRIES_PER_PAGE=32
PAGES_PER_FILE=1024
SIZE_RATIO=(2 4) # 6 8 10)

INSERTS=8388608
UPDATES=8388608
RANGE_QUERIES=9000
SELECTIVITY=0.1
# RANGE_QUERY_OVERLAPPING_COUNT=100
# RANGE_QUERY_OVERLAPPING_PERCENT=1

SHOW_PROGRESS=1
VERSION=0
SANITY_CHECK=0
USE_DB=0
SNAP=0

echo "Starting experiments with TAG=${TAG}, ENTRY_SIZE=${ENTRY_SIZE}"

for size_ratio in "${SIZE_RATIO[@]}"
do
    echo "Debug: INSERTS=${INSERTS}, UPDATES=${UPDATES}, RANGE_QUERIES=${RANGE_QUERIES}"
    EXP_DIR="experiments-${TAG}-U${UPDATES}-E${ENTRY_SIZE}-B${ENTRIES_PER_PAGE}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${size_ratio}"
    echo "Debug: EXP_DIR=${EXP_DIR}"

    mkdir -p .vstats
    cd .vstats || exit
    mkdir -p "$EXP_DIR"
    cd "$EXP_DIR" || exit

    mkdir -p RocksDB RangeReduce[lb=0]

    # echo "Generating specs for Tectonic..."
    # python3 ../../generate_specs.py -I ${INSERTS} -U ${UPDATES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA} # -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}"
    # echo "Specs generated for -I ${INSERTS} -U ${UPDATES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}"

    echo "Generating workload..."
    cd RocksDB || exit
    # ../../../bin/tectonic-cli generate -w ../workload.specs.json

    echo "../../../bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}" # -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}"
    ../../../bin/load_gen \
            -I ${INSERTS} \
            -U "${UPDATES}" \
            -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} \
            -E ${ENTRY_SIZE} \
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

    echo "Running RangeReduce[lb=0] workload [with lb=0 && re=0]..."
    cd ../RangeReduce[lb=0]
    ../../../bin/working_version \
            -I ${INSERTS} \
            -U "${UPDATES}" \
            -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} \
            -E ${ENTRY_SIZE} \
            -B ${ENTRIES_PER_PAGE} \
            -P ${PAGES_PER_FILE} \
            -T "${size_ratio}" \
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
    cd ../../..
done

source .env

# ------------- Slack Notification -------------
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
HOSTNAME=$(hostname)

MESSAGE="SuccinctKV Experiments Completed on ${HOSTNAME}:
- ENTRY_SIZE=${ENTRY_SIZE}
- INSERTS=${INSERTS}
- RANGE_QUERY_PERCENT=${RANGE_QUERY_PERCENT[*]}
- SELECTIVITY=${SELECTIVITY}"
PAYLOAD="{
    \"text\": \"${MESSAGE}\"
}"

curl -X POST -H 'Content-type: application/json' --data "${PAYLOAD}" ${SLACK_WEBHOOK_URL}
# ------------- End Slack Notification -------------
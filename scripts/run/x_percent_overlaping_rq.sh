#!/bin/bash
set -e

bash ./scripts/rebuild.sh
ROOT_DIR=~/LSMQueryDrivenCompaction

TAG=x_percent_overlap
ENTRY_SIZE=128
LAMBDA=0.125
ENTRIES_PER_PAGE=32
PAGES_PER_FILE=1024
SIZE_RATIO=6

INSERTS=8388608
RANGE_QUERY_PERCENT=(0.00390625)
SELECTIVITY=0.1
RANGE_QUERY_OVERLAPPING_COUNT=1      # we update this later based on number of range queries
RANGE_QUERY_OVERLAPPING_PERCENT=1    # 100% overlapping

SHOW_PROGRESS=1
VERSION=0
SANITY_CHECK=0
USE_DB=0
SNAP=0

echo "=============================="
echo " Starting variable overlapping range query experiments"
echo " TAG=${TAG}"
echo " Scales: ${RANGE_QUERY_OVERLAPPING_PERCENT}"
echo "=============================="

for RQ_PERCENT in "${RANGE_QUERY_PERCENT[@]}"
do
    RANGE_QUERIES=$(echo "(${INSERTS} * ${RQ_PERCENT}) + 0.5" | bc | awk '{printf "%d\n", $0}')
    UPDATES=$(echo "${INSERTS} - ${RANGE_QUERIES}" | bc)
    RANGE_QUERY_OVERLAPPING_COUNT=${RANGE_QUERIES}

    LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO})" | bc)

    echo "Debug: INSERTS=${INSERTS}, UPDATES=${UPDATES}, RANGE_QUERIES=${RANGE_QUERIES}"
    EXP_DIR="experiments-${TAG}-U${UPDATES}-E${ENTRY_SIZE}-B${ENTRIES_PER_PAGE}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${SIZE_RATIO}"
    echo "Debug: EXP_DIR=${EXP_DIR}"

    mkdir -p .vstats
    cd .vstats
    mkdir -p "$EXP_DIR"
    cd "$EXP_DIR"

    mkdir -p RocksDB RangeReduce[lb=0] RangeReduce[lb=T^-1] RangeReduce[lb=T^-1ANDre=1]

    # echo "Generating specs for Tectonic..."
    # python3 ../../generate_specs.py -I ${INSERTS} -U ${UPDATES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA} # -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}"
    # echo "Specs generated for -I ${INSERTS} -U ${UPDATES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}"

    echo "Generating workload..."
    cd RocksDB
    # ${ROOT_DIR}/bin/tectonic-cli generate -w ../workload.specs.json

    echo "${ROOT_DIR}/bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA} -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}"
    ${ROOT_DIR}/bin/load_gen \
            -I ${INSERTS} \
            -U "${UPDATES}" \
            -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} \
            -E ${ENTRY_SIZE} \
            -L ${LAMBDA} \
            -O ${RANGE_QUERY_OVERLAPPING_COUNT} \
            --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}

    # --------------------------------------------------------
    # Copy workload to all experiment variants
    # --------------------------------------------------------
    for target in "../RangeReduce[lb=0]" "../RangeReduce[lb=T^-1]" "../RangeReduce[lb=T^-1ANDre=1]"; do
        if [ -f "workload.txt" ]; then
            cp workload.txt "${target}/workload.txt"
            echo "Copied workload.txt to ${target}"
        else
            echo "Error: workload.txt not found in RocksDB"
            exit 1
        fi
    done


    # --------------------------------------------------------
    # Run each workload configuration
    # --------------------------------------------------------
    echo "Running RocksDB workload..."
    cd ../RocksDB
    ${ROOT_DIR}/bin/working_version \
        -I ${INSERTS} \
        -U "${UPDATES}" \
        -S "${RANGE_QUERIES}" \
        -Y ${SELECTIVITY} \
        -E ${ENTRY_SIZE} \
        -B ${ENTRIES_PER_PAGE} \
        -P ${PAGES_PER_FILE} \
        -T "${SIZE_RATIO}" \
        --rq 0 --lb 0 --re 0 \
        --progress ${SHOW_PROGRESS} \
        -V ${VERSION} --sanity ${SANITY_CHECK} \
        --usedb ${USE_DB} --snap ${SNAP} \
        --succinctkv 0
    mv db/LOG LOG; rm -rf db workload.txt

    echo "Running RangeReduce[lb=0] workload..."
    cd ../RangeReduce[lb=0]
    ${ROOT_DIR}/bin/working_version \
        -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
        -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
        -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
        --rq 1 --lb 0 --re 0 \
        --progress ${SHOW_PROGRESS} \
        -V ${VERSION} --sanity ${SANITY_CHECK} \
        --usedb ${USE_DB} --snap ${SNAP} --succinctkv 1
    mv db/LOG LOG; rm -rf db workload.txt

    echo "Running RangeReduce[lb=T^-1] workload..."
    cd ../RangeReduce[lb=T^-1]
    ${ROOT_DIR}/bin/working_version \
        -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
        -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
        -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
        --rq 1 --lb ${LOWER_BOUND} --re 0 \
        --progress ${SHOW_PROGRESS} \
        -V ${VERSION} --sanity ${SANITY_CHECK} \
        --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
    mv db/LOG LOG; rm -rf db workload.txt

    echo "Running RangeReduce[lb=T^-1ANDre=1] workload..."
    cd ../RangeReduce[lb=T^-1ANDre=1]
    ${ROOT_DIR}/bin/working_version \
        -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
        -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
        -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
        --rq 1 --lb ${LOWER_BOUND} --re 1 \
        --progress ${SHOW_PROGRESS} \
        -V ${VERSION} --sanity ${SANITY_CHECK} \
        --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
    mv db/LOG LOG; rm -rf db workload.txt
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

set +e
curl -X POST -H 'Content-type: application/json' \
     --data "${PAYLOAD}" \
     "${SLACK_WEBHOOK_URL}"
set -e

# ------------- End Slack Notification -------------
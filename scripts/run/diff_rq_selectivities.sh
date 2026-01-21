#!/bin/bash

bash ./scripts/rebuild.sh

ROOT_DIR=~/LSMQueryDrivenCompaction

TAG=tail_latencies # this is the new one
ENTRY_SIZE=128
LAMBDA=0.125
ENTRIES_PER_PAGE=32
PAGES_PER_FILE=1024
SIZE_RATIO=6

INSERTS=8388608
RANGE_QUERY_PERCENT=(0.00390625)
SELECTIVITY=0.1

SHOW_PROGRESS=1
VERSION=0
SANITY_CHECK=0
USE_DB=0
SNAP=0
MAX_TRIVIAL_MOVE=1

echo "Starting experiments with TAG=${TAG}, ENTRY_SIZE=${ENTRY_SIZE}"

LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO})" | bc)

START_DIR=$(pwd)
WORKLOAD_ROOT="${START_DIR}/workloads"
mkdir -p "${WORKLOAD_ROOT}"

for RQ_PERCENT in "${RANGE_QUERY_PERCENT[@]}"; do
    RANGE_QUERIES=$(echo "(${INSERTS} * ${RQ_PERCENT}) + 0.5" | bc | awk '{printf "%d\n", $0}')
    UPDATES=$(echo "${INSERTS} - ${RANGE_QUERIES}" | bc)

    echo "Debug: INSERTS=${INSERTS}, UPDATES=${UPDATES}, RANGE_QUERIES=${RANGE_QUERIES}"

    EXP_DIR="experiments-${TAG}-U${UPDATES}-E${ENTRY_SIZE}-B${ENTRIES_PER_PAGE}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${SIZE_RATIO}"
    echo "Debug: EXP_DIR=${EXP_DIR}"

    WORKLOAD_DIR="${WORKLOAD_ROOT}/S${RANGE_QUERIES}-Y${SELECTIVITY}"
    mkdir -p "${WORKLOAD_DIR}"

    # --------------------------------------------------------
    # Generate workload ONCE per RQ_PERCENT
    # --------------------------------------------------------
    if [ ! -f "${WORKLOAD_DIR}/workload.txt" ]; then
        echo "Generating workload once for S=${RANGE_QUERIES}..."
        cd "${WORKLOAD_DIR}" || exit
        ${ROOT_DIR}/bin/load_gen \
            -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} \
            -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}
        cd "${START_DIR}"
    else
        echo "Reusing existing workload for S=${RANGE_QUERIES}"
    fi

    for run in 1 2 3; do
        cd .vstats || exit
        mkdir -p "${EXP_DIR}"
        cd "${EXP_DIR}" || exit

        mkdir -p \
            RangeReduce[lb=T^-1ANDre=1]-${run} \
            RangeReduce[lb=T^-1]-${run} \
            SuccinctKV-${run} \
            RocksDB-${run}

        # --------------------------------------------------------
        # Distribute workload (symlink)
        # --------------------------------------------------------
        for target in \
            "RocksDB-${run}" \
            "SuccinctKV-${run}" \
            "RangeReduce[lb=T^-1]-${run}" \
            "RangeReduce[lb=T^-1ANDre=1]-${run}"; do
            ln -sf "${WORKLOAD_DIR}/workload.txt" "${target}/workload.txt"
        done

        # --------------------------------------------------------
        # Run experiments
        # --------------------------------------------------------
        echo "Running RangeReduce[lb=T^-1ANDre=1]-${run}..."
        cd RangeReduce[lb=T^-1ANDre=1]-${run}
        ${ROOT_DIR}/bin/working_version \
            -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
            -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
            --rq 1 --lb ${LOWER_BOUND} --re 1 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
        mv db/LOG LOG; rm -rf db
        cd ..

        echo "Running RangeReduce[lb=T^-1]-${run}..."
        cd RangeReduce[lb=T^-1]-${run}
        ${ROOT_DIR}/bin/working_version \
            -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
            -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
            --rq 1 --lb ${LOWER_BOUND} --re 0 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
        mv db/LOG LOG; rm -rf db
        cd ..

        echo "Running SuccinctKV-${run}..."
        cd SuccinctKV-${run}
        ${ROOT_DIR}/bin/working_version \
            -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
            -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
            --rq 1 --lb 0 --re 0 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} --snap ${SNAP} --succinctkv 1
        mv db/LOG LOG; rm -rf db
        cd ..

        echo "Running RocksDB-${run}..."
        cd RocksDB-${run}
        ${ROOT_DIR}/bin/working_version \
            -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
            -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
            --rq 0 --lb 0 --re 0 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
        mv db/LOG LOG; rm -rf db

        cd "${START_DIR}"
    done
done

source .env

# ------------- Slack Notification -------------
HOSTNAME=$(hostname)
MESSAGE="SuccinctKV Experiments Completed on ${HOSTNAME}: TAG=${TAG}"
PAYLOAD="{ \"text\": \"${MESSAGE}\" }"

curl -X POST -H 'Content-type: application/json' --data "${PAYLOAD}" ${SLACK_WEBHOOK_URL}
# ------------- End Slack Notification -------------

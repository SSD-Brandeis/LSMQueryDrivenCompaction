#!/bin/bash
set -e

bash ./scripts/rebuild.sh
ROOT_DIR=~/LSMQueryDrivenCompaction

TAG=skv-limitations-new
ENTRY_SIZE=128
LAMBDA=0.125
ENTRIES_PER_PAGE=32
PAGES_PER_FILE=1024
SIZE_RATIO=6

# P1: inserts + updates (after 50\% -- think this)\\ 40% 40%
# P2: only RQs\\.                                    100
# P3: inserts more updates\\                         40% 40%
# P4: only RQs\\                                     100
# P5: insert only\\                                  20%

INSERTS=8388608
UPDATES=8388608
RANGE_QUERIES=400
SELECTIVITY=(0.1)

POINT_DELETES=0

SHOW_PROGRESS=1
VERSION=0
SANITY_CHECK=0
USE_DB=0
SNAP=0

echo "Starting experiments with TAG=${TAG}, ENTRY_SIZE=${ENTRY_SIZE}"

for sel in "${SELECTIVITY[@]}"
do
    echo "Debug: INSERTS=${INSERTS}, UPDATES=${UPDATES}, RANGE_QUERIES=${RANGE_QUERIES}"
    EXP_DIR="experiments-${TAG}-U${UPDATES}-E${ENTRY_SIZE}-B${ENTRIES_PER_PAGE}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${SIZE_RATIO}"
    echo "Debug: EXP_DIR=${EXP_DIR}"

    mkdir -p .vstats
    cd .vstats || exit
    mkdir -p "$EXP_DIR"
    cd "$EXP_DIR" || exit

    mkdir -p RangeReduce[lb=T^-1ANDre=1] SuccinctKV RocksDB #  RangeReduce[lb=0] RangeReduce[lb=0ANDsmlck=0] RangeReduce[lb=T^-1]

    # --------------------------------------------------------
    # Workload Generation
    # --------------------------------------------------------

    # echo "Generating specs for Tectonic..."
    # python3 ../../scripts/generate_specs.py -I ${INSERTS} -U ${UPDATES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${sel} -E ${ENTRY_SIZE} -L ${LAMBDA} # -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}"
    # echo "Specs generated for -I ${INSERTS} -U ${UPDATES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${sel} -E ${ENTRY_SIZE} -L ${LAMBDA}"

    echo "Generating workload..."
    cd RocksDB || exit
    ${ROOT_DIR}/bin/tectonic-cli generate -w ../workload.specs.json

    # echo "${ROOT_DIR}/bin/load_gen -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${sel} -E ${ENTRY_SIZE} -L ${LAMBDA}" # -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}"
    # ${ROOT_DIR}/bin/load_gen \
    #         -I ${INSERTS} \
    #         -U "${UPDATES}" \
    #         -S "${RANGE_QUERIES}" \
    #         -Y ${sel} \
    #         -E ${ENTRY_SIZE} \
    #         -L ${LAMBDA}

    # --------------------------------------------------------
    # Copy workload to all experiment variants
    # --------------------------------------------------------
    for target in "../RangeReduce[lb=T^-1ANDre=1]" "../SuccinctKV"; do #  "../RangeReduce[lb=T^-1]" "../RangeReduce[lb=0ANDsmlck=0]" "../RangeReduce[lb=0]" ; do
        if [ -f "workload.txt" ]; then
            cp workload.txt "${target}/workload.txt"
            echo "Copied workload.txt to ${target}"
        else
            echo "Error: workload.txt not found in RocksDB"
            exit 1
        fi
    done

    LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO})" | bc)

    # --------------------------------------------------------
    # Run each workload configuration
    # --------------------------------------------------------

    echo "Running RangeReduce[lb=T^-1ANDre=1] workload..."
    cd ../RangeReduce[lb=T^-1ANDre=1]
    ${ROOT_DIR}/bin/working_version \
        -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
        -Y ${sel} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
        -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
        --rq 1 --lb ${LOWER_BOUND} --re 1 \
        --progress ${SHOW_PROGRESS} \
        -V ${VERSION} --sanity ${SANITY_CHECK} \
        --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
    mv db/LOG LOG; rm -rf db  # workload.txt

    # echo "Running RangeReduce[lb=T^-1] workload..."
    # cd ../RangeReduce[lb=T^-1]
    # ${ROOT_DIR}/bin/working_version \
    #     -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
    #     -Y ${sel} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
    #     -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
    #     --rq 1 --lb ${LOWER_BOUND} --re 0 \
    #     --progress ${SHOW_PROGRESS} \
    #     -V ${VERSION} --sanity ${SANITY_CHECK} \
    #     --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
    # mv db/LOG LOG; rm -rf db  # workload.txt

    echo "Running SuccinctKV workload..."
    cd ../SuccinctKV
    ${ROOT_DIR}/bin/working_version \
        -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
        -Y ${sel} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
        -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
        --rq 1 --lb 0 --re 0 \
        --progress ${SHOW_PROGRESS} \
        -V ${VERSION} --sanity ${SANITY_CHECK} \
        --usedb ${USE_DB} --snap ${SNAP} --succinctkv 1
    mv db/LOG LOG; rm -rf db # workload.txt

    # echo "Running RangeReduce[lb=0] workload..."
    # cd ../RangeReduce[lb=0]
    # ${ROOT_DIR}/bin/working_version \
    #     -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
    #     -Y ${sel} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
    #     -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
    #     --rq 1 --lb 0 --re 0 \
    #     --progress ${SHOW_PROGRESS} \
    #     -V ${VERSION} --sanity ${SANITY_CHECK} \
    #     --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
    # mv db/LOG LOG; rm -rf db  # workload.txt

    # echo "Running RangeReduce[lb=0ANDsmlck=0] workload..."
    # cd ../RangeReduce[lb=0ANDsmlck=0]
    # ${ROOT_DIR}/bin/working_version \
    #     -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
    #     -Y ${sel} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
    #     -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
    #     --rq 1 --lb 0 --re 0 --epl 0 \
    #     --progress ${SHOW_PROGRESS} \
    #     -V ${VERSION} --sanity ${SANITY_CHECK} \
    #     --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
    # mv db/LOG LOG; rm -rf db  # workload.txt

    echo "Running RocksDB workload..."
    cd ../RocksDB
    ${ROOT_DIR}/bin/working_version \
        -I ${INSERTS} \
        -U "${UPDATES}" \
        -S "${RANGE_QUERIES}" \
        -Y ${sel} \
        -E ${ENTRY_SIZE} \
        -B ${ENTRIES_PER_PAGE} \
        -P ${PAGES_PER_FILE} \
        -T "${SIZE_RATIO}" \
        --rq 0 --lb 0 --re 0 \
        --progress ${SHOW_PROGRESS} \
        -V ${VERSION} --sanity ${SANITY_CHECK} \
        --usedb ${USE_DB} --snap ${SNAP} \
        --succinctkv 0
    mv db/LOG LOG; rm -rf db  # workload.txt

    cd ../../..

done

source .env

# ------------- Slack Notification -------------
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
HOSTNAME=$(hostname)

MESSAGE="SuccinctKV Experiments Completed on ${HOSTNAME}: TAG=${TAG}"
PAYLOAD="{
    \"text\": \"${MESSAGE}\"
}"

curl -X POST -H 'Content-type: application/json' --data "${PAYLOAD}" ${SLACK_WEBHOOK_URL}
# ------------- End Slack Notification -------------
#!/bin/bash
set -e

bash ./scripts/rebuild.sh
ROOT_DIR=~/LSMQueryDrivenCompaction

TAG=scalability
ENTRY_SIZES=(128)
LAMBDA=0.25
ENTRIES_PER_PAGE=(32)
PAGES_PER_FILE=1024
SIZE_RATIO=6

BASE_INSERTS=8388608  # baseline (~1 GB)
RANGE_QUERIES=9000
SELECTIVITY=0.1

SHOW_PROGRESS=1
VERSION=0
SANITY_CHECK=0
USE_DB=0
SNAP=0

# Scaling factors for total data size
SCALE_FACTORS=(1 10 20 30 40 50)

echo "=============================="
echo " Starting scalability experiments"
echo " TAG=${TAG}"
echo " Scales: ${SCALE_FACTORS[@]}"
echo "=============================="



for SCALE in "${SCALE_FACTORS[@]}"; do
    for i in "${!ENTRY_SIZES[@]}"; do
        entry_size=${ENTRY_SIZES[$i]}
        entries_per_page=${ENTRIES_PER_PAGE[$i]}
        inserts=$(( BASE_INSERTS * SCALE ))
        UPDATES=$(( inserts ))                            # proportional updates
        RANGE_QUERIES=$(( 9000 * SCALE ))                 # proportional queries

        LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO})" | bc)

        EXP_DIR="experiments-${TAG}-${SCALE}x-U${UPDATES}-E${entry_size}-B${entries_per_page}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${SIZE_RATIO}"

        echo "------------------------------------------------------------"
        echo " SCALE=${SCALE}x | INSERTS=${inserts}, UPDATES=${UPDATES}, ENTRY_SIZE=${entry_size}"
        echo " EXP_DIR=${EXP_DIR}"
        echo "------------------------------------------------------------"

        mkdir -p .vstats
        cd .vstats || exit
        mkdir -p "$EXP_DIR"
        cd "$EXP_DIR" || exit

        mkdir -p RocksDB RangeReduce[lb=0] RangeReduce[lb=T^-1] RangeReduce[lb=T^-1ANDre=1]

        # --------------------------------------------------------
        # Workload Generation
        # --------------------------------------------------------
        echo "Generating workload..."
        cd RocksDB || exit

        echo "${ROOT_DIR}/bin/load_gen -I ${inserts} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${entry_size} -L ${LAMBDA}"
        ${ROOT_DIR}/bin/load_gen \
            -I ${inserts} \
            -U "${UPDATES}" \
            -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} \
            -E ${entry_size} \
            -L ${LAMBDA}

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
            -I ${inserts} \
            -U "${UPDATES}" \
            -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} \
            -E ${entry_size} \
            -B ${entries_per_page} \
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
            -I ${inserts} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} -E ${entry_size} -B ${entries_per_page} \
            -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
            --rq 1 --lb 0 --re 0 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} --snap ${SNAP} --succinctkv 1
        mv db/LOG LOG; rm -rf db workload.txt

        echo "Running RangeReduce[lb=T^-1] workload..."
        cd ../RangeReduce[lb=T^-1]
        ${ROOT_DIR}/bin/working_version \
            -I ${inserts} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} -E ${entry_size} -B ${entries_per_page} \
            -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
            --rq 1 --lb ${LOWER_BOUND} --re 0 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
        mv db/LOG LOG; rm -rf db workload.txt

        echo "Running RangeReduce[lb=T^-1ANDre=1] workload..."
        cd ../RangeReduce[lb=T^-1ANDre=1]
        ${ROOT_DIR}/bin/working_version \
            -I ${inserts} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
            -Y ${SELECTIVITY} -E ${entry_size} -B ${entries_per_page} \
            -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
            --rq 1 --lb ${LOWER_BOUND} --re 1 \
            --progress ${SHOW_PROGRESS} \
            -V ${VERSION} --sanity ${SANITY_CHECK} \
            --usedb ${USE_DB} --snap ${SNAP} --succinctkv 0
        mv db/LOG LOG; rm -rf db workload.txt

        cd ../../..
    done
done

# ------------------------------------------------------------
# Slack Notification
# ------------------------------------------------------------
source .env

SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
HOSTNAME=$(hostname)
MESSAGE="SuccinctKV Scalability Experiments Completed on ${HOSTNAME} (TAG=${TAG})"
PAYLOAD="{\"text\": \"${MESSAGE}\"}"

curl -X POST -H 'Content-type: application/json' --data "${PAYLOAD}" ${SLACK_WEBHOOK_URL}

echo "All scalability experiments complete."

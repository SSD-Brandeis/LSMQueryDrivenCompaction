#!/bin/bash
set -e

# bash ./scripts/rebuild.sh
ROOT_DIR=~/LSMQueryDrivenCompaction

TAG=ycsbe
ENTRY_SIZE=1024
LAMBDA=0.125
ENTRIES_PER_PAGE=4
PAGES_PER_FILE=4
SIZE_RATIO=6

INSERTS=1000000 # 250000
UPDATES=50000 # 250000 I + 500000 U

RANGE_QUERIES=950000 # 95000 S + 5000 U
SELECTIVITY=0.0001

SHOW_PROGRESS=1
VERSION=0
SANITY_CHECK=0
USE_DB=0
SNAP=0

echo "Starting experiments with TAG=${TAG}, ENTRY_SIZE=${ENTRY_SIZE}"

echo "Debug: INSERTS=${INSERTS}, UPDATES=${UPDATES}, RANGE_QUERIES=${RANGE_QUERIES}"
EXP_DIR="experiments-${TAG}-U${UPDATES}-E${ENTRY_SIZE}-B${ENTRIES_PER_PAGE}-S${RANGE_QUERIES}-Y${SELECTIVITY}-T${SIZE_RATIO}"
echo "Debug: EXP_DIR=${EXP_DIR}"

mkdir -p .vstats
cd .vstats || exit
mkdir -p "$EXP_DIR"
cd "$EXP_DIR" || exit

mkdir -p RocksDB RangeReduce[lb=0] RangeReduce[lb=T^-1] RangeReduce[lb=T^-1ANDre=1]

# --------------------------------------------------------
# Workload Generation
# --------------------------------------------------------

# echo "Generating specs for Tectonic..."
# python3 ../../../scripts/generate_specs.py -I ${INSERTS} -U ${UPDATES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA} # -O ${RANGE_QUERY_OVERLAPPING_COUNT} --PO ${RANGE_QUERY_OVERLAPPING_PERCENT}"
# echo "Specs generated for -I ${INSERTS} -U ${UPDATES} -D ${POINT_DELETES} -S ${RANGE_QUERIES} -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -L ${LAMBDA}"

# echo "Generating workload..."
cd RocksDB || exit
# ../../../bin/tectonic-cli generate -w workload.specs.json

# --------------------------------------------------------
# Copy workload to all experiment variants
# --------------------------------------------------------
# for target in "../RangeReduce[lb=0]" "../RangeReduce[lb=T^-1]" "../RangeReduce[lb=T^-1ANDre=1]"; do
#     if [ -f "workload.txt" ]; then
#         cp workload.txt "${target}/workload.txt"
#         echo "Copied workload.txt to ${target}"
#     else
#         echo "Error: workload.txt not found in RocksDB"
#         exit 1
#     fi
# done

LOWER_BOUND=$(echo "scale=9; 1/(${SIZE_RATIO})" | bc)

# --------------------------------------------------------
# Run each workload configuration
# --------------------------------------------------------
echo "Running RocksDB workload..."
cd ../RocksDB
# ${ROOT_DIR}/bin/working_version \
#     -I ${INSERTS} \
#     -U "${UPDATES}" \
#     -S "${RANGE_QUERIES}" \
#     -Y ${SELECTIVITY} \
#     -E ${ENTRY_SIZE} \
#     -B ${ENTRIES_PER_PAGE} \
#     -P ${PAGES_PER_FILE} \
#     -T "${SIZE_RATIO}" \
#     --rq 0 --lb 0 --re 0 \
#     --progress ${SHOW_PROGRESS} \
#     -V ${VERSION} --sanity ${SANITY_CHECK} \
#     --usedb ${USE_DB} --snap ${SNAP} \
#     --succinctkv 0
# mv db/LOG LOG; rm -rf db workload.txt

# echo "Running RangeReduce[lb=0] workload..."
# cd ../RangeReduce[lb=0]
# ${ROOT_DIR}/bin/working_version \
#     -I ${INSERTS} -U "${UPDATES}" -S "${RANGE_QUERIES}" \
#     -Y ${SELECTIVITY} -E ${ENTRY_SIZE} -B ${ENTRIES_PER_PAGE} \
#     -P ${PAGES_PER_FILE} -T "${SIZE_RATIO}" \
#     --rq 1 --lb 0 --re 0 \
#     --progress ${SHOW_PROGRESS} \
#     -V ${VERSION} --sanity ${SANITY_CHECK} \
#     --usedb ${USE_DB} --snap ${SNAP} --succinctkv 1
# mv db/LOG LOG; rm -rf db workload.txt

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
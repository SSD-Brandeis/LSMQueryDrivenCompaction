#!/bin/bash
# Script for measuring CPU, memory and IO device utilization
# Author: Manos Athanassoulis

CPU_IOSTATOUT=$(mktemp __iostat_out.XXXXXXXXXX)
DISK_IOSTATOUT=$(mktemp __iostat_disk_out.XXXXXXXXXX)
TOPOUT=$(mktemp __top_out.XXXXXXXXXX)

DEVICE=/dev/sda
CPU_INTERVAL=1
CPU_TOP_INTERVAL=00.05
DISK_INTERVAL=1
# ----------------------------------------------------------------------
iostat -t -c ${CPU_INTERVAL} >> ${CPU_IOSTATOUT}&
CPU_IOSTATPID=$!
iostat -t -d ${DISK_INTERVAL} -x -k ${DEVICE}>> ${DISK_IOSTATOUT}&
DISK_IOSTATPID=$!
# $@ &
./working_version --rq "$1" --lb "$3" --ub "$4" > "${2}_workload.log" &
APP_PID=$!
#echo ${APP_PID}
#ps -ef | grep ${APP_PID}
top -b -p ${APP_PID} -d ${CPU_TOP_INTERVAL} >> ${TOPOUT}&
TOP_PID=$!
wait ${APP_PID}
kill ${CPU_IOSTATPID}
kill ${DISK_IOSTATPID}
kill ${TOP_PID}
#iostat -t -d -m ${DEVICE} >> ${DISK_IOSTATOUT}
sleep 1
echo Printing results
echo
echo "CPU from iostat (every $DISK_INTERVAL s)"
cat "${CPU_IOSTATOUT}" | head -n 4 | tail -n 1 >> "${2}_cpu_iostat.txt"
cat "${CPU_IOSTATOUT}" | grep "avg-cpu" -A 1 | grep -v "avg-cpu" | awk '{if ($1!="--") print $0}' >> "${2}_cpu_iostat.txt"
rm "${CPU_IOSTATOUT}"
echo
echo "CPU from top (every $CPU_TOP_INTERVAL s)"
cat "${TOPOUT}" | head -n 7 | tail -n 1 >> "${2}_cpu_top.txt"
cat "${TOPOUT}" | grep ${APP_PID} >> "${2}_cpu_top.txt"
rm "${TOPOUT}"
echo
echo "IO from iostat (every $DISK_INTERVAL s)"
cat "${DISK_IOSTATOUT}" | head -n 4 | tail -n 1 >> "${2}_io_iostat.txt"
cat "${DISK_IOSTATOUT}" | grep "Device" -A 1 | grep -v "Device" | awk '{if ($1!="--") print $0}' >> "${2}_io_iostat.txt"
rm "${DISK_IOSTATOUT}"
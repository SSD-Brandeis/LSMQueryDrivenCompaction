import os
import time
import shutil
import json
from pathlib import Path

CURR_DIR = Path(__file__).parent
# WORKLOAD_DIR = CURR_DIR.joinpath("workloads")
EXPERIMENT_DIR = CURR_DIR.joinpath("experiments")
OUTPUT_FILE = CURR_DIR.joinpath("stats.txt")
LOG_FILE = CURR_DIR.joinpath("logs.txt")

# if not WORKLOAD_DIR.exists():
#     WORKLOAD_DIR.mkdir()

if not EXPERIMENT_DIR.exists():
    EXPERIMENT_DIR.mkdir()


def create_workload(args, dir_name, log):
    os.chdir(EXPERIMENT_DIR)
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)

    os.chdir(dir_name)
    process_output = os.popen(f"../../../../../emulator/emu_runner {args}").read()
    log.write(f"{process_output}\n")
    os.chdir(CURR_DIR)


def run_workload(dir_name, log):
    os.chdir(EXPERIMENT_DIR)
    os.chdir(dir_name)

    print("\nrunning workload\n")

    db_dir = os.path.join(os.getcwd(), "db_working_home")
    if os.path.exists(db_dir):
        log.write("removing db_working_home\n")
        shutil.rmtree(db_dir)

    args = f"> '{dir_name} -V 1 --rq off.log' -V 1 --rq 0"
    print("running for rq off", dir_name)
    process_output = os.popen(f"../../working_version {args}").read()
    log.write(f"{process_output}\n")

    time.sleep(5)
    if os.path.exists(db_dir):
        log.write("removing db_working_home\n")
        shutil.rmtree(db_dir)

    args = f"> '{dir_name} -V 1 --rq on.log' -V 1 --rq 1"
    print("running for rq on", dir_name)
    process_output = os.popen(f"../../working_version {args}").read()
    log.write(f"{process_output}\n")

    if os.path.exists(db_dir):
        log.write("removing db_working_home\n")
        shutil.rmtree(db_dir)

    os.chdir(CURR_DIR)


if __name__ == "__main__":
    # read experments to run file `experiments.txt`
    experiements_to_run = list()
    workloads = json.load(open("experiments.json"))

    for workload in workloads["workloads"]:
        log = open(LOG_FILE, "w")
        args = ""
        dir_name = ""

        if "inserts" in workload:
            args += f" -I {workload['inserts']}"
            dir_name += (
                f"I {workload['inserts']}"
                if dir_name == ""
                else f" I {workload['inserts']}"
            )
        if "updates" in workload:
            args += f" -U {workload['updates']}"
            dir_name += (
                f"U {workload['updates']}"
                if dir_name == ""
                else f" U {workload['updates']}"
            )
        if "range_queries" in workload and "selectivity" in workload:
            args += f" -S {workload['range_queries']}"
            args += f" -Y {workload['selectivity']}"
            dir_name += (
                f"S {workload['range_queries']}"
                if dir_name == ""
                else f" S {workload['range_queries']}"
            )
            dir_name += f" Y {workload['selectivity']}"
        # can add more stuff as well

        log.write(f"Creating workload for .. {args}\n")
        create_workload(args, dir_name, log)
        log.write(f"Running workload for .. {args}\n")
        run_workload(dir_name, log)
        print(f"ran successfully for {args}")

        log.close()


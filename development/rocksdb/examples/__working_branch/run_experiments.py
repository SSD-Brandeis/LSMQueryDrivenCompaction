import os
import shutil
import subprocess
from pathlib import Path

CURR_DIR = Path(__file__).parent
project_dir = Path(__file__).parent.absolute().__str__()
# WORKLOAD_DIR = CURR_DIR.joinpath("workloads")
EXPERIMENT_DIR = (
    Path(__file__).parent.joinpath("experiments-epoch").absolute().__str__()
)
OUTPUT_FILE = Path(__file__).parent.joinpath("stats.txt").absolute().__str__()
LOG_FILE = Path(__file__).parent.joinpath("logs.txt").absolute().__str__()

if not Path(EXPERIMENT_DIR).exists():
    Path(EXPERIMENT_DIR).mkdir()

def create_workload(args, dir_name, log):
    os.chdir(EXPERIMENT_DIR)
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)

    workload_file = os.path.join("workload.txt")

    if os.path.exists(workload_file):
        shutil.copy(workload_file, os.path.join(EXPERIMENT_DIR, dir_name))
    else:
        process_output = os.popen(
            f"../../../../emulator/emu_runner {args}"
        ).read()
        log.write(f"{process_output}\n")
        shutil.copy(workload_file, os.path.join(EXPERIMENT_DIR, dir_name))
    os.chdir(project_dir)


def run_workload(params, dir_name, log):
    os.chdir(EXPERIMENT_DIR)
    os.chdir(dir_name)

    log.write(" -------------- STARTING -------------- \n")

    db_dir = os.path.join(os.getcwd(), "db_working_home")
    log.write(f"\nrunning workload: {params} \n")
    if os.path.exists(db_dir):
        log.write("removing db_working_home\n")
        shutil.rmtree(db_dir)

    args = f" {params}"
    log.write(f"../../track_io.sh {args}")
    process_output = os.popen(
        f"../../track_io.sh {args}"
    ).read()
    log.write(f"{process_output}\n")

    if os.path.exists(db_dir):
        log.write("removing db_working_home\n")
        shutil.rmtree(db_dir)

    log.write(" -------------- DONE -------------- \n\n\n\n")
    os.chdir(CURR_DIR)

if __name__ == "__main__":
    # size_ratio = [2, 4, 6]
    size_ratio = [6]
    inserts = 31250                           # 1M
    updates = 7812                            # 250K
    range_queries = 100
    selectivity = 0.1                           # 10 percent (Y)
    entry_size = 1024 # 32                             # 32 bytes (E)
    number_of_entries_per_page = 4 # 128            # 128 entries per page (B)
    number_of_pages = 128                       # 128 pages per file (P)

    buffer_size = entry_size * number_of_entries_per_page * number_of_pages
    log = open(LOG_FILE, "a")
    
    print("Buffer size: ", buffer_size)

    os.chdir(EXPERIMENT_DIR)

    print("Current Dir: ", os.getcwd())

    for size in size_ratio:
        directory_name = f"I {inserts} U {updates} S {range_queries} Y {selectivity} T {size}"
        arguments = f"-I {inserts} -U {updates} -S {range_queries} -Y {selectivity} -E {entry_size} -B {number_of_entries_per_page} -P {number_of_pages} -T {size}"

        create_workload(arguments, directory_name + f" rq 0", log)

        # vaniall run
        run_workload(arguments + " --rq 0", directory_name + f" rq 0", log)

        create_workload(arguments, directory_name + f" rq 1", log)

        # rqdc run
        run_workload(arguments + f" --rq 1 --lb {0.12} --ub {1}", directory_name + " rq 1", log)

    log.close()

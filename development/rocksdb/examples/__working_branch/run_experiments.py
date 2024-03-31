import os
import shutil
from pathlib import Path

CURR_DIR = Path(__file__).parent
project_dir = Path(__file__).parent.absolute().__str__()
# WORKLOAD_DIR = CURR_DIR.joinpath("workloads")
EXPERIMENT_DIR = (
    Path(__file__).parent.joinpath("experiments").absolute().__str__()
)
OUTPUT_FILE = Path(__file__).parent.joinpath("stats.txt").absolute().__str__()
LOG_FILE = Path(__file__).parent.joinpath("logs.txt").absolute().__str__()

def create_workload(args, dir_name, log):
    os.chdir(EXPERIMENT_DIR)
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)

    workload_file = os.path.join("workload.txt")

    if os.path.exists(workload_file):
        print("Found already generated workload, Replacing ...")
        shutil.copy(workload_file, os.path.join(EXPERIMENT_DIR, dir_name))
    else:
        process_output = os.popen(f"../../../../emulator/load_gen {args}").read()
        print(f"{process_output}\n")
        shutil.copy(workload_file, os.path.join(EXPERIMENT_DIR, dir_name))
    os.chdir(project_dir)


def run_workload(params, dir_name, log):
    os.chdir(EXPERIMENT_DIR)
    os.chdir(dir_name)

    log.write(" -------------- STARTING -------------- \n")

    db_dir = os.path.join(os.getcwd(), "db_working_home")
    workload_txt = os.path.join(os.getcwd(), "workload.txt")

    log.write(f"\nrunning workload: {params} \n")
    if os.path.exists(db_dir):
        log.write("removing db_working_home\n")
        shutil.rmtree(db_dir)

    args = f" {params}"
    log.write(f"../../working_version {args} > workload.log")
    print(f"Running ../../working_version {args}")
    process_output = os.popen(f"../../working_version {args} > workload.log").read()
    log.write(f"{process_output}\n")

    if os.path.exists(db_dir):
        log.write("removing db_working_home\n")
        shutil.rmtree(db_dir)
    
    if os.path.exists(workload_txt):
        log.write("removing workload.txt\n")
        os.remove(workload_txt)

    log.write(" -------------- DONE -------------- \n\n\n\n")
    os.chdir(CURR_DIR)


if __name__ == "__main__":
    # size_ratio = [2, 4, 6]
    size_ratio = [8]
    inserts = 5000000
    updates = 1250000
    range_queries = 500
    selectivity = 0.2
    entry_size = 64  # (E)
    number_of_entries_per_page = 64  # (B)
    number_of_pages = 128  # (P)

    lower_bounds = [0.01] # [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1, 2, 3]
    upper_bounds = [6]    # [0.05, 0.1, 0.25, 0.5, 0.75, 1, 2, 4, 6]

    buffer_size = entry_size * number_of_entries_per_page * number_of_pages
    log = open(LOG_FILE, "a")

    print("Buffer size: ", buffer_size)

    EXPERIMENT_DIR = Path(__file__).parent.joinpath(f"experiments-consecutive-range-E{entry_size}-B{number_of_entries_per_page}-Y{selectivity}").absolute().__str__()

    if not Path(EXPERIMENT_DIR).exists():
        Path(EXPERIMENT_DIR).mkdir()

    os.chdir(EXPERIMENT_DIR)

    print("Current Dir: ", os.getcwd())

    for size in size_ratio:

        lower_upper_bounds = list()

        for lb in lower_bounds:
            for ub in upper_bounds:
                if lb == 0.01 and ub < 4:
                    continue
                if lb < ub:
                    lower_upper_bounds.append((lb, ub))

        directory_name = (
            f"I {inserts} U {updates} S {range_queries} Y {selectivity} T {size}"
        )
        arguments = f"-I {inserts} -U {updates} -S {range_queries} -Y {selectivity} -E {entry_size}"

        create_workload(
            arguments + " --SRQC 5 --SRQOS 0.95",
            directory_name + f" rq 0 E {entry_size} B {number_of_entries_per_page}",
            log,
        )

        # vaniall run
        run_workload(
            arguments + f" -B {number_of_entries_per_page} -P {number_of_pages} -T {size} --rq 0",
            directory_name + f" rq 0 E {entry_size} B {number_of_entries_per_page}",
            log,
        )

        for lower_bound, upper_bound in lower_upper_bounds:
            create_workload(
                arguments + " --SRQC 5 --SRQOS 0.95",
                directory_name
                + f" rq 1 E {entry_size} B {number_of_entries_per_page} lb {lower_bound} ub {upper_bound}",
                log,
            )

            # rqdc run
            run_workload(
                arguments + f" -B {number_of_entries_per_page} -P {number_of_pages} -T {size} --rq 1 --lb {lower_bound} --ub {upper_bound}",
                directory_name
                + f" rq 1 E {entry_size} B {number_of_entries_per_page} lb {lower_bound} ub {upper_bound}",
                log,
            )

    log.close()

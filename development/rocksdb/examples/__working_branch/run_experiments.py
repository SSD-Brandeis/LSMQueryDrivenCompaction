import os
import shutil
from pathlib import Path
from typing import Tuple

CURR_DIR = Path(__file__).parent
project_dir = Path(__file__).parent.absolute().__str__()
# WORKLOAD_DIR = CURR_DIR.joinpath("workloads")
EXPERIMENT_DIR = (
    Path(__file__).parent.joinpath("experiments").absolute().__str__()
)
OUTPUT_FILE = Path(__file__).parent.joinpath("stats.txt").absolute().__str__()
LOG_FILE = Path(__file__).parent.joinpath("logs.txt").absolute().__str__()


# lower_bound = [0, 0.05, 0.1, 0.25, 0.5, 0.75, 1, 2, 3]
# upper_bound = [0, 0.25, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 3.5, 4]
# selectivities = [0.01, 0.02, 0.1]

# one_exp = {
#     "inserts": 1000000,
#     "updates": 250000,
#     "range_queries": 100,
#     "size_ratio": 4,
# }

# workloads = []

# for selectivity in selectivities:
#     for ub in lower_bound:
#         for lb in upper_bound:
#             workload = one_exp.copy()

#             if ub == 0 and lb == 0:
#                 workload["range_query_enabled"] = 0
#             elif ub >= lb:
#                 continue
#             else:
#                 workload["range_query_enabled"] = 1
                
#             workload["selectivity"] = selectivity
#             workload["lower_bound"] = ub
#             workload["upper_bound"] = lb
#             workloads.append(workload)

# print(workloads)

workloads = {
    "workloads": workloads
}

if not Path(EXPERIMENT_DIR).exists():
    Path(EXPERIMENT_DIR).mkdir()

def getSSTFileInfo(directory_path) -> Tuple[int, int]:

    total_sst_files = 0
    total_sst_size = 0

    for filename in os.listdir(directory_path):
        if filename.endswith(".sst"):
            file_path = os.path.join(directory_path, filename)
            file_size = os.path.getsize(file_path)
            total_sst_files += 1
            total_sst_size += file_size
    
    return total_sst_files, total_sst_size

def create_workload(args, dir_name, log):
    os.chdir(EXPERIMENT_DIR)
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)

    workload_file = os.path.join("workload.txt")

    if os.path.exists(workload_file):
        shutil.copy(workload_file, os.path.join(EXPERIMENT_DIR, dir_name))
    else:
        process_output = os.popen(
            f"../../../../emulator/emu_runner {args} -E 256"
        ).read()
        shutil.copy(workload_file, os.path.join(EXPERIMENT_DIR, dir_name))
        log.write(f"{process_output}\n")
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

    args = f" {params} > '{dir_name}.log'"
    log.write(f"../../working_version {args}")
    process_output = os.popen(f"../../working_version {args}").read()
    log.write(f"{process_output}\n")

    # files_to_move = [f for f in os.listdir(db_dir) if f.startswith("LOG")]

    sst_files_count, sst_files_size = getSSTFileInfo(db_dir)

    # open a file and write the stats
    with open("sst_file_size_and_count.txt", "a") as f:
        log.write(f"writing stats to sst_file_size_and_count.txt\n")
        f.write(f"{sst_files_count}\t{sst_files_size}\n")

    # for file in files_to_move:
    #     source_path = os.path.join(db_dir, file)
    #     destination_path = os.path.join(os.getcwd(), file)
    #     shutil.move(source_path, destination_path)

    workload_file = os.path.join(os.path.join(os.getcwd(),"workload.txt"))

    if os.path.exists(workload_file):
        log.write("removing workload.txt\n")
        os.remove(workload_file)

    if os.path.exists(db_dir):
        log.write("removing db_working_home\n")
        shutil.rmtree(db_dir)

    log.write(" -------------- DONE -------------- \n\n\n\n")
    os.chdir(CURR_DIR)

if __name__ == "__main__":
    for workload in workloads["workloads"]:
        log = open(LOG_FILE, "a")
        gen_workload_args = ""
        run_args = ""
        dir_name = ""

        if "inserts" in workload:
            run_args += f" -I {workload['inserts']}"
            gen_workload_args += f" -I {workload['inserts']}"
            dir_name += (
                f"I {workload['inserts']}"
                if dir_name == ""
                else f" I {workload['inserts']}"
            )
        if "updates" in workload:
            run_args += f" -U {workload['updates']}"
            gen_workload_args += f" -U {workload['updates']}"
            dir_name += (
                f"U {workload['updates']}"
                if dir_name == ""
                else f" U {workload['updates']}"
            )
        if "range_queries" in workload:
            run_args += f" -S {workload['range_queries']}"
            run_args += f" -Y {workload['selectivity']}"
            gen_workload_args += f" -S {workload['range_queries']}"
            gen_workload_args += f" -Y {workload['selectivity']}"
            dir_name += (
                f"S {workload['range_queries']}"
                if dir_name == ""
                else f" S {workload['range_queries']}"
            )
            dir_name += f" Y {workload['selectivity']}"
        if "size_ratio" in workload:
            run_args += f" -T {workload['size_ratio']}"
            dir_name += (
                f"T {workload['size_ratio']}"
                if dir_name == ""
                else f" T {workload['size_ratio']}"
            )
        # if "write_cost" in workload:
        #     run_args += f" --wc {workload['write_cost']}"
        #     dir_name += (
        #         f"wc {workload['write_cost']}"
        #         if dir_name == ""
        #         else f" wc {workload['write_cost']}"
        #     )
        if "lower_bound" in workload:
            run_args += f" --lb {workload['lower_bound']}"
            dir_name += (
                f"lb {workload['lower_bound']}"
                if dir_name == ""
                else f" lb {workload['lower_bound']}"
            )
        if "upper_bound" in workload:
            run_args += f" --ub {workload['upper_bound']}"
            dir_name += (
                f"ub {workload['upper_bound']}"
                if dir_name == ""
                else f" ub {workload['upper_bound']}"
            )
        if "range_query_enabled" in workload:
            run_args += f" --rq {workload['range_query_enabled']}"
            dir_name += (
                f"rq {workload['range_query_enabled']}"
                if dir_name == ""
                else f" rq {workload['range_query_enabled']}"
            )

        log.write(f"Creating workload for .. {run_args}\n")
        print("Creating workload for .. ", run_args)
        create_workload(gen_workload_args, dir_name, log)
        log.write(f"Running workload for .. {run_args}\n")
        run_workload(run_args, dir_name, log)

        log.close()

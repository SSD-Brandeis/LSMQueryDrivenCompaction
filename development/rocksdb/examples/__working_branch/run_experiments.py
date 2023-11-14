import os
import time
import shutil
import json
from pathlib import Path
from typing import List

CURR_DIR = Path(__file__).parent
project_dir = Path(__file__).parent.absolute().__str__()
# WORKLOAD_DIR = CURR_DIR.joinpath("workloads")
EXPERIMENT_DIR = Path(__file__).parent.joinpath("experiments-Nov-9-varing-range-and-varing-selectivity").absolute().__str__()
OUTPUT_FILE = Path(__file__).parent.joinpath("stats.txt").absolute().__str__()
LOG_FILE = Path(__file__).parent.joinpath("logs.txt").absolute().__str__()


# if not WORKLOAD_DIR.exists():
#     WORKLOAD_DIR.mkdir()

if not Path(EXPERIMENT_DIR).exists():
    Path(EXPERIMENT_DIR).mkdir()


def create_workload(args, dir_name, log):
    os.chdir(EXPERIMENT_DIR)
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)

    os.chdir(dir_name)
    process_output = os.popen(f"../../../../../emulator/emu_runner {args} -E 1024").read()
    log.write(f"{process_output}\n")
    os.chdir(project_dir)


def run_workload(params, dir_name, log):
    os.chdir(EXPERIMENT_DIR)
    os.chdir(dir_name)

    log.write(" -------------- STARTING -------------- \n")

    db_dir = os.path.join(os.getcwd(), "db_working_home")
    # if os.path.exists(db_dir):
    #     log.write("removing db_working_home\n")
    #     shutil.rmtree(db_dir)

    # args = f"> '{dir_name} rq off.log' -V 1 {params}"
    # print(" ------------- running for rq off", dir_name, " --------------")
    # process_output = os.popen(f"../../working_version {args}").read()
    # log.write(f"{process_output}\n")

    # time.sleep(5)
    print("\nrunning workload\n")
    if os.path.exists(db_dir):
        log.write("removing db_working_home\n")
        shutil.rmtree(db_dir)

    args = f"> '{dir_name}.log' -V 1 {params}"
    print("running for rq on", dir_name)
    process_output = os.popen(f"../../working_version {args}").read()
    log.write(f"{process_output}\n")

    files_to_move = [f for f in os.listdir(db_dir) if f.startswith("LOG")]

    for file in files_to_move:
        source_path = os.path.join(db_dir, file)
        destination_path = os.path.join(os.getcwd(), file)
        shutil.move(source_path, destination_path)

    if os.path.exists(db_dir):
        log.write("removing db_working_home\n")
        shutil.rmtree(db_dir)

    log.write(" -------------- DONE -------------- ")
    os.chdir(CURR_DIR)

if __name__ == "__main__":
    # read experments to run file `experiments.txt`
    experiements_to_run = list()
    # workloads = json.load(open("experiments.json"))
    workloads = {"workloads": [
        # {
        #     "inserts": 250000,
        #     "updates": 125000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "range_query_enabled": 0
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 125000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 125000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     # "write_cost": 0.25,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },


        ############# NOVEMBER 9th 2023 ##############
        
        ## Change the range queries from 10, 100, 500, 1000, 2000
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 10,
            "selectivity": 0.25,
            "size_ratio": 3,
            "range_query_enabled": 0
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 10,
            "selectivity": 0.25,
            "size_ratio": 3,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 10,
            "selectivity": 0.25,
            "size_ratio": 3,
            "upper_to_lower_ratio": 0.4,
            "lower_to_upper_ratio": 0.8,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.25,
            "size_ratio": 3,
            "range_query_enabled": 0
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.25,
            "size_ratio": 3,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.25,
            "size_ratio": 3,
            "upper_to_lower_ratio": 0.4,
            "lower_to_upper_ratio": 0.8,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 500,
            "selectivity": 0.25,
            "size_ratio": 3,
            "range_query_enabled": 0
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 500,
            "selectivity": 0.25,
            "size_ratio": 3,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 500,
            "selectivity": 0.25,
            "size_ratio": 3,
            "upper_to_lower_ratio": 0.4,
            "lower_to_upper_ratio": 0.8,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 1000,
            "selectivity": 0.25,
            "size_ratio": 3,
            "range_query_enabled": 0
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 1000,
            "selectivity": 0.25,
            "size_ratio": 3,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 1000,
            "selectivity": 0.25,
            "size_ratio": 3,
            "upper_to_lower_ratio": 0.4,
            "lower_to_upper_ratio": 0.8,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 2000,
            "selectivity": 0.25,
            "size_ratio": 3,
            "range_query_enabled": 0
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 2000,
            "selectivity": 0.25,
            "size_ratio": 3,
            "range_query_enabled": 1
        },        
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 2000,
            "selectivity": 0.25,
            "size_ratio": 3,
            "upper_to_lower_ratio": 0.4,
            "lower_to_upper_ratio": 0.8,
            "range_query_enabled": 1
        },

        ### Change the selectivity from 0.10, 0.20, 0.40, 0.60, 0.80  VANILLA
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.10,
            "size_ratio": 3,
            "range_query_enabled": 0
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.20,
            "size_ratio": 3,
            "range_query_enabled": 0
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.40,
            "size_ratio": 3,
            "range_query_enabled": 0
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.60,
            "size_ratio": 3,
            "range_query_enabled": 0
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.80,
            "size_ratio": 3,
            "range_query_enabled": 0
        },

        ### Change the selectivity from 0.10, 0.20, 0.40, 0.60, 0.80   RQDC = 1
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.10,
            "size_ratio": 3,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.20,
            "size_ratio": 3,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.40,
            "size_ratio": 3,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.60,
            "size_ratio": 3,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.80,
            "size_ratio": 3,
            "range_query_enabled": 1
        },

        ### Change the selectivity from 0.10, 0.20, 0.40, 0.60, 0.80   RQDC = 1 with UTL AND LTU
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.10,
            "size_ratio": 3,
            "upper_to_lower_ratio": 0.4,
            "lower_to_upper_ratio": 0.8,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.20,
            "size_ratio": 3,
            "upper_to_lower_ratio": 0.4,
            "lower_to_upper_ratio": 0.8,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.40,
            "size_ratio": 3,
            "upper_to_lower_ratio": 0.4,
            "lower_to_upper_ratio": 0.8,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.60,
            "size_ratio": 3,
            "upper_to_lower_ratio": 0.4,
            "lower_to_upper_ratio": 0.8,
            "range_query_enabled": 1
        },
        {
            "inserts": 250000,
            "updates": 125000,
            "range_queries": 100,
            "selectivity": 0.80,
            "size_ratio": 3,
            "upper_to_lower_ratio": 0.4,
            "lower_to_upper_ratio": 0.8,
            "range_query_enabled": 1
        },







        ###### OLDER EXPERIMENTS ########
        # {
        #     "inserts": 250000,
        #     "updates": 125000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 10,
        #     "range_query_enabled": 0
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 125000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 10,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 125000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 10,
        #     "write_cost": 0.25,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 125000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 10,
        #     "write_cost": 0.50,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 125000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 10,
        #     "write_cost": 0.75,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 125000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 10,
        #     "write_cost": 1.0,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # }

        # # Size Ratio = 3 with 100 percent updates
        # {
        #     "inserts": 250000,
        #     "updates": 250000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "range_query_enabled": 0
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 250000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 250000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 0.25,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 250000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 0.50,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 250000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 0.75,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 250000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 1.0,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },

        # # Size Ratio = 10 with 150 percent updates
        # {
        #     "inserts": 250000,
        #     "updates": 375000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "range_query_enabled": 0
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 375000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 375000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 0.25,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 375000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 0.50,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 375000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 0.75,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 375000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 1.0,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },

        # # Size Ratio = 10 with 200 percent updates
        # {
        #     "inserts": 250000,
        #     "updates": 500000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "range_query_enabled": 0
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 500000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 500000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 0.25,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 500000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 0.50,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 500000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 0.75,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        # {
        #     "inserts": 250000,
        #     "updates": 500000,
        #     "range_queries": 100,
        #     "selectivity": 0.25,
        #     "size_ratio": 3,
        #     "write_cost": 1.0,
        #     "upper_to_lower_ratio": 0.4,
        #     "lower_to_upper_ratio": 0.8,
        #     "range_query_enabled": 1
        # },
        ]}

    for workload in workloads["workloads"]:
        log = open(LOG_FILE, "a")
        gen_workload_args = ""
        run_args = ""
        dir_name = ""

        if "inserts" in workload:
            gen_workload_args += f" -I {workload['inserts']}"
            dir_name += (
                f"I {workload['inserts']}"
                if dir_name == ""
                else f" I {workload['inserts']}"
            )
        if "updates" in workload:
            gen_workload_args += f" -U {workload['updates']}"
            dir_name += (
                f"U {workload['updates']}"
                if dir_name == ""
                else f" U {workload['updates']}"
            )
        if "range_queries" in workload and "selectivity" in workload:
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
        if "write_cost" in workload:
            run_args += f" --wc {workload['write_cost']}"
            dir_name += (
                f"wc {workload['write_cost']}"
                if dir_name == ""
                else f" wc {workload['write_cost']}"
            )
        if "upper_to_lower_ratio" in workload:
            run_args += f" --utl {workload['upper_to_lower_ratio']}"
            dir_name += (
                f"utl {workload['upper_to_lower_ratio']}"
                if dir_name == ""
                else f" utl {workload['upper_to_lower_ratio']}"
            )
        if "lower_to_upper_ratio" in workload:
            run_args += f" --ltu {workload['lower_to_upper_ratio']}"
            dir_name += (
                f"ltu {workload['lower_to_upper_ratio']}"
                if dir_name == ""
                else f" ltu {workload['lower_to_upper_ratio']}"
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


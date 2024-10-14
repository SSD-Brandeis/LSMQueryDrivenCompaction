import os
import shutil
import logging
from pathlib import Path

# paths and file names
CURR_DIR = Path(__file__).parent
PROJECT_DIR = CURR_DIR.absolute()
EXPERIMENTS_DIR = CURR_DIR.joinpath(".vstats").absolute()
WORKLOAD_FILE = "workload.txt"

LOG_FILE = CURR_DIR.joinpath("logs.txt").absolute()
LOAD_GEN_PATH = f"{CURR_DIR.absolute()}/bin/load_gen"
WORKING_VERSION = f"{CURR_DIR.absolute()}/bin/working_version"

# directory tag
TAG = "heatmap4"

DEFAULT_ENTRY_SIZES = [16]
METADATA_SIZE = 8
COMPACTION_STYLE = 1

if not os.path.exists(EXPERIMENTS_DIR):
    os.mkdir(EXPERIMENTS_DIR)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:\t%(message)s",
    handlers=[logging.FileHandler(LOG_FILE, mode="w"), logging.StreamHandler()],
)


def create_workload(args, dir_name):
    """Create workload files for the experiment."""
    try:
        os.chdir(PROJECT_DIR)
        # if not os.path.exists(dir_name):
        #     os.mkdir(dir_name)

        if os.path.exists(WORKLOAD_FILE):
            logging.info("Found already generated workload, Replacing ...")

            os.chdir(EXPERIMENTS_DIR)
            if not os.path.exists(dir_name):
                os.mkdir(dir_name)

            shutil.copy(os.path.join(PROJECT_DIR, WORKLOAD_FILE), os.path.join(EXPERIMENTS_DIR, dir_name))
        else:
            process_output = os.popen(f"{LOAD_GEN_PATH} {args}").read()
            logging.info(f"Workload generation output: {process_output}")

            os.chdir(EXPERIMENTS_DIR)
            if not os.path.exists(dir_name):
                os.mkdir(dir_name)

            shutil.copy(os.path.join(PROJECT_DIR, WORKLOAD_FILE), os.path.join(EXPERIMENTS_DIR, dir_name))
    except Exception as e:
        logging.error(f"Error in create_workload: {e}")
    finally:
        os.chdir(PROJECT_DIR)

# def create_workload(args, dir_name, flag=False):
#     """Create workload files for the experiment."""

#     try:
#         os.chdir(EXPERIMENTS_DIR)
#         if not os.path.exists(dir_name):
#             os.mkdir(dir_name)
#             os.chdir(dir_name)

#         if flag:
#             items = dir_name.split(' ')[:-4]
#             items[-7] = "0"
#             van_workload = os.path.join(" ".join(items))
#             shutil.copy(os.path.join("..", van_workload, WORKLOAD_FILE), os.path.join(EXPERIMENTS_DIR, dir_name))
#             return

#         if os.path.exists(WORKLOAD_FILE):
#             logging.info("Found already generated workload, Replacing ...")
#             shutil.copy(WORKLOAD_FILE, os.path.join(EXPERIMENTS_DIR, dir_name))
#         else:
#             logging.info(f"{LOAD_GEN_PATH} {args}")
#             process_output = os.popen(f"{LOAD_GEN_PATH} {args}").read()
#             logging.info(f"Workload generation output: {process_output}")
#             # shutil.copy(WORKLOAD_FILE, os.path.join(EXPERIMENTS_DIR, dir_name))
#     except Exception as e:
#         logging.error(f"Error in create_workload: {e}")
#     finally:
#         os.chdir(PROJECT_DIR)

def run_workload(params, dir_name):
    """Run the generated workload for the experiment."""
    try:
        os.chdir(EXPERIMENTS_DIR)
        os.chdir(dir_name)

        logging.info(" -------------- STARTING -------------- ")

        db_dir = os.path.join(os.getcwd(), "db")
        workload_txt = os.path.join(os.getcwd(), WORKLOAD_FILE)

        logging.info(f"Running workload with params: {params}")
        if os.path.exists(db_dir):
            logging.info("Removing db")
            shutil.rmtree(db_dir)

        args = f" {params}"
        logging.info(f"{WORKING_VERSION} {args} -C {COMPACTION_STYLE} > workload.log")
        process_output = os.popen(
            f"{WORKING_VERSION} {args} -C {COMPACTION_STYLE} > workload.log"
        ).read()
        logging.info(f"Workload run output: {process_output}")

        if os.path.exists(db_dir):
            logging.info("Removing db")
            shutil.rmtree(db_dir)

        # if os.path.exists(workload_txt):
        #     logging.info("Removing workload.txt")
        #     os.remove(workload_txt)

        logging.info(" -------------- DONE -------------- ")
    except Exception as e:
        logging.error(f"Error in run_workload: {e}")
    finally:
        os.chdir(CURR_DIR)


# def get_bounds(lowest, highest, num_points):
#     """Get a list of bounds between the lowest and highest values."""
#     points = []

#     def find_midpoints(start, end, point):
#         if point == 1:
#             return [start, end]
#         midpoint = (start + end) / 2
#         left_point = point // 2
#         right_point = point - left_point
#         points.append(midpoint)
#         find_midpoints(start, midpoint, left_point)
#         find_midpoints(midpoint, end, right_point)

#     find_midpoints(lowest, highest, num_points)
#     return sorted(points) + [highest]


if __name__ == "__main__":
    # Parameters for experiments
    size_ratios = [6]
    inserts = 4_500_000
    updates = 1_125_000  # 25 %
    range_queries = 9000  # 0.002 %
    selectivity = 0.1 # 10 %
    entries_per_page = 64
    number_of_pages = 64
    # same_range_queries = 100
    # overlapping_percent = 0.98

    for size_ratio in size_ratios:
        xx = size_ratio-1
        bounds = sorted([size_ratio/(2**x) for x in range(xx-4, xx+5)])

        # lower_bounds = get_bounds(0, size_ratio*0.25, 8)
        # upper_bounds = get_bounds(0, size_ratio*0.5, 5)

        lower_upper_bounds = list()

        for lb in bounds:
            for ub in bounds:
                if lb < ub:
                    lower_upper_bounds.append((lb, ub))

        for entry_size in DEFAULT_ENTRY_SIZES:
            buffer_size = entry_size * entries_per_page * number_of_pages
            logging.info(f"Buffer size: {buffer_size}")

            EXPERIMENTS_DIR = CURR_DIR.joinpath(".vstats", 
                f"experiments-{TAG}-E{entry_size}-B{entries_per_page}-S{range_queries}-Y{selectivity}-T{size_ratio}"
            ).absolute()

            if not EXPERIMENTS_DIR.exists():
                EXPERIMENTS_DIR.mkdir()

            os.chdir(EXPERIMENTS_DIR)
            logging.info(f"Current Directory: {os.getcwd()}")

            directory_name = (
                f"I {inserts} U {updates} S {range_queries} Y {selectivity} T {size_ratio}"
            )
            arguments = f"-I {inserts} -U {updates} -S {range_queries} -Y {selectivity} -E {entry_size}"
            lower_bound, upper_bound = lower_upper_bounds[0]

            if size_ratio not in []:
                # vanilla run
                create_workload(
                    arguments,
                    directory_name + f" rq 0 re 0 E {entry_size} B {entries_per_page}",
                )

                run_workload(
                    arguments
                    + f" -B {entries_per_page} -P {number_of_pages} -T {size_ratio} --rq 0",
                    directory_name + f" rq 0 re 0 E {entry_size} B {entries_per_page}",
                )

            # range reduce run
            for lower_bound, upper_bound in lower_upper_bounds:
                # if (size_ratio, lower_bound, upper_bound) not in done_bounds and (size_ratio, lower_bound, upper_bound) not in error_bounds:
                create_workload(
                    arguments,
                    directory_name + f" rq 1 re 0 E {entry_size} B {entries_per_page} lb {lower_bound} ub {upper_bound}",
                )

                run_workload(
                    arguments + f" -B {entries_per_page} -P {number_of_pages} -T {size_ratio} --rq 1 --lb {lower_bound} --ub {upper_bound}",
                    directory_name + f" rq 1 re 0 E {entry_size} B {entries_per_page} lb {lower_bound} ub {upper_bound}"
                )

            os.chdir(EXPERIMENTS_DIR.parent)
        os.chdir(EXPERIMENTS_DIR.parent.parent.absolute())

    logging.info("Experiment Completed.")

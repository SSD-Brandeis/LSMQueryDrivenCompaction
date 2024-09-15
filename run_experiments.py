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
TAG = "heatmaps2"

# workload specification
"""
    DATA_SIZE   SIZE_RATIO      LEVELS (excluding level 0)
    1966080         2             4


"""
# DATA_SIZE = 1_966_080
# DEFAULT_FILE_SIZE = 65_536

# DEFAULT_INSERTS = ...
# DEFAULT_UPDATES = 0
# DEFAULT_RANGE_QUERIES = 0
# DEFAULT_SELECTIVITY = 0
DEFAULT_ENTRY_SIZES = [16]  # [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]  # (E)

# # with each entry we add a 8 byte meta data that includes (sequence number and key type)
METADATA_SIZE = 8

# # system knobs
# DEFAULT_NUMBER_OF_PAGES = 4  # (P)
# DEFAULT_ENTRIES_PER_PAGE = ...  # (B) 65,536 / (E * P) = B
# DEFAULT_LOWER_BOUNDS = [0.25]
# DEFAULT_UPPER_BOUNDS = [4]
# DEFAULT_SIZE_RATIO = 2
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

        if os.path.exists(workload_txt):
            logging.info("Removing workload.txt")
            os.remove(workload_txt)

        logging.info(" -------------- DONE -------------- ")
    except Exception as e:
        logging.error(f"Error in run_workload: {e}")
    finally:
        os.chdir(CURR_DIR)


def get_bounds(lowest, highest, num_points):
    """Get a list of bounds between the lowest and highest values."""
    points = []

    def find_midpoints(start, end, point):
        if point == 1:
            return [start, end]
        midpoint = (start + end) / 2
        left_point = point // 2
        right_point = point - left_point
        points.append(midpoint)
        find_midpoints(start, midpoint, left_point)
        find_midpoints(midpoint, end, right_point)

    find_midpoints(lowest, highest, num_points)
    return sorted(points) + [highest]


if __name__ == "__main__":
    # Parameters for experiments
    size_ratios = [10, 9, 8] #, 7, 6, 5, 4, 3, 2]
    inserts = 4_500_000
    updates = 1_125_000  # 25 %
    range_queries = 4500  # 0.1 %
    selectivity = 0.1 # 10 %
    entries_per_page = 64
    number_of_pages = 64

    for size_ratio in size_ratios:
        lower_bounds = get_bounds(0, size_ratio*0.25, 8)
        upper_bounds = get_bounds(0, size_ratio*0.5, 5)

        done_bounds = {(10, 0.3125, 1.25), (10, 0.3125, 2.5), (10, 0.3125, 3.75)}
        error_bounds = {(10, 0.3125, 4.375), (10, 0.3125, 5.0)}
        might_perform_bad = set()

        lower_upper_bounds = []

        for lb in lower_bounds:
            for ub in upper_bounds:
                if lb < ub and (lb, ub) not in done_bounds:
                    lower_upper_bounds.append((lb, ub))

        for entry_size in DEFAULT_ENTRY_SIZES:
            # actual_entry_size = entry_size + METADATA_SIZE
            # inserts = DATA_SIZE // actual_entry_size
            # entries_per_page = DEFAULT_FILE_SIZE // (actual_entry_size * DEFAULT_NUMBER_OF_PAGES)
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


            if size_ratio not in [10]:
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

            # # vanilla with level renaming run
            # create_workload(
            #     arguments,
            #     directory_name + f" rq 0 re 1 E {entry_size} B {entries_per_page}",
            # )

            # run_workload(
            #     arguments
            #     + f" -B {entries_per_page} -P {number_of_pages} -T {size_ratio} --rq 0 --re 1",
            #     directory_name + f" rq 0 re 1 E {entry_size} B {entries_per_page}",
            # )

            # range reduce run
            for lower_bound, upper_bound in lower_upper_bounds:
                if (size_ratio, lower_bound, upper_bound) not in done_bounds and (size_ratio, lower_bound, upper_bound) not in error_bounds:
                    create_workload(
                        arguments,
                        directory_name + f" rq 1 re 0 E {entry_size} B {entries_per_page} lb {lower_bound} ub {upper_bound}"
                    )

                    run_workload(
                        arguments + f" -B {entries_per_page} -P {number_of_pages} -T {size_ratio} --rq 1 --lb {lower_bound} --ub {upper_bound}",
                        directory_name + f" rq 1 re 0 E {entry_size} B {entries_per_page} lb {lower_bound} ub {upper_bound}"
                    )

            # # range reduce with level renamining run
            # for lower_bound, upper_bound in lower_upper_bounds:
            #     create_workload(
            #         arguments,
            #         directory_name + f" rq 1 re 1 E {entry_size} B {entries_per_page} lb {lower_bound} ub {upper_bound}"
            #     )

            #     run_workload(
            #         arguments + f" -B {entries_per_page} -P {number_of_pages} -T {size} --rq 1 --re 1 --lb {lower_bound} --ub {upper_bound}",
            #         directory_name + f" rq 1 re 1 E {entry_size} B {entries_per_page} lb {lower_bound} ub {upper_bound}"
            #     )

            os.chdir(EXPERIMENTS_DIR.parent)
        os.chdir(EXPERIMENTS_DIR.parent.parent.absolute())

    logging.info("Experiment Completed.")

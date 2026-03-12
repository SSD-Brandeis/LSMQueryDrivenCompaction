# RangeReduce: LSM Compactions Driven by Range Queries
RangeReduce is a range query-aware LSM-engne that piggybacks on the reads performed by range queries to write the valid data back to storage as part of a single sorted run. RangeReduce improves range query latency and operational throughput, reduces space amplification and overall data movement, and significantly diminishes compaction debt.

## System Requirements
- C++17 compatible compiler (e.g., g++ 7 or higher)
- CMake 3.10 or higher
- RocksDB 6.20 or higher
- Tectonic CLI (included in the `bin` directory)

## Getting Started
1. Clone the repository:
    ```bash
    git clone https://github.com/SSD-Brandeis/RangeReduce.git
    cd RangeReduce
    ```

2. Setup and build the project:
    ```bash
    bash ./scripts/setup.sh
    bash ./scripts/rebuild.sh
    ```

3. Run experiments:
    ```bash
    bash ./scripts/run/<experiment to run>.sh
    ```

4. Every experiments creates stats in .vstats directory with a tag given in bash script (e.g. .vstats/experiments-<TAG>-...). To generate plots:
    ```bash
    cd src/.notebooks
    bash plot_*.py        # * is just the tag or figure number

## Workload Generator
We use Tectonic as well as KV Workload Generator to generate workloads for our experiments. To learn more about KV-WorkloadGenerator, visit the [KV-WorkloadGenerator GitHub repository](https://github.com/SSD-Brandeis/KV-WorkloadGenerator) and [Tectonic](https://github.com/SSD-Brandeis/Tectonic).




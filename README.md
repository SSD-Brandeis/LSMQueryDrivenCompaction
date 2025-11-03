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
    git clone https://github.com/SSD-Brandeis/LSMQueryDrivenCompaction.git
    cd LSMQueryDrivenCompaction
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

## Workload Generator
We use Tectonic to generate workloads for our experiments. To learn more about KV-WorkloadGenerator, visit the [KV-WorkloadGenerator GitHub repository](https://github.com/SSD-Brandeis/KV-WorkloadGenerator).




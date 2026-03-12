cmake_minimum_required(VERSION 3.10)
project(LSMQueryDrivenCompaction)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)

option(WITH_TESTS OFF)
option(WITH_TOOLS OFF)
option(WITH_ALL_TESTS OFF)
option(WITH_BENCHMARK_TOOLS OFF)
option(WITH_CORE_TOOLS OFF)
option(WITH_TRACE_TOOLS OFF)

add_subdirectory(lib/rocksdb)

add_custom_target(tectonic-cli ALL
    COMMAND cargo build --release
    COMMAND ${CMAKE_COMMAND} -E copy
            ${CMAKE_CURRENT_SOURCE_DIR}/lib/tectonic/target/release/tectonic-cli
            ${CMAKE_CURRENT_SOURCE_DIR}/bin/tectonic-cli
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/lib/tectonic
    COMMENT "Building tectonic in release mode"
)

set(SOURCES
    src/aux_time.cc 
    src/buffer.cc
    src/db_env.cc
    src/event_listners.cc
    src/utils.cc
    src/run_workload.cc
    src/working_version.cc
)

target_compile_definitions(rocksdb PRIVATE PRINT_TREE)
target_compile_definitions(rocksdb-shared PRIVATE PRINT_TREE)
add_executable(working_version ${SOURCES})

target_include_directories(working_version PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/lib/rocksdb/include
)

target_compile_options(working_version PRIVATE -O2)

target_link_libraries(working_version PRIVATE
    rocksdb
    Threads::Threads
)

add_dependencies(working_version tectonic-cli)
set_target_properties(working_version PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin
)
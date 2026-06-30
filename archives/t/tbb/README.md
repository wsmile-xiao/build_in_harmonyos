# tbb (Intel Threading Building Blocks)

Intel Threading Building Blocks (oneTBB) - A flexible C++ library for parallel programming.

## Description

oneTBB is a flexible C++ library that simplifies the work of adding parallelism to complex applications, even those that are already designed using serial algorithms or other parallel programming approaches. The library enables you to specify logical parallelism instead of threads, letting you focus on the task at hand rather than thread mechanics.

## Key Features

- Task-based parallelism
- Concurrent containers (hash maps, vectors, queues)
- Parallel algorithms (for, reduce, sort)
- Synchronization primitives (mutexes, condition variables)
- Memory allocators (scalable allocator)

## Build System

- CMake
- No traditional configure/make

## Compile Dependencies

- cmake >= 4.1.2
- hwloc >= 2.13.0 (optional)
- clang >= 15.0.4

## Compiled Versions

- 2023.0.0 (2026-05-29)

## Official Repository

https://github.com/oneapi-src/oneTBB
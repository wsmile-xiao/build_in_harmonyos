# bs-thread-pool

BS::thread_pool is a fast, lightweight, modern, and easy-to-use C++17/C++20/C++23 thread pool library.

## OHOS adaptation

- Header-only: ship `include/BS_thread_pool.hpp`, no compilation of the library itself.
- Upstream test `tests/BS_thread_pool_test.cpp` (custom harness) is compiled and run in `build()` with `tests stdout` (standard suite only, no benchmarks).
- Native extensions stay disabled so musl affinity/priority probes are skipped by upstream.

## Dependencies

None (C++17 standard library only).

## References

- https://github.com/bshoshany/thread-pool
- https://github.com/bshoshany/thread-pool/releases/tag/v5.1.0

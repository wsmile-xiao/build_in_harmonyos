# cpp-ipc

cpp-ipc is a high performance C++17 inter-process communication library:
shared memory channels, lock-free ring queues, process-shared mutex /
condition / waiter primitives, with Linux, Windows and FreeBSD backends
(upstream repository: https://github.com/mutouyun/cpp-ipc, MIT).

## OHOS adaptation

- Builds the official `v1.3.0` tag with its CMake project
  (`-DCMAKE_BUILD_TYPE=Release`), producing the static `libipc.a` plus
  the public `include/libipc/*.h` headers.
- No third-party dependencies: only the compiler, `pthread` and the empty
  musl `librt` stub are used.
- Two source patches, both guarded by library macros rather than a
  platform macro: upstream injects `std::unique_ptr` deduction guides into
  `namespace std`, which libc++ rejects because it declares `unique_ptr`
  inside an inline ABI namespace; and the robust-mutex unit test is kept on
  glibc Linux only, because musl does not implement
  `pthread_mutexattr_setrobust` / `pthread_mutex_consistent`.
- The consumer `test_package` exercises POSIX shared memory, a named
  process-shared mutex and a broadcast channel send/receive round trip.

## Known limitation

HongMeng's kernel does not implement the futex operations
`FUTEX_CMP_REQUEUE_PI`, `FUTEX_WAIT_REQUEUE_PI` and `FUTEX_TRYLOCK_PI`
(`ENOSYS`), so the upstream a0 condition-variable broadcast/wait path
degrades: tests that rely on broadcast time out or abort, while shared
memory and unicast queue paths work. Details are in `1.3.0/notes.md`.

## Dependencies

- None (libc / pthread only).

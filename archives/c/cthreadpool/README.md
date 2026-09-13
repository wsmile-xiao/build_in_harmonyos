# cthreadpool

`cthreadpool` is a minimal but powerful thread pool written in ANSI C
(Pithikos C-Thread-Pool): fixed-size POSIX worker threads with pause,
resume, wait, and destroy operations over a bounded job queue.

## OpenHarmony adaptation

- Source: https://github.com/Pithikos/C-Thread-Pool (official, MIT)
- Version `0.0-git20231218.4eb5a69` pins upstream commit `4eb5a69`
  (2023-12-18); upstream publishes no versioned releases.
- Build system: none upstream (custom direct-cc recipe compiles `thpool.c`
  into `libthpool.a` and `libthpool.so`).
- Runtime dependency: pthreads provided by the platform C library.
- No source patches: `thpool.c` uses only POSIX C and pthreads
  (`pthread_kill`/`sigaction` for pause, `prctl` thread naming under
  `__linux__` with ignored return value).
- Upstream `tests/*.sh` drivers run in the recipe `build()`; the 9
  valgrind-based leak cases are excluded because valgrind is unavailable
  on OHOS, and host-calibrated timing bounds are asserted as successful
  completion only. The Conan consumer test links the packaged library and
  checks exact task accounting plus the pause/resume lifecycle.

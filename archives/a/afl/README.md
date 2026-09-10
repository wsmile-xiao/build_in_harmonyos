# afl

American Fuzzy Lop (afl) is a security-oriented fuzzer written by Michal
Zalewski. It uses compile-time instrumentation (assembly-level, via the
`afl-gcc`/`afl-as` pair) and genetic algorithms to discover edge cases in
target programs.

- **Versions**: 1.35b
- **Homepage**: http://lcamtuf.coredump.cx/afl/ (offline; source mirrored at https://github.com/cmouse/afl-fuzz)
- **License**: Apache-2.0
- **Build System**: Makefile
- **Type**: CLI tool (fuzzer)

## OHOS Build Notes

Built tools:
- `afl-fuzz` — main fuzzer
- `afl-showmap` — trace map tool
- `afl-tmin` — test case minimizer
- `afl-gotcpu` — CPU affinity checker
- `afl-gcc` / `afl-as` — instrumentation compiler wrapper / assembler
- `afl-cmin` / `afl-plot` / `afl-whatsup` — helper scripts

Platform notes (HarmonyOS PC / arm64):
- SysV shared memory (`shmget`) is blocked by the OHOS sandbox (SIGSYS);
  the three tools are patched to use POSIX shared memory
  (`shm_open` + `ftruncate` + `mmap`), the same approach AFL++ takes with
  USEMMAP.
- The `make` `test_x86` gate is patched to be non-fatal on non-x86 builds.
- Classic afl's assembly instrumentation (`afl-as`) is x86-only — it cannot
  instrument aarch64 binaries. Functional scope on OHOS is **dumb-mode
  fuzzing** (`afl-fuzz -n`, no coverage feedback) plus the utility tools;
  the instrumentation mode is a documented upstream platform limitation.

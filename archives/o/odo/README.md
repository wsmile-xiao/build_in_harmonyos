# odo 0.2.2 for HarmonyOS PC

`odo` is an atomic, concurrency-safe odometer: it keeps a counter in a
memory-mapped file and updates it with a compare-and-swap, so that many
processes can increment/read/set a shared counter concurrently. This archive
packages the upstream 0.2.2 command-line tool for OHOS aarch64.

- Upstream: https://github.com/atomicobject/odo
- License: ISC
- Conan reference: `odo/0.2.2`
- Executables: `odo`

The recipe builds the plain Makefile project (C99 + POSIX) with the OHOS
clang toolchain. No third-party dependencies and no patches required — the
upstream source compiles unmodified. The test_package wraps the upstream
`test_odo` behavior as a consumer test exercising the packaged `odo` CLI.

## Usage

```bash
odo [name]        # increment (create +1 if missing)
odo -s 1234 name  # set counter to 1234
odo -c name       # print current value without updating
odo -p name       # increment AND print the new value
odo -r name       # reset counter to 0
```

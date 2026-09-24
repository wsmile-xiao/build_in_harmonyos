# libmill

libmill brings Go's concurrency primitives to C: coroutines (`go`), channels
(`chmake`, `chs`, `chr`) and a `choose` statement, on top of a small scheduler
that keeps each coroutine's stack in a separate heap block.

- Upstream: https://github.com/sustrik/libmill (http://libmill.org/)
- Release: 1.18
- License: MIT
- Build system: CMake
- Package form: `lib/libmill.a` + `include/libmill.h` (or `libmill.so` with
  `-o shared=True`)

## HarmonyOS PC adaptation

**No patches.** Two upstream details are handled from the recipe:

| Upstream | Handling |
|---|---|
| `cmake_minimum_required(VERSION 2.8.7)` | pass `CMAKE_POLICY_VERSION_MINIMUM=3.5` (CMake ≥ 3.28 refuses compatibility below 3.5) |
| no `install()` rules at all | `package()` copies the header and library directly |

`millinclude_HEADERS = libmill.h` in upstream's `Makefile.am` is the authority
for the public header, and `libmill.h` is self-contained.

## Compiler note (GCC vs clang)

`dns/dns.h` gates `dns_quietinit()` on the compiler: clang gets a
`_Pragma`-wrapped compound literal (an lvalue), GCC gets
`__extension__ ({ ...; })` (a statement expression). Taking the address of the
latter is an error, so **libmill does not compile with GCC** — but clang, which
is what the HarmonyOS worker uses, builds it cleanly.

## Upstream tests

`CMakeLists.txt` globs `tests/*.c` and registers one CTest case per file —
**18 cases**. They run for real inside `build()`:

```
ctest --output-on-failure --timeout 120
```

and cover channels, `choose`, coroutine-local storage, fd/file/signal
interaction, fork interaction, the scheduler clock, and loopback TCP/UDP/Unix
sockets. The seven programs under `perf/` are benchmarks, not tests (they have
no `add_test`), and are excluded from the count.

See `1.18/notes.md` for the full record and `1.18/test_package/MANIFEST.yml`
for the per-case audit.

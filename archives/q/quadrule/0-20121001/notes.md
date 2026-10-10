# quadrule 0-20121001 HarmonyOS PC adaptation

## Source and scope

- Upstream author: John Burkardt.
- Exact snapshot: Debian Science `upstream/0_20121001` tag, matching the
  version selected by the task.
- Language: C (accepted by the C/C++ task family).
- Build system: Autotools/libtool.
- Dependencies: libc and libm only; no third-party Conan dependencies.

## HarmonyOS adaptation

- The bundled 2012 GNU configuration scripts predate HarmonyOS. Two minimal
  portability patches recognize `HarmonyOS`/`OHOS` and preserve the canonical
  `aarch64-unknown-linux-ohos` triplet.
- One legacy call used glibc's obsolete `gamma()` alias. It is replaced with
  the standard C99 `tgamma()` function, preserving the mathematical result and
  allowing musl-based HarmonyOS to link the library.
- On OHOS, the recipe removes Autoconf's restrictive `umask 077` only from
  the generated `config.status` temporary-directory template. This prevents
  HMDFS permission mapping from making `subs1.awk` unreadable while leaving
  the upstream source files and normal platform behavior unchanged.
- Both shared and static Conan options are supported; static is the default so
  consumers have no runtime dependency on an extra loader search path.

## Upstream test inventory (R51)

| Inventory item | Result | Evidence |
|---|---:|---|
| `tests/` directory | 0 | Exact source archive file listing |
| Test source files | 0 | No test/check/prb source in the snapshot |
| Automake `TESTS` / `check_PROGRAMS` | 0 | `Makefile.am` inspection |
| Official `make check` | 0 tests | Runs successfully; no registered targets |

The upstream measured baseline is therefore **0 tests**. The Conan consumer
suite adds eight independently registered scenarios using the installed
library API: Legendre, Hermite, Laguerre, Clenshaw-Curtis, interval adjustment,
helper functions, the `summer` integrator, and a HarmonyOS AArch64 ABI check.

## Validation result

- Native upstream build and `make check`: pass (0 registered tests).
- HarmonyOS AArch64 Conan build: pass.
- Consumer tests: **8/8 pass (100%)**.

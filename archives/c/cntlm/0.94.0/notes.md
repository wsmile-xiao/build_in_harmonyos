# cntlm 0.94.0 adaptation notes

## Build environment

- Build system: makefile (plain Makefile plus custom `configure` shell script)
- Compiler: clang/clang++ (OHOS profile, Conan-provided CC)
- Status: built
- Upstream: https://github.com/versat/cntlm, tag 0.94.0

## Build steps

1. `get()` downloads `https://github.com/versat/cntlm/archive/refs/tags/0.94.0.tar.gz` (sha256 `da9e98f2...198500`).
2. `generate()` exports Conan `CC` via `conanbuild` script from `tools.build:compiler_executables:c`.
3. `build()` runs `CC="<conan-cc>" sh ./configure` to create `configure-stamp` and `config/config.h`.
4. `build()` runs `make CC="<conan-cc>" -j1` to link the `cntlm` binary.
5. `package()` copies `cntlm` to `bin/`, `doc/cntlm.1` to `share/man/man1`, `doc/cntlm.conf` to `share/doc/cntlm`.

## Issues and solutions

| # | Issue | Root cause | Solution |
|---|-------|------------|----------|
| 1 | Makefile auto-runs `./configure` via `$(shell ./configure)` using `/bin/sh` shebang | OHOS may not provide `/bin/sh` | Recipe pre-runs `sh ./configure` with `CONFIG_SHELL`, stamp then exists so make does not re-probe |
| 2 | Bare `${CC}` is empty on CI workers (R33) | Shell env not defined | Read compiler from `self.conf.get("tools.build:compiler_executables:c")` and pass explicitly |
| 3 | `make install` uses GNU `install -D -s` | Not portable to OHOS worker | Skip `make install`, manual `copy()` of binary, man page and sample config |
| 4 | Preflight `can't create /tmp/sh*.tmp: Read-only` + `Signal 9` in `./configure` | dash `$(...)` needs writable /tmp/sh* (ignores TMPDIR); probe execution `./config/*` killed on worker | Do not run `./configure`; synthesize `configure-stamp` + `config/config.h` in Python, compile-only probe checks, stamp blocks make auto-probe |
| 5 | Risky probes (strlcat/strlcpy/arc4random_buf/memset_s/gss) may exist on OHOS libc | Claiming 1 when missing breaks link | Conservative 0 (enables bundled fallbacks); certain ones audited: endian=1, gethostname=0, socklen_t=1, strdup=1 |
| 6 | `config.c`/`utils.c` fail with `use of undeclared identifier 'u_char'` under clang `-std=c99` on OHOS | `u_char` is a BSD/glibc typedef, not provided by OHOS libc under strict C99 (`_DEFAULT_SOURCE` not honored); `config.c` lacks `<sys/types.h>` entirely | Procedural fix in `build()` (`_fix_u_char_portability`): replace all `(u_char)` casts with standard `(unsigned char)` across `*.c`/`*.h` in Python; declarative conandata patch abandoned after worker Conan parser rejected the stream ("patch stream is incomplete") |

## Upstream test audit

- Searched upstream tree at tag 0.94.0: `Makefile` targets are `all/install/tgz/tbz2/deb/rpm/win`, no `check/test` target.
- File listing via GitHub API shows no `tests/`, `test/`, `*_test.c`, `CMakeLists.txt` or `meson.build`.
- Feature probes under `config/*.c` are configure-time checks, not a runnable test suite.
- Conclusion: upstream ships no test suite. `test_package/MANIFEST.yml` declares `upstream_tests_exist: false` with this audit.

## Verification

- `test_package` runs `test_cntlm.py`: help output check, version banner check, minimal config startup check.
- Expected on HarmonyOS aarch64: `cntlm` builds, `cntlm -h` prints usage containing `cntlm`, config startup binds a loopback proxy port.
- Real pass counts are filled from preflight evidence, not estimated here.

## Deliverables

| File | Description |
|------|-------------|
| `bin/cntlm` | NTLM proxy binary |
| `share/man/man1/cntlm.1` | Man page |
| `share/doc/cntlm/cntlm.conf` | Sample configuration |

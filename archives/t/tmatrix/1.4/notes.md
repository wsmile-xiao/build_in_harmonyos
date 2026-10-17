# tmatrix 1.4 - HarmonyOS PC (OHOS aarch64) adaptation notes

## Software

| Item | Value |
|------|-------|
| Name | tmatrix |
| Version | 1.4 (first adaptation, so the upstream version is used verbatim per R37) |
| Upstream | https://github.com/M4444/TMatrix |
| License | GPL-2.0-only |
| Language | C++17 |
| Build system | CMake >= 3.8 |
| Deliverable | single CLI executable `tmatrix` (application package) |
| Dependencies | ncurses (published as `ncurses/6.6`) |
| Archive path | `archives/t/tmatrix/1.4/` |

## Upstream test inventory (R51)

The v1.4 release tarball ships **no test suite**. Evidence gathered before adapting:

```
$ tar tzf TMatrix-v1.4.tar.gz | grep -iE 'test|spec'
(no matches)

$ grep -rn 'enable_testing\|add_test' CMakeLists.txt
(no matches)

$ ls .github/workflows/
(no test job; the directory carries only repository metadata)
```

`CMakeLists.txt` declares no `check`/`test` target either, so there is no
upstream `make check` / `ctest` to run inside `build()`. The upstream "test
surface" for this project is its command-line behaviour, so `test_package/`
drives the packaged executable and asserts on what it does.

Reported honestly for this PR: **upstream 0 cases; 9 assertions in
test_package, 8 executed and passed, 1 conditional** (T6b, see the terminfo
caveat below). As an unprivileged user with a reachable terminfo database all 9
execute and pass.

## Dependency check (W0)

```
$ conan download "ncurses/6.6" -r=ohpcd --only-recipe
  ncurses/6.6
    revisions
      3dcfd3b6d759300e8997800cefe8c61f (2026-08-07 15:55:31 UTC)
```

The recipe is published, and a matching OHOS aarch64 **binary** exists too
(verified with `conan install --requires=ncurses/6.6 -pr:h=ohos-aarch64-wsl
-pr:b=ohos-aarch64-wsl -r=ohpcd`, which downloaded revision
`d9a448fa2aa1885bf07d8caa897afb78` rather than building from source). No
dependency had to be adapted first, so no separate dependency PR was needed.

tmatrix has no other dependency: it only uses the C++17 standard library plus
ncurses.

## Adaptation work

One patch: `patches/0001-CMakeLists.txt.patch` against `CMakeLists.txt`,
generated with `ohc-run.py refresh-patch --auto tmatrix 1.4` (R3) and
registered in `conandata.yml`. It contains no platform conditional and no
`__OHOS__` macro (R8).

### 1. ncurses resolution: `find_package(Curses)` -> `find_package(ncurses CONFIG)`

CMake's `FindCurses` module has no sysroot notion. Because the recipe is a
cross build (`CMAKE_SYSTEM_NAME=Linux` + an OHOS `clang++` from the profile),
the module can only find the archive if the recipe seeds `CURSES_LIBRARY` by
hand - and then it contributes the archive *alone*:

```
-- Looking for cbreak in .../libncursesw.a
-- Looking for cbreak in .../libncursesw.a - found
-- Found Curses: .../libncursesw.a
...
/root/.../src/Terminal.cpp:8:10: fatal error: 'ncurses.h' file not found
```

`link_libraries(${CURSES_LIBRARIES})` propagates a path, not an include
directory. Switching to the `ncurses` CONFIG package that Conan generates makes
`ncurses::ncurses` carry both, and pins the link to the exact static
`libncursesw.a` this ecosystem publishes instead of whatever ncurses flavour a
sysroot probe happens to find.

### 2. Toolchain flags were being overwritten

`set(CMAKE_CXX_FLAGS "-Wall -Wextra -Wpedantic")` and
`set(CMAKE_CXX_FLAGS_RELEASE "-O2")` overwrite the cache values Conan injects
(the `-stdlib=libc++` selection and the build-type flags). The patch appends
instead, preserving upstream's warning set and `-O2`. `CMAKE_EXE_LINKER_FLAGS`
got the same treatment for the `-pthread` line.

### 3. `gzip` made optional for the man page

The `manpage` target shells out to `gzip` and is part of `all`, so a build image
without `gzip` fails for a cosmetic reason. The patch looks the compressor up
with `find_program()` and installs the plain man page when it is absent.

### 4. E077: the packaged executable has to be self-signed

CI builds #64687, #64859 and #64894 compiled cleanly and then failed in
`conan-build-test` with seven of eight `test_package` assertions red. The
signature was unmistakable and the split was diagnostic:

```
FAIL: T1 --version prints 'tmatrix version 1.4' (rc=126)
...
PASS: T7 artifact is a 64-bit AArch64 PIE ELF
```

Status 126 is the shell reporting that `execve()` failed, and T7 passed because
it only *reads* the ELF header. So the file was present, complete and of the
right architecture; the kernel simply refused to load it. Per **E077** the OHOS
kernel only loads an ELF carrying a *valid* `.codesign` section, and a freshly
linked executable only gets the linker's unsigned placeholder - so the packaged
binary was unsigned.

This had already been misdiagnosed twice. `e414ff57` chmod'ed a copy
("HMDFS exec bit") and `2da13a19` staged the copy onto
`/data/storage/el2/base/cache` ("exec-capable partition"). Build #64894 ran that
second revision and still returned 126 *from that very directory*, which
falsifies the location theory outright. E077's own `forbid_1_consequence`
predicts exactly this loop: an unsigned ELF "cannot be executed however the
permissions are set", and chasing `chmod` is the documented dead end.

The fix is the E077 four-step flow in `package()`, in the one order that works
(cronutils/1.1, qastools/1.4.0, qemu/11.1.1, jupp/3.1.41 all use it):

1. `llvm-objcopy --remove-section .codesign` - drop the unsigned placeholder.
   Mandatory first: `binary-sign-tool` refuses to overwrite an existing
   section (`.codesign section already exists`, SignElf 29).
2. sign - `binary-sign-tool sign -selfSign 1` into a sibling file.
3. `os.replace()` it over the original.
4. `os.chmod(0o755)` - signing leaves the output with no permission bits.

Step 2 runs with `env -u LD_LIBRARY_PATH` so the signer resolves its own system
libraries rather than the profile's SDK path (jupp/3.1.41). Only files with the
ELF magic are signed, so the bash-completion and zsh completion scripts
installed next to the binary are left alone. When the signing tools are absent
the recipe warns and continues rather than claiming a signature it did not make
(jupp/3.1.41), and never calls `self.run` against a missing tool, which would
otherwise abort with 127 on a host that has no OHOS SDK.

With the binary signed, `test_package` executes it where it sits, straight out
of the package folder - no staging copy. That is also what
`test_package/MANIFEST.yml` already documented
(`sh test_tmatrix.sh <package-folder>/bin/tmatrix`), so the code now matches its
own stated contract, and T7 asserts on the real delivered artifact. The
writable-copy path was removed rather than kept: it encoded a theory that CI
disproved, and it made the test depend on some unrelated directory being
writable.

## Knowledge base entries used

- **E077** - an OHOS executable needs a valid `.codesign` section or the kernel
  refuses to load it; `chmod` and relocating the file cannot substitute. The
  four-step remove/sign/replace/chmod flow is the fix, and its order is part of
  the contract.
- **E092** - CMake has no `HarmonyOS` platform module. The toolchain declares
  `CMAKE_SYSTEM_NAME=Linux` with `CMAKE_SYSTEM_PROCESSOR=aarch64`, which is the
  repository-wide convention (202+ recipes use the same pair).
- **E011** - generated scripts carrying a restrictive `umask` are a separate
  Autotools concern and did not apply here; noted so the next agent does not
  chase it for a CMake project.
- **R32** - `settings.os` is validated with `in ("Linux", "OHOS")`.
- **R33** - no bare `${CC}`/`${CFLAGS}` in `build()`; the compiler comes from
  the Conan toolchain.
- **R38** - the product is an executable, so `archives/t/tmatrix/commands.json`
  declares it as a `tool`.
- **R49** - nothing is injected into a shared prefix; `CMAKE_INSTALL_PREFIX` is
  `/` inside the package folder only.
- **R3** - the patch is tool-generated, not hand-written.

## Verification (W3)

```
$ conan create archives/t/tmatrix/1.4 --name=tmatrix --version=1.4 \
    -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
...
tmatrix/1.4: Package '5451db01063ffef70a6f03c02395d1808faeb5e5' created
======== Testing the package: Executing test ========
--- tmatrix 1.4 test_package: ALL PASS ---
```

Build produced 11 translation units, linked `tmatrix`, and installed
`bin/tmatrix`, `share/man/man6/tmatrix.6.gz`, the bash completion and the zsh
completion.

### test_package assertions

| # | Assertion | Result |
|---|-----------|--------|
| T1 | `--version` prints `tmatrix version 1.4` | PASS |
| T2 | `--help` prints the full option table | PASS |
| T3 | an unknown option is rejected *before* the render path | PASS |
| T4 | an out-of-range `--steps-per-sec` is rejected | PASS |
| T5 | fractional `--fall-speed=0.4,1.7` reaches the render path | PASS |
| T6 | the render path is entered under a pty | PASS |
| T6b | a painted frame carries the bright-attribute sequence | PASS / SKIP (see below) |
| T6c | out-of-range `--fall-speed=99,100` never reaches curses | PASS |
| T7 | the artifact is a 64-bit AArch64 PIE ELF | PASS |

T5 is the 1.4-specific one: fractional fall speeds are what the 1.4 release
notes call out, and `0.4,1.7` is a value the pre-1.4 integer parser could not
accept. T7 is the HarmonyOS-specific artifact assertion, reading the ELF header
directly with `od(1)` so no binutils are required.

### One caveat worth recording: T6b under uid 0

`ncurses/6.6` as published is configured without `USE_ROOT_ENVIRON`, so
`use_terminfo_vars()` resolves to `_nc_env_access()`, which returns false when
`euid == 0`. The consequence is observable:

```
$ TERMINFO=<ncurses>/share/terminfo tmatrix --version   # as root
ncurses: cannot initialize terminal type ($TERM="xterm"); exiting
$ ...                                                    # as an unprivileged uid
<frame painted, escape sequences on the pty>
```

This is a trait of the published ncurses package, not of this recipe, and it is
not worked around here (patching a dependency is out of scope for this PR). The
test therefore asserts that the render path was *entered* - a painted escape
sequence, the ncurses terminal-type diagnostic, or still running when the timer
fires - which holds under both root and unprivileged execution. T6b, the check
on the painted frame's escape sequences, is skipped with a printed `SKIP` line
when no terminfo database is reachable rather than being reported as a pass.

Both paths were exercised locally: as root (8 assertions, T6b skipped) and as an
unprivileged uid with the terminfo database reachable (9 assertions, T6b
passing). The CI worker runs the suite the same way `conan create` runs it, so
whichever branch it takes is a real execution of the packaged binary.

### A runenv trap worth recording

An earlier revision of this recipe exported `TERMINFO`/`TERMINFO_DIRS` pointing
at `share/terminfo` **inside the tmatrix package** - a directory the build never
creates. Because `runenv_info` is last-writer-wins across the graph, that
silently shadowed the correct value coming from `ncurses/6.6`, leaving any
consumer unable to resolve a terminal type.

The fix is not to simply re-point it at the ncurses package: when a consumer
resolves `tmatrix/1.4` from the cache, the dependency's `package_folder` is
`None` and its `includedirs` are relative, so no correct absolute path can be
recomputed in `package_info()`. The override is therefore dropped entirely, and
`package_info()` documents why. Verified both ways:

```
# consumer requiring only tmatrix/1.4  -> no TERMINFO exported (correct, not broken)
$ conan install --requires=tmatrix/1.4 ...
export PATH=".../tmatrix/bin:$PATH"

# consumer that also requires ncurses/6.6 -> correct path, and it resolves
$ conan install --requires=tmatrix/1.4 --requires=ncurses/6.6 ...
export TERMINFO=".../ncurses-6.6/p/share/terminfo"   # contains x/xterm
```

### Cross execution

An OHOS aarch64 ELF cannot run on an x86_64 build host unaided, so
`test_package/conanfile.py` passes a runner prefix (`qemu-aarch64 -L <sysroot>`)
when the host is not aarch64. On the native OHOS worker no prefix is used and
the binary is executed directly.

## Local CI gate run

```
$ CI_PACKAGES="archives/t/tmatrix/1.4" CONAN_PROFILE=ohos-aarch64-wsl \
      zsh ci/conan/build_and_test.sh
```

`CONAN_PROFILE` is set because the checked-in `ohos-aarch64` profile points at
`/data/service/hnp/bin/clang++`, which exists only on the OHOS CI worker; this
x86_64 WSL host cross-builds with the local toolchain shim. Every other gate is
the repository default.

| Stage | Result |
|-------|--------|
| G0 (knowledge graph integrity) | pass, 541 entries |
| G0e (root whitelist) | pass |
| L0 (quality gate: L0i deps, L0j version, L0k commands.json, L0m structure) | pass |
| KC (knowledge check KC1-KC5) | pass, 0 errors |
| JC (junk check: JC1-JC6) | pass |
| L1 (conan create + test_package executed) | pass |
| L1e (destructive negative test) | pass - moving bin/ away makes the test fail, proving it really depends on the package |
| L2 (smoke test) | pass, `tmatrix --version` OK |
| L4 (patch safety scan) | pass |
| L5 (artifact baseline) | pass, bin/ has content |

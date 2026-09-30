# ntldd 0.2 adaptation notes

## W0 dependency audit

- Upstream: `https://github.com/LRN/ntldd`, tag `0.2` (official archive, 7 files).
- Source archive: `https://ghfast.top/https://github.com/LRN/ntldd/archive/refs/tags/0.2.tar.gz`
  (mirror prefix; CI workers cannot reach github.com — build #64322 failed with
  a source download timeout. Same pattern as existing recipes, e.g.
  syntax-highlighting. The mirror serves byte-identical content: the SHA256
  below was verified against both the official archive and the mirror.)
- Source archive SHA256:
  `3c63d83333413be19dcf0823dc17bd3f014447a43b8d48212829c4cc5fbf74ce`.
- License: GPL-3.0-or-later (`gpl-3.0.txt` shipped in the archive).
- Runtime dependencies: none (the parsed format, PE, is read from files).
- Build dependencies upstream: MinGW gcc + win32api + imagehlp. After the
  portability patch: a C99 compiler only — no external libraries.
- Conan dependencies: none.
- Registry check: `conan list "*ntldd*" -r=ohpcd` found no existing recipe,
  so the Conan version stays `0.2`, identical to upstream.
- Issue number: not confirmed in this session — to be linked before the PR
  (one library, one issue, one branch, one PR).

## W1 source and build analysis

- Project type: pure C, two translation units (`libntldd.c`, `ntldd.c`) plus
  `libntldd.h`; upstream builds via `makeldd.sh`/`makeldd.cmd` with MinGW.
- Function: parses PE import/export/delay-import directories and prints an
  ldd-style dependency tree. All parsing is plain file processing — no
  Windows runtime is needed for the file-based code paths.
- Windows-only touchpoints found (all handled by the patch):
  - `windows.h`/`winnt.h` PE structure definitions.
  - imagehlp `MapAndLoad`/`UnMapAndLoad`/`LOADED_IMAGE`.
  - `GetModuleHandleExA`/`GetModuleFileNameA`/`GetLastError` — only used by
    `on_self` mode, which the `ntldd` CLI never enables.
  - MinGW `stricmp`/`strnicmp`.
- Upstream tests: none. Upstream ships no test suite or `make check`; the
  recipe runs `./ntldd --version` in `build()` when not cross-building, and
  the consumer test exercises real behavior (see W3).

## W2 recipe decisions

- No `conandata.yml`: source URL/SHA256 live in `conanfile.py` and the patch
  is exported via `export_sources()`. This deliberately avoids the CI
  conandata pre-download path that references an uninitialized `BUILD_DIR`
  (known infrastructure defect, see common-issues guide §5.2).
- The tarball root is `ntldd-0.2/`, so `get(..., strip_root=True)` is correct
  (verified by extraction).
- Build is a single compiler invocation (3 files) — no configure, no make,
  so none of the autotools/`config.guess`/shebang pitfalls apply.
- `-Wno-format` keeps upstream printf-style mismatches warnings-only; the
  remaining `-Wempty-body`/`-Wint-to-void-pointer-cast` warnings are
  upstream code style in the delayload path and are left untouched.
- Windows hosts keep the original code path: the patch is guarded by
  `#ifdef _WIN32` everywhere except the `#include` swap, which is itself
  conditioned inside `pe_compat.h`.

## Patch description

`patches/0001-ohos-pe-compat-port.patch`:

- Adds `pe_compat.h`/`pe_compat.c` — a self-contained PE compatibility layer
  (types, PE structures from the public PE format specification, and a
  `MapAndLoad`/`UnMapAndLoad` replacement that reads the whole file into
  memory and locates DOS/NT headers and the section table, with imagehlp's
  `.dll`-suffix fallback behavior).
- `libntldd.h`/`libntldd.c`/`ntldd.c`: include `pe_compat.h` instead of
  `windows.h`/`Imagehlp.h`/`winnt.h`; `stricmp`/`strnicmp` map to
  `strcasecmp`/`strncasecase`; the Windows-only `on_self` branch is guarded
  by `#ifdef _WIN32` and returns an error off-Windows.

## W3 test_package

- `gen_pe.py` builds a tiny but fully valid PE32 executable with two import
  dependencies (`KERNEL32.dll` → `Foo`, `advapi32.dll` → `Bar`). Verified on
  the Windows host: `llvm-objdump -p tiny.exe` shows both DLL names and
  imported symbols, matching the generator's intent.
- `test_ntldd.sh` asserts 6 checks: `--version` output `ntldd 0.2`,
  `--help` usage text, `KERNEL32.dll` in the dependency listing,
  `advapi32.dll` in the listing, `not found` reporting for unresolvable
  DLLs, and `-i` listing the imported symbol `Foo`. Without `python3` the
  last 4 checks degrade to a documented skip and the first 2 still run.

## W4 local verification (Windows host)

- Source archive download + SHA256: passed.
- OHOS SDK cross-compile with
  `clang --target=aarch64-linux-ohos --sysroot=<sdk>`: exit 0;
  `llvm-readelf -h`: `ELF64 / DYN / Machine: AArch64`.
- Patch applies cleanly to the pristine upstream archive
  (`git apply --check` passed).
- Host execution of the tool itself was not possible on this Windows host
  (no MSVC/MinGW native target and no Linux container running); functional
  verification is delegated to the device shadow CI. Nothing untested is
  reported as passed.
- Python syntax check for recipe + test_package: passed (py_compile).
- YAML parse check for manifest/MANIFEST: passed.
- Test PE generation: passed, structure confirmed by `llvm-objdump`.

## Shadow CI handover (next step)

```sh
conan create archives/n/ntldd/0.2 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```

Then, as an isolated single job on the device:

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job <job-name> \
  --package archives/n/ntldd/0.2 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

Record L0/L1/L2/L4/L5, the `--version` self-check, and the 6 test_package
assertions. The tool parses files only; no PE execution happens, so no
extra device permissions are expected beyond normal ELF signing.

## Shadow CI iteration log (device `<device>:<port>`)

| round | job / run | wait | exit | gate result | root cause | fix |
|---|---|---|---|---|---|---|
| r1 | ntldd-0.2-20260929 / ...-101613-15141 | 5s | 127 | runner layer, no L gates | repo copied from an older job whose repo snapshot lacks `ci/` entirely (`zsh: can't open input file`) | recreate job with a repo-source that contains `ci/` (esekeyd job verified complete) |
| r2 | ntldd-0.2-20260929-r2 / ...-102012-18692 | 11s | 1 | `L0_RESULT=fail: commands_json_r38` | CLI tool packages must ship a software-level `archives/n/ntldd/commands.json`; nettoe-era "warn" behavior is now a hard gate | added `archives/n/ntldd/commands.json` (name/type=tool/0.2/binary=true/commands=[ntldd]) |
| r3a | ntldd-0.2-20260929-r3 / ...-102323-21970 | 157s | 1 | `L0_RESULT=fail: knowledge_check failed` (`permission denied: bash`) | `ci/conan/build_and_test.sh` KC step invokes bare `bash`; `/usr/bin/bash` access intermittently denied on the device (a sibling job passed KC minutes earlier with identical env) | prepend `/data/service/hnp/bin` to PATH in the job's `env.sh` so `bash` resolves to the runnable hnp copy; job-local file only, no shared-script changes |
| r3b | ...-102851-29743 | 217s | 1 | `L1_RESULT=fail: conan create failed` | `self.conf.get("tools.build:compiler_executables:c", ..., check_type=str)` raised `ConanException: does not exist in configuration list` on the OHOS-adapted Conan 2.29.1 | drop `check_type` |
| r3c | ...-103615-40948 | 66s | 1 | same exception without `check_type` | this Conan build also rejects direct sub-key conf access even without check_type | read the whole `tools.build:compiler_executables` dict and take `["c"]` |
| r3d | ...-103931-45230 | 1s | **0** | **L0/L1/L2/L4/L5 all pass, pass rate 100%** | — | — |

Final shadow CI result (run ...-103931-45230, exit code 0):

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: ntldd --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
L1e: Negative test confirmed — test genuinely depends on ntldd
test_package: 6/6 assertions passed
  (--version "ntldd 0.2", --help usage, KERNEL32.dll listing,
   advapi32.dll listing, "not found" reporting, -i symbol Foo)
```

Also fixed during device runs (both caught before/while queueing):

- `test_ntldd.sh` now creates its temp dir under `${TMPDIR:-$HOME}`
  because OHOS `/tmp` is read-only (E002).

Notes: every runner was launched with `--lock` queueing; `wait_seconds`
recorded from `logs/lock.txt`. L0 checks that passed: version collision
(first publish), commands.json (after r2 fix), directory structure.
Local host-compile cross-verification (OHOS SDK clang, AArch64 ELF) had
already passed on the Windows host before the device run.

## Status

- W0/W1/W2/W3: complete.
- W4: complete (host cross-compile verification; device-independent checks).
- W5: complete — OHOS armv8 shadow CI passed (L0/L1/L2/L4/L5 all pass,
  L1e negative test confirmed, test_package 6/6 assertions).
- W6: pending — attach issue number, push branch, open PR.
- Issue number: pending — must be attached before opening the PR.

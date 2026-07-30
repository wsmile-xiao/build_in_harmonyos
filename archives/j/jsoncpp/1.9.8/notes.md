# JsonCpp 1.9.8 OpenHarmony PC adaptation notes

## Scope

JsonCpp 1.9.8 is a mandatory dependency of Redex. It has no third-party
dependencies of its own. This dependency adaptation is tracked only by
Issue #1268.

## Source

- URL: https://github.com/open-source-parsers/jsoncpp/archive/refs/tags/1.9.8.tar.gz
- SHA-256: `51828cf3574281d2b79ec2a1c56a9e4c20cc1103711321ea96384cffb8d2d904`
- Build system: CMake
- Offline validation: set `JSONCPP_SOURCE_ARCHIVE` to the same official tarball;
  the recipe verifies its SHA-256 before extraction

## Package design

The upstream defaults build shared, static, and object variants together.
The Conan recipe instead maps `shared=True` to only `libjsoncpp.so` and
`shared=False` to only `libjsoncpp.a`; `BUILD_OBJECT_LIBS` is always disabled.

For HarmonyOS, the recipe supplies CMake's missing SONAME and build-RPATH
linker variables. The source patch suppresses `VERSION` and `SOVERSION` only
when `CMAKE_SYSTEM_NAME` is `HarmonyOS`, avoiding HMDFS symlinks while keeping
a basename SONAME. Linux retains upstream versioned-library behavior.

HarmonyOS Python 3.12 raises `TypeError: can't concat str to bytes` while
the upstream `runjsontests.py` reads an `os.popen` text stream. The second
patch keeps the same commands and failure semantics, but captures bytes with
`subprocess.PIPE` and performs an explicit UTF-8 decode. No test is skipped.

## Test inventory

Logical cases are counted once; shared/static reruns, CTest wrappers, three
writer modes, and assertions are not additional cases.

| Category | Cases | Evidence |
|---|---:|---|
| Unit | 127 | Registered and executed fixtures from `src/test_lib_json/main.cpp` |
| Integration | 69 | Distinct `test/data/*.json` parser/writer inputs |
| Integration | 27 | Runnable JSONChecker inputs after 9 upstream exclusions |
| Consumer unit | 1 | `test_package/unit.cpp` |
| Consumer integration | 1 | `test_package/integration.cpp` |
| HarmonyOS-specific | 1 | `test_package/ohos_portability.cpp` |

The `_WIN32`-guarded `StreamWriterTest/escapeTabCharacterWindows` fixture is
not registered on HarmonyOS and is excluded from the count.

Upstream total: 223. New consumer flows: 3.

## Native HarmonyOS validation

Environment: HarmonyOS aarch64, Conan 2.29.1, CMake 4.1.2, Clang 15.0.4,
Python 3.12.9. The device profile was completed per invocation with
`os.version=6.0`, `compiler.libcxx=libc++`, and absolute HNP clang paths;
the global profile was not modified.

After W4 detected a fuzzy import hunk, both source patches were regenerated
from the verified official archive with `refresh-patch --auto`. `git apply
--check` and GNU `patch --dry-run --fuzz=0 -p1` then passed for the full patch
set. Both package modes were rebuilt from scratch in an isolated Conan cache
using this exact recipe revision:

`724ba812213a9ba6c84a8734aa55a441`

| Mode | Package ID | Package revision | Result |
|---|---|---|---|
| shared | `01d92cf349a0dd98ff915f4bd99a04430171517f` | `0da8629434f50ec9e901c5d1c7ad9e5e` | upstream `223/223`, consumers `3/3` |
| static | `21b17f8b2bc0e9511e276e3d57a23893067cefe5` | `92ed8a8eccd474501b74ce5798e9191f` | upstream `223/223`, consumers `3/3` |

The package IDs are profile-dependent. The r5 input therefore binds the exact
HarmonyOS profile and target-side Conan graph evidence before comparing each
fresh build's full package reference. Historical IDs from another isolated
cache are not reused as cross-device constants.

The final shared package contains one signed AArch64 `libjsoncpp.so`, no
symlinks, SONAME `libjsoncpp.so`, no RPATH/RUNPATH, and no path-bearing
`DT_NEEDED` entry. SHA-256:
`18b444b328aaa94fe4dd76f5fc4c5848f7915fc50164a647d06d63cfa08aa579`.

The final static package contains one `libjsoncpp.a`, no `.so` and no
symlinks. Its signed static consumer has no `libjsoncpp.so` dependency.
Archive SHA-256:
`1e927539b8a488f08f5b8eb44e703f77b0f39af55d3a0ad2ecac05160a7d92c9`.

## Evidence

- Run ID: `jsoncpp-3004-r5-20260724T081900Z-49196`
- Candidate HEAD: `beaff8f9e65af9f3ead8a320bc69e331ad3e05a2`
- Candidate tree: `78fb93cf0daf4be1cdb46fd79d85b1e585a4ec71`
- Input bundle SHA-256:
  `e1da9dfe50efd5f4acd80677135c50ac91c330de3e51c4943e6e4d4e70139642`
- Returned result bundle SHA-256:
  `ddeedf133abc0e4f1a25465758d5ff46b61d1eda2aea9707954c109cb08cf42c`
- Evidence manifest SHA-256:
  `f4c9de6e2f814521cfe8e1498ee6303f07aba46dc54a3ecaad163a75f7f38b17`
- Terminal totals: upstream `223/223`, consumers `3/3`, artifact checks
  `15/15`; FAIL `0`, ERROR `0`, TIMEOUT `0`, unknown `0`.

The verbose log independently resolves to 127 unit fixtures, 69 data inputs,
and 27 additional JSONChecker inputs. It also records the three official
CTest entries passing. Shared/static reruns and writer modes are not recounted.
The independent validator replays the exact evidence manifest, terminal rows,
process records, package references, and artifact assertions.

# LibXC 7.1.2 Test Report

## Scope

- Official `libxc-7.1.2.tar.bz2` source, SHA-256
  `3915FAC94416E4C415534223EA492AD2663F928ACF27E98662C861B094A6C306`.
- Candidate `0001-CMakeLists.txt.patch`, SHA-256
  `12CCEA6F8B049F95283C94D87049828F2712C0FCB3A47236D309DE1F78A0C9E1`.
- Native Windows shared host build, one build job.
- HarmonyOS PC aarch64 shared upstream build and complete official test suite,
  one Ninja build job and serial pytest execution.
- HarmonyOS PC aarch64 target `conan create`, two substantive consumers, and
  static-archive inspection, one build job and no WSL.
- No commit, push, or CI was performed during these validation runs.

## Host Results

| Surface | Total | PASS | SKIP | XFAIL | Unexpected terminals |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native CTest | 3 | 3 | 0 | 0 | 0 |
| pytest | 14084 | 13987 | 79 | 18 | 0 |
| Combined | 14087 | 13990 | 79 | 18 | 0 |

CTest registered 23 entries: 20 `python-*` wrappers plus three native entries.
The native-only command was:

```text
ctest -E '^python-' --output-on-failure -j1
```

The full pytest command was:

```text
python -m pytest -q -o addopts= testsuite
```

Pytest completed in 175.73 seconds. The terminal arithmetic closes exactly:
`13987 + 79 + 18 = 14084`.

## Host Diagnostic Attempt Excluded From Acceptance

The first direct pytest collection returned RC 2 with 1,414 import errors
because Windows `ctypes.util.find_library("xc")` did not resolve the built
`libxc.dll`. This loader-layout failure is not counted as a source test result.
The DLL was copied only inside the isolated validation tree to
`src/pylibxc/libxc.dll`; both copies had SHA-256
`2E40933737B35CDB1F3F63598AE7936379DD4772FED25510D0D6CAE366258DF8`.
The corrected collection and full execution then returned RC 0.

## Evidence

| Evidence | SHA-256 |
| --- | --- |
| Corrected pytest collection stdout | `4EA64DBFF482CC55B48BC14701D2B898875F8C004EEB5E608F8CD191912FA615` |
| Full pytest stdout | `BADEDAD9947E445F3CA10B67B66AD6CCCD8B89A750420E7EA4EF48AAED4F3563` |
| Native CTest stdout | `F7341E49B4807CDEDB42C087A7F936F662A4DF7F19229A395170A0C4C7C1EB73` |
| Full validation record | `FE97829112F4630939D81C36FDDB1A19CF875EF2D79E6F9D0E9481168D5BFDBD` |

The complete host evidence directory is
`E:/HarmonyPC/validation/libxc-7.1.2-host-upstream-20260731`.

## HarmonyOS PC Target Upstream Results

The accepted r10 run was bound to PR candidate commit
`09d4883981167bca6fc35e3f8a228a3c26e44eb3`, the official source and patch
hashes above, and a 15-file frozen input closure. It used one Ninja build job,
an isolated offline Python dependency directory, serial pytest execution, and
separate explicit pytest base directories for collection and execution.

| Surface | Total | PASS | SKIP | XFAIL | Unexpected terminals |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native CTest | 3 | 3 | 0 | 0 | 0 |
| pytest | 14084 | 13987 | 79 | 18 | 0 |
| Combined | 14087 | 13990 | 79 | 18 | 0 |

The target shared build completed all 349 Ninja edges. Pytest collection and
execution contained the same 14,084 unique nodeids, every nodeid had exactly
one terminal, and the full run completed in 972.49 seconds. The copied
`pylibxc/libxc.so` was the one real built shared object and inspected as an
ELF64 AArch64 `DYN` file.

Two earlier diagnostics are excluded from acceptance. Without the optional
test dependencies SymPy and mpmath, pytest returned zero but silently collected
only 13,966 nodeids. After restoring the complete dependency closure, the r7
run collected 14,084 but its only error was pytest's default temporary-root
ownership check: the process UID was `20020107`, while HMDFS exposed the new
`pytest-of-currentUser` directory as UID `20001006`. Replaying the exact test
with an isolated explicit `--basetemp` passed. The accepted r10 run used
distinct explicit base directories for collection and execution and closed the
complete inventory.

| Target upstream evidence | SHA-256 |
| --- | --- |
| Frozen `input.sha256` | `8ED121E8E54EB6D0A49900AF3FABAA65C38BF9DD6390DB29DA52D5C62EE22A5A` |
| Frozen runner | `8966C3BAD88B949297CAF57A9FEB46EEA1BD958261F8FDBD5C2F3DE627AFB91F` |
| Frozen manifest | `809E7B3927525B7CCB47EF8C0C117B8548166EEB9CA48CC7E51DEA576CC0E2AC` |
| Evidence checksum manifest | `244CB25BFE644769E0F19191F4EF46A6A0D0933C6F2423A3329F2BD402D09811` |
| Downloaded result tar | `18EDFFB1D980F33DC802F88CA9EF9ECFD6139EB365C980C2001A53C62C4D95ED` |

The result contains 35 sorted, hash-bound evidence files. The independent
validator passed after download at
`E:/HarmonyPC/validation/libxc-7.1.2-target-upstream-r10-20260801/downloaded/result`.

## HarmonyOS PC Target Results

The final r5 run used candidate index tree
`d47baa00c4def998fb5d88e438a62df4a7b923c1` and one build job. Candidate input
validation reported `CR=0` and exact file-list agreement. `conan create`
returned zero and produced:

```text
libxc/7.1.2#388674bd8ae779d9c327a304f5182081:67b1ef552f88cbbdfea884e9d0a9077b41cdad94#9d58b49573531ab0d22e03149e2f2d6e
```

| Target surface | Total | PASS | Unexpected terminals |
| --- | ---: | ---: | ---: |
| C package consumer | 1 | 1 | 0 |
| LLVMFlang Fortran KXC consumer | 1 | 1 | 0 |
| Combined consumers | 2 | 2 | 0 |

The package contains static `libxc.a`, static `libxcf03.a`, two LLVMFlang
module files, and the fail-closed Fortran ABI CMake module under the actual
`lib/cmake/Libxc` directory. Inspection found 328 ELF64 little-endian AArch64
objects in `libxc.a` and one in `libxcf03.a`. The independent download
validator passed all 39 hash-bound evidence files.

The downloaded evidence is stored at
`E:/HarmonyPC/validation/libxc-7.1.2-target-r5-20260731/downloaded/result`.
The candidate archive SHA-256 is
`A32061DA4CEA263897D81D112B09B97154BA406B8AE611F115E60EB75F57052D`.

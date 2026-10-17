# DRAFT - A test binary compiled from part of the upstream test target exits green with zero cases

> Status: DRAFT | Source: semver 1.0.1 PR #7318, fix commit `d94eff60c5`; re-measured on HarmonyOS PC aarch64 (clang 15.0.4) on 2026-09-01

## Failure shape

doctest and Catch2 register only the translation units that are actually linked
into the binary. The file that carries the framework entry point compiles and
links completely on its own — and running it is a no-op that exits 0:

```text
$ clang++ -std=c++17 -O1 -Iinclude -Itest/3rdparty/doctest test/test.cpp -o only_main
$ ./only_main; echo "exit=$?"
[doctest] doctest version is "2.5.3"
===============================================================================
[doctest] test cases: 0 | 0 passed | 0 failed | 0 skipped
[doctest] assertions: 0 | 0 passed | 0 failed |
[doctest] Status: SUCCESS!
exit=0
```

`Status: SUCCESS!` plus exit code 0 satisfies every layer that only inspects the
exit status: the recipe's `self.run`, W3, CI and the archive. Nothing in the
toolchain distinguishes "all cases passed" from "no cases exist". This is the
silent variant of a false green; the loud variant (a missing symbol, a failed
ctest) is not the problem being described here.

In semver 1.0.1, `test/test.cpp` is exactly that file: it holds
`#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN` and **zero** `TEST_CASE` blocks.
All 98 cases live in eight sibling files. The original recipe compiled
`test.cpp` alone, so the archived "upstream tests pass" evidence was an empty run.

## Second, independent finding: the summary line is not an upper bound

Building the complete target is necessary but not sufficient for reconciling
counts. On the same tree:

| measurement | value |
|---|---|
| `grep -cE '^[[:space:]]*TEST_CASE\('` over `test/*.cpp` | **98** |
| runtime summary, `-std=c++17` | **89** cases / 52851 assertions |
| runtime summary, `-std=c++20` | **90** cases / 52872 assertions |
| `--list-test-cases`, `-std=c++17` | 89 names |

The nine cases that never register are behind feature guards, not standard-level
switches. Diffing the static names against `--list-test-cases` identifies them:

| guarded name | file | guard |
|---|---|---|
| `constexpr parse and accessors` … (6 cases) | `test_validation.cpp` | `#if SEMVER_HAS_CONSTEXPR` |
| `consteval _semver literal` | `test_validation.cpp` | `#if SEMVER_HAS_CONSTEVAL_LITERAL` |
| `operator<=>` | `test_operators.cpp` | `__cpp_impl_three_way_comparison >= 201907L` |
| `std::formatter` | `test_to_string.cpp` | `__cpp_lib_format >= 201907L` |

Raising the language standard is **not** an effective remedy: on clang 15
`-std=c++20` recovered exactly one of the nine. Treat the static scan and the
runtime summary as two independent measurements, name the guard macros
responsible for the delta, and never let the runtime line overwrite the declared
total.

## Diagnosis boundary

- This is not E229 (an isolated test that failed to link the library's own
  fallback object). Here the *library* is exercised correctly; the defect is
  which test translation units reached the linker.
- This is not E231 (evidence not bound to a checksummed archive). The source was
  pinned and correct; the compiled subset was not.
- This is not a compiler-support complaint about OHOS. The empty run reproduces
  identically on any host, which is what makes it a recipe-authoring rule rather
  than a platform finding.
- The three-line `验证结果` reporting format used by contest PR review is a
  *reporting* convention. It is not knowledge-graph content and is deliberately
  not encoded here; only the reproducible engineering facts are.

## Recommended repair

Take the file list from the upstream test target instead of inventing one, and
state exclusions explicitly when a sibling target does not apply:

```python
# Upstream main test target (test/CMakeLists.txt SOURCES): test.cpp provides
# the doctest main; the 8 suite files carry the 98 TEST_CASEs.
# test_config.cpp needs a SEMVER_CONFIG_FILE override (separate target) and
# test_windows_minmax.cpp is MSVC-frontend-only: both excluded.
suite = ["test.cpp", "test_operators.cpp", "test_parse.cpp", "test_ranges.cpp",
         "test_to_string.cpp", "test_validation.cpp", "test_api.cpp",
         "test_advanced_ranges.cpp", "test_edge_cases.cpp"]
```

Then gate on the parsed summary, not on the exit code:

```bash
./semver_tests | grep -qE 'test cases: [1-9][0-9]* \|' || exit 1
```

A one-line equivalent for auditing an existing recipe: if the compile command
names a single `.cpp` and the upstream target lists several, the run is suspect
until the summary proves a non-zero case count.

## Related knowledge, not new entries

- **E294** 恢复被构建选项（`BUILD_SHARED_LIBS`）丢弃的完整上游测试，本条恢复的是被不完整
  文件列表丢弃的上游测试：两者都要求"跑满上游 target"，但失效点在 recipe 侧而非构建系统侧。
- **E239** 关注多用例 `test_package` 运行中的诊断信息保全；本条关注的是根本没有用例被执行。
- **E231** 要求测试清单绑定到已校验的压缩包来源；本条即使清单来源正确，编译集合仍可能少于 target。
- **E229** 是独立测试未链接库内 fallback 对象——被测库没被真正行使；本条相反，被测库行使正常，
  少的是测试 translation unit。两条在检视时容易互认，故列在 `similar_to`。

## Prohibited variants

- Do not submit `test.cpp` alone (or any single TU) as "the upstream suite".
- Do not accept `Status: SUCCESS!` / exit 0 as evidence of coverage.
- Do not declare the runtime summary as the upstream total when the source scan
  is higher; declare the scan count and report the measured number separately.
- Do not "fix" the gap by forcing `-std=c++20` — measured to recover 1 of 9 here.
- Do not delete the guard explanation from `notes.md`; the delta is the part a
  later reviewer cannot reconstruct from the log.

## Reproduction

```bash
curl -sSL -o semver.tgz https://github.com/Neargye/semver/archive/refs/tags/v1.0.1.tar.gz
tar xzf semver.tgz && cd semver-1.0.1
clang++ -std=c++17 -O1 -Iinclude -Itest/3rdparty/doctest test/test.cpp -o only_main && ./only_main   # 0 | 0 passed, exit 0
clang++ -std=c++17 -O1 -DDOCTEST_CONFIG_USE_STD_HEADERS -Iinclude -Itest/3rdparty/doctest \
  test/test.cpp test/test_operators.cpp test/test_parse.cpp test/test_ranges.cpp \
  test/test_to_string.cpp test/test_validation.cpp test/test_api.cpp \
  test/test_advanced_ranges.cpp test/test_edge_cases.cpp -o full && ./full | tail -3                   # 89 | 52851
```

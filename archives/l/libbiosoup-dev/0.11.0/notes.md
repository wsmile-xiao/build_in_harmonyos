# libbiosoup-dev 0.11.0 适配笔记

## 编译环境
- 构建系统: header-only（无编译产物）+ 上游测试用 GoogleTest 直接编译
- 编译日期: 2026-09-15
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 任务版本 `0.11.0` 对应上游 tag `0.11.0`。
- 源码：`https://codeload.github.com/rvaser/biosoup/tar.gz/refs/tags/0.11.0`
  sha256 `e4addc3965ca9291535a131c07ef958a98e779ef1375d38d354536df66e16cd4`。

## 打包步骤

header-only，仅复制头文件：

```
include/biosoup/{nucleic_acid.hpp,overlap.hpp,progress_bar.hpp,sequence.hpp,timer.hpp}
licenses/LICENSE
```

`package_info` 暴露 CMake 目标 `biosoup::biosoup`。

## 上游测试（GoogleTest）真的跑了

上游 `test/` 有 5 个测试文件、共 **11 个 `TEST` 用例**（取数 `grep -rhoE '^TEST\([^)]*\)' test/*.cpp | wc -l` → 11）：
`nucleic_acid_test.cpp`(4)、`overlap_test.cpp`(1)、`progress_bar_test.cpp`(1)、
`sequence_test.cpp`(1)、`timer_test.cpp`(4)。

`build()` 里用 `test_requires("gtest/1.17.0")` 提供的 GoogleTest 头/库，**未修改上游源码**直接编译并运行：

```sh
clang++ -std=c++17 -O2 -pthread \
  -I <gtest include> -I <repo>/include \
  test/nucleic_acid_test.cpp test/overlap_test.cpp test/progress_bar_test.cpp \
  test/sequence_test.cpp test/timer_test.cpp \
  -L <gtest lib> -lgtest -lgtest_main -o biosoup_test
./biosoup_test
```

实测结果：

```
[  PASSED  ] 11 tests.
```

> 注：`gtest/1.17.0` 是 ohpcd 远端已有的预编译包（OHOS armv8 / clang 15 / libc++ / Release），
> 与本 profile 的 package_id 一致，`conan create` 只下载不重编。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试此前未运行 | 上游用 meson subproject（`gtest.wrap`）引入 GoogleTest | 改为 `test_requires("gtest/1.17.0")`（远端有预编译二进制）并在 `build()` 里直接编译执行上游 5 个测试文件 |
| 2 | 静态成员 `num_objects` | `NucleicAcid`/`Sequence` 声明了 `static std::atomic<uint32_t> num_objects` | 上游测试文件已各自定义一次；消费者使用需自行定义（见注意事项） |

## 源码修改

无补丁（`patches/` 为空）——上游 `test/*.cpp` 未改动。

## 依赖版本

- 构建/测试依赖：`gtest/1.17.0`（`test_requires`，仅用于跑上游测试，不传播给消费者）
- 运行依赖：无

## 验证结果

```bash
conan create archives/l/libbiosoup-dev/0.11.0 \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=$HOME/.conan2/profiles/ohos-aarch64
# 上游 GoogleTest：11 用例 / 11 通过（[  PASSED  ] 11 tests.）
# test_package：14/14 通过
```

## 注意事项

- 头文件引用为 `<biosoup/xxx.hpp>`；使用 `Sequence`/`NucleicAcid` 需自行定义 `num_objects`。
- 不要再用"gtest 不可用"作为不跑上游测试的理由：ohpcd 已有 `gtest/1.17.0` 预编译包。

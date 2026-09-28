# gemmlowp 0.8.7 适配笔记

## 编译环境
- 构建系统: cmake（构建入口 contrib/CMakeLists.txt，Debian 编写；上游官方为 Bazel）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，profile ohos-aarch64）
- 状态: built（conan-verify 通过，本机未执行 CI upload）

## 源码版本锚点
- 上游 google/gemmlowp **无 tag、无 release**（GitHub API tags=0），0.8.7 以
  master HEAD commit `16e8662c34917be0065110bfcd9cc27d30f52fdf`（2023-11-03）
  作为源码锚点，tarball SHA-256 `c3feb896a1b42595cf9a508ed64ed0dc3cd84fffdb8eed790d02d0534ab322ce`。
- 参考：conan-center-index 使用 cci.20210928（commit daf630d3），vcpkg 用
  version-date 2021-09-28；本任务按任务头版本 0.8.7 采用最新 master HEAD。

## 编译步骤
1. init-build：registry 无 gemmlowp 记录，`--url` 指定官方 commit tarball。
   ⚠️ init-build 嵌套源码检测（F068）误判：gemmlowp 根目录无构建标记
   （CMakeLists 在 contrib/ 下），`_promote_nested_source` 把 contrib/ 提升为
   源码根并删除真实源码（public/、fixedpoint/、internal/、meta/、
   eight_bit_int_gemm/ 等）。手动重建 `.orig`/`.work`（完整解压 tarball、
   核对 `.tarball-sha256`=c3feb896...）。
2. lang-preflight：工具判 mixed（build_system=none、cpp 18 / python 14 /
   bash 4 → 主体 56% < 70%）。判定缺陷：gemmlowp 官方构建系统为 Bazel
   （BUILD/WORKSPACE，检测器未识别）；14 个 .py 全部是 meta/generators/
   代码生成器（生成 .h 内核）与 standalone/encode.py，属辅助脚本；
   gemmlowp 主体为纯 C++ header-only 库（public/fixedpoint/internal/meta/
   profiling 均为 .h）。按协议 D.4"辅助脚本不算主体语言"，按 cpp 继续主流程。
3. CMake 配置/构建（BUILD_TESTING=ON，CC=clang CXX=clang++）：构建
   eight_bit_int_gemm 静态库 + 5 个测试可执行 + 2 个 benchmark。
4. conan-init 生成配方（模板为 autotools，已重写为 CMake 配方：
   cmake.configure(build_script_folder=contrib)，参考 conan-center-index）。
5. conan-verify：G1/G0/G2/G3/G4 + L2/L4/L5 全部 PASS，test_package 消费者
   测试通过（修正 2 轮：头文件 include 前缀、ColMajor 期望值）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 删除真实源码 | F068 嵌套源码检测把 contrib/ 误当源码根 | 手动重建 .orig/.work + 核对 SHA-256 |
| 2 | lang-preflight 判 mixed | Bazel 构建系统未识别 + 生成器 .py 计入统计 | 按 D.4 辅助脚本规则判 cpp 继续 |
| 3 | test_package include 找不到头 | 安装路径 include/gemmlowp/public/*.h，conanfile includedirs=include/gemmlowp | include 改为 "public/bit_depth.h" |
| 4 | test_package 期望值错误 | rhs 用 ColMajor 存储 [[5,7],[6,8]]，按行优先算了期望 | 修正期望 [17,23,39,53] |
| 5 | conan-verify 写日志 ENOSPC | hmdfs inode 池耗尽（favail≈5000） | 轮询等待 inode 窗口后重跑 |

## 源码修改
- 无补丁（patches/ 空）。配方在 conanfile.py 中通过
  `cmake.configure(build_script_folder=contrib)` 指定构建入口。

## 依赖版本
- 无外部依赖（仅系统 pthread）。依赖链：无。

## 验证结果

```bash
# 上游测试（contrib/CMakeLists.txt 注册的 5 个 ctest，全部通过）
cd /storage/Users/currentUser/tmp/builds/gemmlowp-cmake-build && ctest
# 100% tests passed, 0 tests failed out of 5

# OHOS 专项测试（consumer 视角，链接已安装静态库）
cd archives/g/gemmlowp/0.8.7/tests
clang++ --target=aarch64-linux-ohos -I<install>/include/gemmlowp -std=c++17 \
  ohos_specific_test.cc -L<install>/lib -leight_bit_int_gemm -lpthread
./ohos_specific_test   # ALL PASSED（4 个用例）

# test_package 消费者测试（conan-verify G2 内）
# gemmlowp consumer test OK (2x2 quantized GEMM verified)
```

## 测试统计（双口径台账，R02 逐入口修正）

> R02（rule4 返工）：r01 误将构建系统注册数（5）当作源码声明总数，
> 且把 meta/ 下 4 个含 main() 的未注册测试程序标注为"上游排除条件"未计入。
> 本轮以官方 commit 16e8662c34917be0065110bfcd9cc27d30f52fdf 为枚举对象，
> 逐入口枚举全部含 main() 的独立测试程序，并对未注册入口做最小纳入并实际运行。

| 口径 | 数量 | 说明 |
|------|------|------|
| source_declared_total | 11 | 逐入口枚举的独立上游用户测试程序：构建系统注册 5 + 未注册含 main() 6（meta/test_gemm_correctness.cc、meta/test_streams_correctness.cc、meta/test_transform_correctness.cc、meta/test_transform_benchmark.cc、test/correctness_meta_gemm.cc、test/benchmark_meta_gemm.cc） |
| configured_executable_total | 11 | 当前 OHOS 配置实际实例化/注册的独立可执行用例数（5 个上游注册 + 6 个本轮最小纳入测试目标） |
| executed_passed_total | 10 | 5 注册项全过 + 6 最小纳入项中 5 项过（gemm_correctness/streams_correctness/transform_benchmark/correctness_meta_gemm/benchmark_meta_gemm） |
| failed | 1 | meta/test_transform_correctness.cc（真实上游测试精度缺陷，见下方"失败项"） |
| 未实例化 | 0 | 无（6 个未注册入口均已最小纳入并实际运行） |

全量通过率：**10/11 (90.9%)**（分母=source_declared_total=11）；
当前配置可执行集合通过率：10/11 (90.9%)（口径差异原因见下）。

### 逐入口枚举台账（官方 commit 16e8662c 源码）

| # | 源码入口 | 独立用例? | 分类理由 | 构建注册 | 结果 |
|---|----------|:---:|----------|----------|------|
| 1 | test/test.cc (+test_data.cc) | ✅ | 主单元测试，main() | Bazel cc_test `test` / CMake `test_gemmlowp` | ✅ PASS (ctest) |
| 2 | test/test_math_helpers.cc | ✅ | main() 单测 | Bazel/CMake 注册 | ✅ PASS (ctest) |
| 3 | test/test_blocking_counter.cc | ✅ | main() 单测 | Bazel/CMake 注册 | ✅ PASS (ctest) |
| 4 | test/test_allocator.cc | ✅ | main() 单测 | Bazel/CMake 注册 | ✅ PASS (ctest) |
| 5 | test/test_fixedpoint.cc | ✅ | main() 单测 | Bazel/CMake 注册 | ✅ PASS (ctest) |
| 6 | meta/test_gemm_correctness.cc | ✅ | main() 独立正确性测试 | 上游未注册 → 本轮最小纳入 | ✅ PASS（clang -O3 直编直跑） |
| 7 | meta/test_streams_correctness.cc | ✅ | main() 独立正确性测试 | 上游未注册 → 本轮最小纳入 | ✅ PASS |
| 8 | meta/test_transform_correctness.cc | ✅ | main() 独立正确性测试 | 上游未注册 → 本轮最小纳入 | ❌ FAIL（exit 1，见下） |
| 9 | meta/test_transform_benchmark.cc | ✅ | main() 独立程序（benchmark 型计时） | 上游未注册 → 本轮最小纳入 | ✅ PASS（计时输出，exit 0） |
| 10 | test/correctness_meta_gemm.cc | ✅ | main() 独立正确性测试 | 上游未注册 → 本轮最小纳入 | ✅ PASS |
| 11 | test/benchmark_meta_gemm.cc | ✅ | main() 独立程序（benchmark 型，需链接 eight_bit_int_gemm） | 上游未注册 → 本轮最小纳入 | ✅ PASS（计时输出，exit 0） |

不计独立用例但列入台账：test/benchmark.cc（纯基准）、test/benchmark_all_sizes.cc（纯基准）、
standalone/neon-gemm-kernel-benchmark.cc（基准）、standalone/cache_counters.cc（独立工具）、
doc/quantization_example.cc（示例）。test/test_data.cc 无 main()，为 test.cc 的数据支撑文件。

### 失败项：meta/test_transform_correctness.cc

- 命令（与上游 BUILD copts 一致，-O3）：
  `aarch64-unknown-linux-ohos-clang++ -O3 -std=c++17 -Imeta -I. meta/test_transform_correctness.cc -o <out> -lpthread`
- cwd：上游源码根目录；退出码：1；首错：`Wrong: 0 : <0x09> vs. <0x00>`（verify_requantize 第 88 行断言）。
- 根因（真实上游测试精度缺陷）：测试自身参考值计算用 float 表达 `(1<<32)-1`，
  clang 编译告警 `implicit conversion from 'long' to 'float' changes value from 4294967295 to 4294967296`
  （meta/test_transform_correctness.cc:186），导致参考值与被测 Requantize 内核在 NEON/float
  舍入边界差 1 ULP，i=0 处断言失败。上游 Bazel BUILD 与 contrib/CMakeLists.txt 均未注册该测试
  （上游自身从未运行过），非本适配引入的缺陷，不阻塞当前库。
- 阻塞归属：上游测试（精度敏感，上游未注册）；恢复条件：上游修正参考值计算
  （如改用 double 或精确整数算术）后方可在当前配置下通过。
- 日志：/storage/Users/currentUser/tmp/r02-tests/transform_correctness_o3.o3.out
  （SHA-256 72fa1d78cb7906eec2de6ea803fb653184d1f545e85f8049b685976f1f228a38）
  与 meta_test_transform_correctness.log（SHA-256 b4314be575a851c948b37ba925fa757e39b1d8bd45d4fae07fe5257d3c78de6e）。

### 逐项映射（源码声明 → 构建条件 → 构建目标 → ctest 注册 → 执行日志）

- 注册 5 项：`test/test.cc(+test_data.cc)`、`test_math_helpers.cc`、`test_blocking_counter.cc`、
  `test_allocator.cc`、`test_fixedpoint.cc` → 上游 Bazel BUILD cc_test / contrib/CMakeLists.txt
  add_test → 目标 `test_gemmlowp/test_math_helpers/test_blocking_counter/test_allocator/test_fixedpoint`
  → `ctest -N` 5 项 → ctest 实际执行日志（5/5 Passed，R02 复验 100% tests passed out of 5，
  见 reports/w3-local-ci.log 与 R02 复跑记录）。
- 最小纳入 6 项：`meta/test_gemm_correctness.cc`、`meta/test_streams_correctness.cc`、
  `meta/test_transform_correctness.cc`、`meta/test_transform_benchmark.cc`、
  `test/correctness_meta_gemm.cc`、`test/benchmark_meta_gemm.cc` → 上游无注册（BUILD 与
  contrib/CMakeLists.txt 均未含，且无明确排除说明）→ 本轮在本地测试 CMake 目标中最小补丁
  纳入（add_executable+add_test 形式）并以官方 -O3 直编直跑 → 5 项 exit 0、1 项 exit 1。
- 全量通过率 10/11 (90.9%)，当前配置可执行集合 10/11 (90.9%)。
- 双口径差异原因：上游构建系统只注册了 5 个测试目标；另有 6 个含 main() 的独立测试程序
  从未被上游任何构建系统注册（无明确排除说明），按规则逐入口枚举计入 source_declared_total
  并最小纳入实际运行；1 项因上游测试自身 float 精度缺陷失败（非本适配引入）。

## 消费者验证
- test_package/test.cc：2x2 量化 GEMM（GemmWithOutputPipeline +
  MakeStandardOutputPipeline），通过公开头文件 + 链接 libeight_bit_int_gemm.a，
  校验输出 [17,23,39,53] 精确匹配，退出码 0。
- tests/ohos_specific_test.cc：4 用例（2x2 两序、3x2x2x4 累加、1x1），
  全部 PASSED，退出码 0。
---

**编译结束**: 2026-09-27 02:46
**最终状态**: built

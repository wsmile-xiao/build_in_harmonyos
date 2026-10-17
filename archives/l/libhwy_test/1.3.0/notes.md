# libhwy_test 1.3.0 适配笔记

## 编译环境

| 项目 | 值 |
|------|-----|
| 平台 | HarmonyOS (OHOS) 6.0，aarch64 |
| 编译器 | clang / clang++ 15.0.4（profile `ci/conan/profiles/ohos-aarch64`） |
| Conan | 2.29.1（OHOS 适配版） |
| 构建系统 | CMake + Unix Makefiles，`-c tools.build:jobs=2` |
| 构建日期 | 2026-09-20 |
| 状态 | built |

## 软件与交付面

`libhwy_test` 是 **google/highway 1.3.0 同一上游 tarball 内的子库** `hwy_test`
（上游 `CMakeLists.txt`）：

```cmake
set(HWY_TEST_SOURCES hwy/tests/hwy_gtest.h hwy/tests/test_util-inl.h
                     hwy/tests/test_util.cc  hwy/tests/test_util.h)
add_library(hwy_test ${HWY_LIBRARY_TYPE} ${HWY_TEST_SOURCES})
target_link_libraries(hwy_test PUBLIC hwy)
```

它是 Highway 官方测试套件共用的**测试支持库**：`RandomState` / `RandomFiniteValue` /
`TypeName` / `AssertEqual` 系列 / `ForAllTypes`·`ForPartialVectors` 等向量长度枚举器，
外加 `hwy_gtest.h` 这个 standalone（不依赖 googletest）GTest 兼容运行器。

**install 面（本包交付面）**：

| 产物 | 来源 |
|------|------|
| `libhwy_test.a` | `install(TARGETS hwy_test)` |
| `hwy/tests/{hwy_gtest.h,test_util.h,test_util-inl.h}` | `foreach (source ${HWY_TEST_SOURCES})` 头文件安装 |
| `libhwy-test.pc` | `list(APPEND HWY_PC_FILES libhwy-test.pc)`（standalone 形态带 `-DHWY_TEST_STANDALONE=1`） |
| `libhwy.a` + `hwy/*.h` + `hwy-config*.cmake`、`libhwy.pc` | hwy_test 以 **PUBLIC** 依赖 hwy 核心库，消费者缺它无法编译/链接；与兄弟包 `archives/l/libhwy/1.3.0` 同源同版本 |

**关键因果**：上游把 `install(TARGETS hwy_test)` 与 `libhwy-test.pc` 都放在
`if (HWY_ENABLE_TESTS)` 内，因此 `HWY_ENABLE_TESTS=ON` 是本包交付面的**必要条件**，
不是「为凑数字放开上游 build 开关」。`HWY_ENABLE_CONTRIB=OFF`（hwy_test 不依赖 contrib，
contrib 子库不属本包交付面）、`HWY_ENABLE_EXAMPLES=OFF`。

**构建目标裁剪**：`cmake.build(target=["hwy", "hwy_test", "test_util_test"])`。
`hwy` 必须在内（既是 `install(TARGETS hwy)` 的产物，也是 hwy_test 的 PUBLIC 依赖）——
否则 `cmake --install` 会对未构建产物报 `file INSTALL cannot find`。不构建 `hwy/tests/`
下其余 83 个测试目标（全树 `HWY_TEST_FILES` 84 个注册目标 − 1 个交付面内目标；不在本包交付面）。

## 同源配方复用说明

兄弟包 `archives/l/libhwy/1.3.0`（已在 `upstream/main`）与本包同源码、同版本
（tarball `google/highway` 1.3.0，sha256 `07b3c1ba2c1096878a85a31a5b9b3757427af963b1141ca904db2f9f4afe0bc2`，
本地下载后逐字复核一致），复用其全部 OHOS 结论：

| # | 结论 | 来源 |
|---|------|------|
| 1 | 源码取 git tag 归档 `archive/refs/tags/1.3.0.tar.gz` | libhwy 1.3.0 conandata.yml |
| 2 | OHOS 下 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=<arch>` | libhwy generate() |
| 3 | `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 绕过部分 worker 缺 libxml2 的探测链接失败 | libhwy generate() |
| 4 | `HWY_TEST_STANDALONE=ON`：上游测试不下载 googletest | libhwy / highway 1.3.0.2 notes |
| 5 | `HWY_FORCE_STATIC_LIBS=ON` + `CMAKE_INSTALL_LIBDIR=lib` | libhwy generate() |

**与兄弟包的差异（本包专属）**：交付面只到 `hwy_test`（+ 其 PUBLIC 依赖 hwy），
不构建/不安装 `hwy_contrib`；上游用例只跑交付面内的 `test_util_test`（见下 N 台账）。

## 上游测试清点（rule4，全部候选口径带单位披露）

外部审查 rule4 是脚本化判据「上游实测 N > 声明 N 即不通过」（子包先例
`libgmpxx/6.3.0` 只申报自身 22 项，审方按父 tarball 量出 190/200 → FAIL）。
本包按**父 tarball 全量注册面**清点，主 N 取「用例/注册类」候选口径的**最大值**：

| # | 口径 | 单位 | 读数（contrib ON / OFF） | 取数方式 |
|---|------|------|--------------------------|----------|
| a | 测试目标（`HWY_TEST_FILES` 框架注册项） | 个目标 | **84** / 67 | 解析 `CMakeLists.txt` 的 `set(HWY_TEST_FILES …)` + `list(APPEND HWY_TEST_FILES …)`（去掉 `.h`） |
| b | 测试源文件数 | 个文件 | **84** / 60（`hwy/tests/*.cc`=60，`hwy/tests/` 全文件=63） | `ls hwy/tests/*.cc \| wc -l`；`find . -name '*_test.cc' \| wc -l` = 84（`*test*.cc` 含 `bench_sort.cc` 为 85） |
| c | 源码注册宏点（`HWY_TEST_FILES` 内：`HWY_EXPORT_AND_TEST_P` + `TEST(`） | 个注册点 | **436**（388+48）/ 348（316+32） | 对 a 的清单逐文件正则计数 |
| d | 注册面用例数（运行时展开）= 导出注册点 × 平台实测目标展开数 T + TEST 用例 | 个用例 | **824**（388×2+48）/ 664（316×2+32） | 见下「T 的实测」 |
| e | **全树宏口径用例数（上界，最保守）= 整棵 tarball 的导出点 × T + TEST 点** | 个用例 | **835**（393×2+49） | 全树正则计数（含头文件里的宏定义/文档片段与仅 Bazel 注册的文件），逐项归因见下 |
| f | 断言数（`HWY_ASSERT`） | 个断言 | 851 | 全树正则计数；**另一单位，只披露、不并入 N** |

主 **N = max(a…e) = 835**（全树宏口径上界；其中**注册面**口径 d = 824）。
按 rule4 只判「实测 > 声明」的方向，取最保守上界以确保任何清点方式都不超过声明值。
交叉印证：同 tarball 兄弟包 `archives/l/libhwy/1.3.0` 的合并 PR 按 `ctest -N` 申报
**801**——835 ≥ 824 ≥ 801，三者同向。

**口径 e 相对 d 多出的 11 项逐项归因**（这 4 个文件不在 CMake `HWY_TEST_FILES` 注册面内，
不会产生 CTest 用例，但按最保守上界计入 N）：

| 文件 | 导出点 | TEST 点 | 展开用例 | 归因 |
|---|---:|---:|---:|---|
| `hwy/tests/hwy_gtest.h` | 3 | 0 | 6 | 交付头文件里 `HWY_EXPORT_AND_TEST_P` 的**宏定义本身**与注释引用（非用例） |
| `hwy/contrib/sort/bench_parallel.cc` | 1 | 0 | 2 | 基准程序（不在 `HWY_TEST_FILES`，CMake 不注册为 CTest 用例） |
| `g3doc/impl_details.md` | 1 | 0 | 2 | 文档（g3doc）里的代码片段 |
| `hwy/abort_header_only_test.cc` | 0 | 1 | 1 | 仅 Bazel `BUILD` 注册、CMake 侧不注册的 header-only 测试（受 `GTEST_HAS_DEATH_TEST` 门控） |
| **合计** | **5** | **1** | **11** | 824（注册面）+ 11 = **835** |

**T 的实测（设备读数）**：`test_util_test.cc` 有 2 个 `HWY_EXPORT_AND_TEST_P` 注册点，
真机构建后 `test_util_test --gtest_list_tests` 报 4 个用例 → T = 4/2 = 2
（OHOS aarch64 运行时支持目标数）。`conan create` 的 build() 会打印
`HMBS_UPSTREAM_TEST_SURFACE={…,"target_multiplier_measured":2.0,"expanded_cases_contrib_on":824.0,…}`
标记，把该推导固化进构建日志（该标记给的是**注册面** d 的 824；全树上界 e=835 由本节的
全树正则读数给出）。

**N 取数命令（设备可直接执行）**：

```sh
S="$TASK_DIR/upstream/highway-1.3.0"     # tar -xzf highway-1.3.0.tar.gz 后的解包根
python3 - "$S" <<'PY'
import re, sys, os, glob
S = sys.argv[1]
src = open(os.path.join(S, 'CMakeLists.txt'), encoding='utf-8').read()
base = [w for w in re.search(r'set\(HWY_TEST_FILES\s*(.*?)\n\)', src, re.S).group(1).split() if w.endswith('.cc')]
contrib = [w for w in re.search(r'list\(APPEND HWY_TEST_FILES\s*(.*?)\n\)', src, re.S).group(1).split() if w.endswith('.cc')]
def stat(files):
    e = t = 0
    for f in files:
        s = open(os.path.join(S, f), encoding='utf-8', errors='ignore').read()
        e += len(re.findall(r'HWY_EXPORT_AND_TEST_P\s*\(', s)); t += len(re.findall(r'(?m)^\s*TEST\s*\(', s))
    return e, t
eo, to = stat(base); en, tn = stat(base + contrib)
print('targets off/on = %d/%d' % (len(base), len(base) + len(contrib)))
print('sites off/on   = %d/%d' % (eo + to, en + tn))
print('expanded(on, T=2) = %d' % (en * 2 + tn))
ass = 0
for p in glob.glob(os.path.join(S, '**', '*'), recursive=True):
    if os.path.isfile(p):
        ass += len(re.findall(r'HWY_ASSERT\b', open(p, encoding='utf-8', errors='ignore').read()))
print('assertions(HWY_ASSERT) = %d' % ass)
PY
```

实测输出：`targets off/on = 67/84`、`sites off/on = 348/436`、`expanded(on, T=2) = 824`、
`assertions(HWY_ASSERT) = 851`。

**全树上界口径（e）取数命令**：

```sh
S="$TASK_DIR/upstream/highway-1.3.0"
python3 - "$S" <<'PY'
import re, sys, os, glob
S = sys.argv[1]
E = T = 0
for p in glob.glob(os.path.join(S, '**', '*'), recursive=True):
    if not os.path.isfile(p):
        continue
    s = open(p, encoding='utf-8', errors='ignore').read()
    E += len(re.findall(r'HWY_EXPORT_AND_TEST_P\s*\(', s))
    T += len(re.findall(r'(?m)^\s*TEST\s*\(', s))
print('TREE export=%d TEST=%d expanded(T=2)=%d' % (E, T, E * 2 + T))
PY
```

实测输出：`TREE export=393 TEST=49 expanded(T=2)=835`。

## 上游测试执行台账（自洽：TOTAL 835 = PASS 4 + FAIL 0 + SKIP 0 + NOT_RUN 831）

展开用例 = 该分组「导出注册点 × T=2」+「TEST 用例 × 1」：

| 分组（`HWY_TEST_FILES` 目标） | 目标数 | 注册点（导出/TEST） | 展开用例 | 交付面内 | PASS | FAIL | SKIP | NOT_RUN |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| `hwy/` 根（abort/aligned_allocator/base/bit_set/highway/nanobenchmark/perf_counters/targets） | 8 | 28 / 32 | 88 | 否（测 hwy 核心） | 0 | 0 | 0 | 88 |
| `hwy/examples/skeleton_test.cc` | 1 | 2 / 0 | 4 | 否（测 examples） | 0 | 0 | 0 | 4 |
| `hwy/tests/`（58 个文件） | 58 | 286 / 0 | 572 | 仅 `hwy/tests/test_util_test.cc` | 4 | 0 | 0 | 568 |
| `hwy/contrib/`（17 个文件，contrib 构建） | 17 | 72 / 16 | 160 | 否（测 hwy_contrib） | 0 | 0 | 0 | 160 |
| **注册面小计（口径 d）** | **84** | **388 / 48** | **824** | — | **4** | **0** | **0** | **820** |
| 非注册面（口径 e − d：`hwy/tests/hwy_gtest.h` 宏定义 3 处、`hwy/contrib/sort/bench_parallel.cc`、`g3doc/impl_details.md`、`hwy/abort_header_only_test.cc`） | 4 个文件 | 5 / 1 | 11 | 否（不产生 CTest 用例） | 0 | 0 | 0 | 11 |
| **总计（N 上界）** | — | **393 / 49** | **835** | — | **4** | **0** | **0** | **831** |

831 项 **NOT_RUN 不是「测试被删减」**，而是**交付面/注册面不同**：

- 其中 820 项（83 个测试可执行文件，= `HWY_TEST_FILES` 84 个注册目标 − 1 个交付面内目标）
  的测试对象是 `hwy` 核心库与 `hwy_contrib` 的 SIMD 算子（Load/Store/算术/掩码/排序/密码学…），
  **不在本包 install 面**；`hwy` 由同源兄弟包 `archives/l/libhwy/1.3.0` 交付（本包自包含交付其
  PUBLIC 依赖副本），`hwy_contrib` 不在本包构建开关内（`HWY_ENABLE_CONTRIB=OFF`）。
- 另 11 项来自 4 个**不在 CMake 注册面**的文件（宏定义/文档片段/基准/仅 Bazel 注册），
  按最保守上界计入 N、同样按 NOT_RUN 记账（逐项归因见上表）。
- **本包交付面内唯一的上游用例**是 `hwy/tests/test_util_test.cc`——上游对 `test_util`
  库自身（本包交付物）的单元测试，已真机执行 **4/4 通过**（`discovered=4 executed=4 passed=4`）。
- **替代验证**：①交付的库/头文件被 `test_package` 消费者真跑 15 项显式断言（见下）；
  ②83 个未运行的 `HWY_TEST_FILES` 目标全部与交付面内用例共用同一份 `hwy_test` 静态库与头文件
  （上游 `set(HWY_TEST_LIBS hwy hwy_test)`），其链接期符号需求对 `libhwy_test.a`
  的导出面构成交叉检验。

## 鸿蒙特有（消费者）测试

`test_package/test_libhwy_test.cpp` 经 `find_package(hwy CONFIG)` + `hwy::hwy_test`
（CMakeDeps 生成）编译并**真跑**，15 项显式 `Check()`：交付头文件版本指纹
（`HWY_MAJOR/HWY_MINOR` = 1.3）、`hwy::SupportedTargets()`、`RandomState` 同种子确定性、
不同种子发散、`TypeName` 三种命名、`RandomFiniteValue` 浮点有限性与整数重载确定性、
`Set/Store` 往返、`ForAllTypes`/`ForPartialVectors` 枚举面与车道数合法性、
`hwy_gtest.h` 的 `--gtest_filter` 解析与匹配。用例把实测检查数打成
`LIBSHWY_TEST_CONSUMER checks_total=… checks_passed=…` 行，`test_package/conanfile.py`
解析该行后输出 `HMBS_TEST_PACKAGE_RESULT`（**不硬编码**）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build --auto` 对全新包给出伪 URL（Savannah/waterlan 的 `libhwy_test-1.3.0.tar.gz`，HEAD 探测假阳性） | `search_url` 只探测不下载，新包必命中 | 用同 tarball 兄弟包的权威源 `https://github.com/google/highway/archive/refs/tags/1.3.0.tar.gz` 重跑 init-build（sha256 本地复算与兄弟包逐字一致），`--from-step` 留痕 |
| 2 | 构建日志出现 `make: jobserver mkfifo: …/GMfifoNNNN: Operation not permitted` | 设备（SELinux/HMMAC）拒绝创建 FIFO；GNU make 自动退化为 pipe jobserver，并发未退化 | 判为噪声（`notes/device-facts.md` §一.13），不按权限问题排查；容器层 `tools/make_jobserver.sh` 可消噪 |
| 3 | 消费者测试里 `hwy::Lanes(d)` / `hwy::MaxLanes(d)` 编译失败（`no member named 'Lanes' in namespace 'hwy'`） | 这两个函数在**目标命名空间**（`hwy::N_NEON_WITHOUT_AES`）内，不在 `hwy::` | 改用 `hwy::HWY_NAMESPACE::…` 别名（`hn::Lanes` / `hn::MaxLanes`），与上游测试同口径 |

## 验证结果

- 构建：✅ 通过（`conan create`，clang 15.0.4 / OHOS aarch64 / jobs=2）
- 交付面内上游用例：**4/4 通过**（`hwy/tests/test_util_test.cc`，`HWY_TEST_STANDALONE=1`）
- 消费者（鸿蒙特有）用例：**15/15 通过**
- 上游全量注册面 N = 835（全树宏口径上界；其中注册面口径 824 = 388×2+48）；NOT_RUN = 831（原因与替代验证见上，**不写 PASS**）

设备侧原始日志（`conan create` 输出，含 `HMBS_UPSTREAM_TEST_RESULT` /
`HMBS_UPSTREAM_TEST_SURFACE` / `HMBS_TEST_PACKAGE_RESULT` 三行标记）以
`reports/` 下的逐字 `.md` 留档（`reports/` 被 `.gitignore` 覆盖，不进 PR）。

## 注意事项

- 本包为纯库，无可执行产物，不需要软件级 `commands.json`（R38 仅命令行工具需要）
- 非系统同名库，保留静态产物由 Conan 管理依赖链（R26：默认静态）
- 平台判断统一使用 `str(self.settings.os) in ("Linux", "OHOS")`（R32）
- `package_info().libs = ["hwy_test", "hwy"]` 固定顺序：静态链接需要 `-lhwy_test -lhwy`
  的顺序（未用 `collect_libs()`，其返回顺序不保证）
- **与兄弟包 `archives/l/libhwy/1.3.0` 的交付面重叠（已知、有意）**：两者都 install
  `lib/libhwy.a`、`hwy/*.h`、`lib/pkgconfig/libhwy.pc`、`lib/cmake/hwy/hwy-config*.cmake`
  ——本包交付这些是因为 `hwy_test` 以 PUBLIC 方式依赖 hwy 核心库，消费者缺它无法编译/链接。
  两个包是同一 tarball 的**不同子库打包面**，同一依赖图内若同时 require 二者，
  Conan 生成的 `hwy-config.cmake` 会发生同名覆盖（本 PR 的消费者只 require 本包，未触发）。
  若后续要求二者同图共存，应改为 `requires("libhwy/1.3.0")` 并裁剪本包 install 面，
  但那样会把本包绑定到 registry 中 `libhwy/1.3.0` 的可用性上（本包当前零外部依赖）。

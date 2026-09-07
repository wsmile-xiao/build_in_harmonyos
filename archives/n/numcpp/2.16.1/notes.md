# numcpp 2.16.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only，配方无编译产物）
- 编译日期: 2026-09-04
- 编译器: OHOS SDK clang 15.0.4 (aarch64-unknown-linux-ohos) / libc++ / C++17
- 状态: built

## 概述

NumCpp 2.16.1 是纯 header-only 的 C++17 NumPy 风格数值库：
`include/` 下共 **544 个 `.hpp`**，无任何需编译/链接的库产物。
上游 tag 名为 `Version_2.16.1`（非 `v2.16.1`），官方 tarball sha256 见 conandata.yml。

上游 CMakeLists.txt 在默认配置（`NUMCPP_NO_USE_BOOST=OFF`）下 `find_package(Boost
1.68.0 REQUIRED COMPONENTS date_time log log_setup)`；公共头 `NumCpp.hpp` 伞形
头在默认宏配置下会 include Boost.Math / Boost.DateTime / Boost.Random /
Boost.Polynomial / Boost.Log 头（全部位于 `#ifndef NUMCPP_NO_USE_BOOST` 保护内）。

## 适配决策

1. **保持 Boost 使能（默认）**：不定义 `NUMCPP_NO_USE_BOOST`，保留全模块
   （Special/DateTime/Logging/Polynomial/Random/gcd/lcm/hamming）。
2. **依赖 = boost/1.84.0（仅需头文件）**：ohpcd 已发布 boost/1.84.0（完整 Boost
   头树 + filesystem/regex/program_options/iostreams 静态库）。NumCpp 用到的
   Boost 部件（math/date_time/random/polynomial）均 header-only；完整
   `NumCpp.hpp` 编译链接运行无需链接已编译 boost 库。
   - 配方 `requires("boost/1.84.0", transitive_headers=True)`
   - `package_info()` `cpp_info.requires = ["boost::boost_headers"]`（传播 Boost 头
     与 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 定义）
3. **package_type = header-library**，`package()` 拷贝 `include/`（544 hpp）+ LICENSE；
   `package_id()` clear。

## 上游测试处理（2026-09-04 攻坚后：全量真实运行，非豁免）

### pytest 主套件（test/pytest，25 文件 / 748 定义 / 747 收集）
- **已真实全量运行**（OHOS PC，venv python3.12.9 + numpy **2.2.6**，与上游
  environment.yml `numpy=2.2` 对齐）：
  - 驱动方式：官方 tarball 解压 → 按上游 `test/pytest/src/CMakeLists.txt` 语义用
    OHOS SDK clang++ 编译 21 个 pybind11 绑定 TU 为
    `NumCppPy.cpython-312-aarch64-linux-ohos.so`（EXT_SUFFIX 平台 tag）放入
    `test/pytest/` → `python -m pytest test_*.py -v --tb=short`。
  - **结果：732 passed / 12 skipped / 3 failed**（12 skipped 为上游作者显式
    `pytest.skip`，任何平台一致）。
  - 3 个 failed 均为**有实证的平台/依赖差异**（不改测试断言无法通过），逐条见
    `reports/pytest-failures-analysis.md`：
    1. `test_fft.py::test_ifft`：OHOS libm 与 glibc sin/cos 1~2 ulp 差 → `np.round(...,5)`
       舍入边界翻转（实测最大绝对误差 ~2.5e-12）。
    2. `test_functions.py::test_diff`：NumPy 2.x 负 float→uint32 越界 cast 置 0
       （RuntimeWarning），而 `np.diff(uint32)` 按无符号回绕；上游测试假设 NumPy 1.x 语义。
    3. `test_functions.py::test_nanpercentile`：NumCpp 与 NumPy 两独立百分位实现精确
       `==`，aarch64 下特定数据差 1 ulp。
- 对照：社区默认 numpy 2.5.2 运行多 1 个 failed（`test_cross`：NumPy ≥2.5 移除
  2 元素向量沿轴叉积），随 numpy 2.2.6 消除；因此取 numpy 2.2.6 为口径。
- **编译期唯一修改**（测试绑定源码，OHOS libc++ 头文件差异，仅测试期使用、不打入
  配方/包）：`test/pytest/src/Functions.cpp::signbitScalar` 中 `signbit` 未限定调用在
  OHOS libc++ 下与 `nc::signbit` 歧义 → 改为 `std::signbit`。补丁文本：
  `reports/upstream-test-binding-ohos.patch`。
- 全量运行日志与复现脚本：`reports/pytest-full-20260904-numpy2.2.6.log`、
  `reports/pytest-full-20260904-numpy2.5.2.log`、`reports/pytest-per-file.md`、
  `reports/run_upstream_pytest.sh`。

### gtest Logger 测试（test/gtest，2 TU）
- **已真实编译运行**：GTest 用制品仓 `gtest/1.17.0`（conan download，ohos clang15
  静态库）；Boost.Log 用本机从 boost-1.84.0 源码 b2 自建
  `libboost_log.a/libboost_log_setup.a`（+ thread/filesystem/regex/date_time/
  chrono/atomic/system），复用 ohpcd boost 的 OHOS musl 补丁
  （`sp_thread_sleep.hpp` 增 `&& !defined(BOOST_SP_NO_PTHREAD_SETCANCELSTATE)`）。
- **LoggerTests：5/5 PASSED**（LoggerTestSuite 2 + BinaryLoggerTestSuite 3）。
- 证据：`reports/gtest-LoggerTests-20260904.log`、`reports/boost-1.84-log-build-20260904.log`。

### C++ test/multiple（配方内执行）
- 已在 conanfile.py `build()` 真实编译运行 rc=0（HMBS_UPSTREAM_TEST_RESULT passed）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 tag 名与包版本不同（Version_2.16.1 vs 2.16.1） | GitHub 上游 tag 命名 | conandata.yml 指向官方 `refs/tags/Version_2.16.1.tar.gz` |
| 2 | github.com 下载慢 | 本机 GitHub 连通性 | 本地 ghfast.top 镜像预取 tarball；conandata 仍官方 URL（R39） |
| 3 | 初次 smoke 崩溃 rc=134 | DateTime 测试串缺结尾 `Z`，NumCpp 正则不匹配抛异常 | 测试字符串补 `Z`（非 OHOS 问题） |
| 4 | NumCpp.hpp include Boost.Log（Logger.hpp） | 伞形头全量引入 | include 不需链接 libboost_log；真正实例化 LOG_* 宏才需要 → 本机自建 Boost.Log 跑通 gtest |
| 5 | pybind11 绑定编译 `signbit` 歧义（Functions.cpp） | OHOS libc++ `<cmath>` 在全局命名空间暴露 `::signbit`，与 `using namespace nc` 的 `nc::signbit` 冲突 | 测试绑定源改为 `std::signbit`（reports/upstream-test-binding-ohos.patch，仅测试期） |
| 6 | pytest 3 例运行失败（ifft/diff/nanpercentile） | 平台 libm 1~2ulp 差 / NumPy 2.x cast 语义 / 独立实现精确相等 | 不改断言，逐条豁免（reports/pytest-failures-analysis.md），证据日志留存 |
| 7 | gtest 需 libboost_log/libboost_log_setup | ohpcd 发布的 boost 变体不提供 log 编译库 | 本机 b2 自建 boost-1.84 log 库（本地、不入 numcpp PR），跑通 LoggerTests |
| 8 | b2 首次构建失败（assert.h/__config_site 缺失、pthread_setcancelstate 未声明） | b2 默认注入 `--target=arm64-pc-linux` 覆盖 OHOS 目标；OHOS libc 缺 pthread_setcancelstate | cxxflags 显式 `--target=aarch64-unknown-linux-ohos`；复用 ohpcd 的 musl 补丁（sp_thread_sleep） |

## 源码修改
- 配方打补丁：**无**（zero-patch header-only 配方，conandata 无 patches）。
- 测试执行期修改（不入库、不打包，供复现全量 pytest）：`test/pytest/src/Functions.cpp`
  一行 `signbit`→`std::signbit`（见 reports/upstream-test-binding-ohos.patch）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| boost | 1.84.0（ohpcd） | 公共头引用的 Boost 头文件（math/date_time/random/polynomial/log） |

## 验证结果

- **pytest 主套件**（上游 environment.yml 口径 numpy 2.2.6）：732/747 passed
  （+12 上游 skip），3 平台差异豁免（详见 reports/pytest-failures-analysis.md）。
- **gtest LoggerTests**：5/5 PASSED（本机 GTest1.17 + 自建 Boost.Log）。
- **test/multiple**：编译+运行 rc=0（conanfile build() 内，HMBS passed）。
- test_package：28/28 断言通过；conan-verify G0-G4/L2/L4/L5 全 PASS；W3 conan create
  exit 0（reports/conan-create.log / w3-local-ci.log）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方（requires boost/1.84.0） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/ | CMake 消费者测试（28 断言）+ MANIFEST.yml（真实豁免收敛） |
| reports/pytest-full-20260904-numpy2.2.6.log 等 | 上游全量 pytest/gtest 实测日志与复现脚本 |
| reports/test-report.md | 测试报告（数字一致口径） |

## 注意事项
- NumCpp header-only；下游 include `NumCpp.hpp` 即可，CMake 消费者
  `find_package(NumCpp)` 链接 `NumCpp::NumCpp`（CMakeDeps 生成）。
- 使用 nc::logger 等 Boost.Log 能力需额外提供 Boost.Log 编译库（ohpcd 生态不提供，
  属已知生态缺口；本机自建验证通过 gtest LoggerTests）。
- pytest 全量运行需要 OHOS Python 科学 venv（numpy 2.2.x 对齐上游），复现命令见
  `reports/run_upstream_pytest.sh`；conan create/CI 默认不依赖该环境（零 Python 依赖）。
---

**编译结束**: 2026-09-04
**最终状态**: built

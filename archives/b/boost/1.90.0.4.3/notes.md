# Boost 1.90.0.4.2 — 质量补强版（上游测试实测 + 鸿蒙特有测试 + 完整 W3）

## 背景与版本策略（R37 / L0j）

本版本是 `boost/1.90.0.4.1`（已发布 main）的**质量补强后缀**：上游源码、组件集、补丁均与
1.90.0.4.1 完全一致（同一 `boost-1.90.0-cmake.tar.xz`，同一
`0001-cmake-avoid-versioned-soname-links-on-ohos.patch`），仅补齐 1.90.0.4.1 缺失的三项质量要求：

1. **上游测试实测（R51）**——1.90.0.4.1 的 `MANIFEST.yml` 写 `upstream_tests total:0`（未跑，违反 R51）；
2. **鸿蒙特有测试**——1.90.0.4.1 无（打包布局断言 + dlopen 消费者）；
3. **完整 W3 本地验证**——`ohc-run.py finish ... built`（W2 结构 + R36 依赖 + conan create）。

## 制品包（conan create 实测，2026-09-25）

- 命令：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
- 日志：`.tmp-boost-1.90.0.4.2/create1.log`（中间迭代记录）；最终权威 W3 日志 `reports/w3-local-ci.log`
- 包：`boost/1.90.0.4.2#100ff22eade92c32b38c4f2e9460d70b:01d92cf349a0dd98ff915f4bd99a04430171517f`（recipe revision 以最终 W3 为准；create1.log 阶段 recipe rev 为 fee75683…，差异源于 W3 预下载阶段 conandata.yml 被工具临时改写后还原，binary package revision 一致）
- PREFIX（`conan cache path`）：`/storage/Users/currentUser/.conan2/p/b/boost28441a9be5f0d/p`
- test_package 两个既有消费者编译/签名/运行通过（`test_boost_morpheus_components`、
  `test_boost_unit_test_framework` → "Running 1 test case… No errors detected"）。

包内 14 个 `libboost_*.so` 全部带 `.codesign`（`llvm-objcopy --dump-section` 实测各 4096 字节），
**无任何 `libboost_*.so.1.90.0` 版本化软链**（patch + `BOOST_INSTALL_NO_VERSIONED_LIBS=TRUE` 生效）。
注：`boost_system` 在 Boost 1.90 已 header-only，包内无 `libboost_system.so`——
`conan create` 日志中 `Component 'system': no library matching 'boost_system' found` 为**预期 WARN**
（1.90.0.4.1 同样存在），`Boost::system` 组件以纯头形式提供。

## 上游测试实测（R51 三步法，核心交付）

### 第一步：清点（见 `reports/upstream-tests/UPSTREAM-TESTS-SUMMARY.md`）

6 个编译型组件，从上游发布源码 `libs/<lib>/test/` 清点官方测试：
以 `Jamfile.v2` 的 **quick 目标 / quick*.cpp** 为准；无 quick 目标的组件取主官方 run 目标。

| 组件 | 清点依据 | 官方测试 |
|---|---|---|
| system | `libs/system/test/Jamfile.v2:85` quick 目标 | `quick.cpp` |
| filesystem | `libs/filesystem/test/Jamfile.v2:103` quick 目标（`<define>BOOST_FILESYSTEM_VERSION=4`） | `quick.cpp` |
| program_options | `libs/program_options/test/Jamfile.v2:43` quick 目标（`--path=initial`） | `quick.cpp` |
| atomic | 无 quick 目标；`test-suite atomic` 主 run | `atomic_api.cpp` |
| container | 无 quick 目标；`test_all` 枚举 | `deque_test.cpp` |
| unit_test_framework | 无 quick 目标；官方 shared-library usage-variant | `usage-variants-ts/shared-library-test.cpp` |

### 第二步：实测（OHOS aarch64 原生）

- 工具链：`/data/service/hnp/bin/clang++ -std=c++17 -I<PREFIX>/include <test>.cpp
  -L<PREFIX>/lib -Wl,-rpath,<PREFIX>/lib -lboost_<lib> -o <out>`
- 签名：`llvm-objcopy --remove-section .codesign <out> && binary-sign-tool sign -inFile <out> -outFile <out> -selfSign 1`
- 运行：`LD_LIBRARY_PATH=runtime-libs <out>`（`reports/upstream-tests/runtime-libs/`，
  包内复制+就地重签名的运行期共享库）
- 编译/签名/运行脚本：`reports/upstream-tests/run_one.sh`；逐项日志同目录。

### 第三步：申报表（实测 N/N′ + 通过率）

| # | 组件 | 测试 | 链接组件 | 结果 | 日志 |
|---|---|---|---|---|---|
| 1 | system | quick.cpp | 无（header-only） | ✅ | `system_quick.log` |
| 2 | filesystem | quick.cpp（`-DBOOST_FILESYSTEM_VERSION=4`） | filesystem | ✅ | `filesystem_quick.log` |
| 3 | program_options | quick.cpp（`--path=initial`） | program_options | ✅ | `program_options_quick.log` |
| 4 | atomic | atomic_api.cpp | atomic | ✅ | `atomic_api.log` |
| 5 | container | deque_test.cpp | container | ✅ | `container_deque.log` |
| 6 | unit_test_framework | shared-library-test.cpp | unit_test_framework | ✅ | `unit_test_framework_shared.log` |

**实测 6/6 = 100% 通过率，无崩溃点。**

> 口径说明：本包上游测试采用 **R51 手工实测**（`reports/upstream-tests/run_one.sh`，对官方
> quick/run 测试源码逐个编译→签名→运行）；配方 `BUILD_TESTING=False`，build 阶段**未启用
> ctest/make check**，W3 日志中 `L1c Upstream official tests executed` 为 CI 启发式字串匹配
> （命中 `lib/cmake/boost_concept_check-*.cmake` 安装路径），并非构建期测试，真实证据以上述
> `reports/upstream-tests/*.log` 为准。

## 鸿蒙特有测试（必须有，双管齐下）

`test_package` 新增两类 OHOS 专属验证，均在 `conan test`/`conan create` 的 `test()` 阶段真实执行：

1. **Python 侧打包检查** `conanfile.py::_check_package_layout()`：
   - 断言包 `lib/` 下**不存在** `libboost_*.so.<digits>` 版本化 soname 软链（HMDFS 不兼容，正是
     patch + `BOOST_INSTALL_NO_VERSIONED_LIBS` 修的点）；
   - 断言每个 `libboost_*.so` 均含 `.codesign` section（`llvm-objcopy --dump-section` 实测）。
2. **C++ dlopen 消费者** `test_boost_ohos_dlopen.cpp`（`test_boost_ohos_dlopen`）：
   对 5 个编译型组件库（atomic/container/filesystem/program_options/unit_test_framework）
   `dlopen(RTLD_NOW)` + `dlsym` 真实导出符号 + **实际调用**（atomic `lock_pool::signal_fence`、
   container `dlmalloc_malloc/free` 往返、filesystem `filesystem_error::get_empty_path`、
   program_options `bool_switch`、unit_test_framework `framework::test_aborted`），
   全部通过打印 `test_boost_ohos_dlopen: all 5 compiled component libraries dlopen+dlsym+call OK`。

`test_package/MANIFEST.yml`：`upstream_tests` 段 6 条真实申报（count/run/pass/pass_rate），
`test_package_tests` 新增 dlopen 消费者与打包检查条目（共 4 项）。

## 遇到的问题与根因（OHOS 加载器签名状态失效）

**现象**：同一份已签名 `libboost_*.so`，在 `conan create` 的 test_package 阶段可正常加载；
但随后任何进程**读取**该文件（`cp`、`llvm-objcopy --dump-section`、甚至独立 `conan test` 重跑）
之后，加载器即报 `symbol not found` / `dlopen: Permission denied`。`conan test` 对已缓存包重跑
即复现（第一次 create 后 test_package 必过，重跑必挂）。

**根因（已验证的技术证明，2026-09-25）**：OHOS `/storage/Users` 为 tmpfs 挂载，选项含
`hmmac=use_task`。实测最小复现：
1. 就地重签 `libboost_program_options.so` → 立即 `dlopen(RTLD_NOW)` **成功**（仅因依赖
   `libboost_container.so` 未重签而继续失败）；
2. 对该文件执行一次 `llvm-objcopy --dump-section .codesign`（纯读）→ 再 `dlopen` 同文件
   **立即 "Permission denied"**；
3. 再次就地重签 → 又恢复可加载。

即：**该文件系统上「读」会失效 `.codesign` 与文件当前状态的一致性，加载器据此拒绝加载；
「就地重签」恢复一致性**。这也解释了 1.90.0.4.1 为何能在 create 时通过 test_package 而
重跑/后续消费不稳定。

**处置**：test_package `test()` 顺序固定为 `_check_package_layout()`（读）→
`_refresh_package_lib_signatures()`（就地重签，刷新）→ 再运行全部消费者；
上游测试的运行期库统一从包内复制到 `runtime-libs/` 后**就地重签**再加载。
该顺序下 `conan test`（重跑）多次实测稳定通过。

## 验证证据路径

- 构建日志：`.tmp-boost-1.90.0.4.2/create1.log`；`conan test` 重跑：`.tmp-boost-1.90.0.4.2/conan-test2.log`、`conan-test6.log`（最终通过）
- 上游测试：`reports/upstream-tests/UPSTREAM-TESTS-SUMMARY.md` + `reports/upstream-tests/*.log` + `runtime-libs/`
- W3 finish：`ohc-run.py finish boost 1.90.0.4.2 built` → 自动写 `.ci-result.json`
- CI 模拟：`CI_PACKAGES="archives/b/boost/1.90.0.4.2" zsh ci/conan/build_and_test.sh`
---

**编译结束**: 2026-09-25 13:27
**最终状态**: built

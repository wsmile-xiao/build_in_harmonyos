# libxtrxll 0.0.1-git20201202.1b6eddf 适配笔记

## 编译环境
- 构建系统: cmake（上游为手写 CMakeLists.txt，非 autotools/meson）
- 编译日期: 2026-10-04
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）
- 目标: HarmonyOS PC aarch64（**原生构建**，build == target == OHOS/armv8）
- Conan: 2.29.1（OHOS 适配版），profile `ohos`
- 状态: built（本地 `conan create` 验证通过；制品仓上传由 CI release 流水线完成 → published）

## 上游信息
- 仓库: https://github.com/myriadrf/libxtrxll（原 `xtrx-sdr/libxtrxll`，已改名/迁移）
- commit: `1b6eddfbedc700efb6f7e3c3594e43ac6ff29ea4`（2020-12-02，"Fixing typos (#5)"）
- tarball sha256: `1ae6d112e41fe7427ab97b7e828609f08aea177edb6fdc08726cc58f01f8566b`
- 许可证: LGPL-2.1（上游 LICENSE 文件）★ 注意：GitHub 元数据标为 Apache-2.0，但仓库内 LICENSE 全文为
  GNU LGPL v2.1，且所有源文件头均声明 LGPL-2.1-or-later。以仓库内 LICENSE 文件为准（conanfile 用 `LGPL-2.1`）。

## 语言预检（R47）
```
expected=cpp, detected=c, 语言匹配（c↔cpp 兼容族）
language_evidence:
  build_system: cmake
  manifest:     CMakeLists.txt project(libxtrxll C)
  source_stats: 源文件 11 个（c:11），主体占比 100%
```
exit 0，通过，进入适配主流程。

## 源码结构
```
CMakeLists.txt                 顶层：project(libxtrxll C)、SHARED 库、CPack 打包
mod_pcie/xtrxll_pcie_linux.c   PCIe 传输：/sys/class/xtrx/、/dev/xtrx*、ioctl
mod_usb3380/xtrxll_libusb3380.c USB3380 传输：需要外部 libusb3380
xtrxll_api.c                   公共 API 与传输注册
xtrxll_base.c / _pcie.c / _mmcm.c / _flash.c / _log.c / _port.c
tests/test_xtrxll.c            交互式硬件工具（1163 行，无断言）
tests/test_xtrxflash.c         交互式 Flash 工具（426 行，无断言）
```

## 依赖
- **libusb3380**：USB3380 传输插件的外部依赖。仓库 `archives/` 与 OHOS 制品仓（`conan list libusb3380/*` → 0 条）均不存在。
  该依赖是**可选**的（上游 `find_package(libusb3380)` 找不到时会 `set(ENABLE_USB3380 OFF)`），
  且未发布到制品仓。按 W0/R36 判定：不捎带适配，直接以 `-DENABLE_USB3380=OFF` 关闭该可选插件。
  PCIe 传输与全部公共低层 API（open/discovery/set_param/LMS7 SPI/DMA/MMCM/flash/log）不受影响。
- 其余（pthread/rt/dl/filesystem）在 OHOS 上属基础 C 运行时，无需显式声明。

## OHOS 适配要点（全部在 conanfile.py，**零源码补丁**）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败 `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 2.8)`，本机 CMake 4.1.2 已移除 <3.5 兼容 | `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`（必须是 **cache** 变量，普通 `variables` 不进 CMakeCache、压不住） |
| 2 | `libxtrxll.so` 链接失败（非 PIC 目标重定位） | 插件默认 STATIC 并归档进 .so；上游仅对 `CMAKE_SYSTEM_NAME MATCHES "Linux"` 的静态插件加 `-fPIC`，HarmonyOS 上不匹配 | `tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"`（全树统一，胜于直接改上游 `if()` 判断） |
| 3 | `find_package(libusb3380)` 找不到 → 警告 | 依赖未适配/未发布（见上） | `-DENABLE_USB3380=OFF` 关闭可选插件 |
| 4 | 运行时插件查找依赖加载器路径 | 上游可把插件编成动态库，核心用 `dlopen("libxtrxll_pcie.so.0")` 查找，依赖 RPATH | 保持上游默认 `XTRXLL_STATIC=ON`，PCIe 传输直接编入 `libxtrxll.so`，避免 RPATH 依赖 |
| 5 | `copy(..., delete=True)` 报 TypeError | Conan 2 的 `conan.tools.files.copy()` 无 `delete` 参数 | 改用 `conan.tools.files.rm(self, pattern, dir)` 清理 `*.la`/`*.dylib` |

> 结论：本库在 OHOS 上**不需要任何源码补丁**，`patches/` 为空。适配全部由 CMake cache/普通变量完成
> （R1 参数最少化 / R8 源码修改四不准则 / R3 不手动造 patch）。

## 上游测试清点（R51 三步法 · 第一步）

清点命令与结果：
```bash
ls tests/                                   # CMakeLists.txt  test_xtrxflash.c  test_xtrxll.c
grep -rn "enable_testing\|add_test(" .      # 0 hits（全树无 ctest 注册）
sed -n '1,12p' tests/CMakeLists.txt         # 只有 add_executable + install
```
- 上游 `tests/` 下有 **2 个 .c 程序**，但均为 getopt 驱动的**交互式硬件工具**：无任何断言，退出码只反映硬件操作结果；
  通过 `xtrxll_open(device, ...)` 打开真实设备（`/dev/xtrx*`、`/sys/class/xtrx/`）。
- `grep -rn "enable_testing|add_test("` 命中数 = **0**，即 ctest 注册用例数 = 0。
- 因此「上游可自动化运行的测试用例数」= **0**。两个程序仍由 `add_subdirectory(tests)`（上游无条件）
  在本配方 `build()` 的 `cmake.build()` 中编译，作为构建期可编译性证据；无 XTRX 硬件时执行它们无意义，
  故不纳入自动化执行。

## 测试（R51 第二步/第三步）

本机 **HarmonyOS PC aarch64 真机**，无 XTRX 硬件与内核驱动（环境事实）。

`conan create . -pr:h=ohos -pr:b=ohos --build=missing`：

| 测试程序 | 断言数 | 结果 |
|----------|--------|------|
| `test_package/test_consumer.c` | 11 | 11/11 通过 |
| `test_package/test_ohos_offline.c` | 7 | 7/7 通过 |
| **合计** | **18** | **18/18（100%）** |

`test_consumer.c`（消费者集成测试，仅设备无关的确定性行为）：
1. `xtrxll_discovery(devs, 0) == 0`（零长度缓冲区）
2. `xtrxll_discovery(devs, 4) >= 0`（返回可用设备数）
3. discovery 不超过传入缓冲区上限
4. `xtrxll_open("usb3380://...")  == -ENODEV`（未知/未编译传输）
5. `xtrxll_open("pcie://<不存在路径>") == -ENODEV`（核心对"无可用设备"的统一返回）
6. `set_loglevel/get_loglevel` 往返（WARNING）
7. 自定义 logfunc 在 open 失败路径上被派发
8. 自定义 logfunc 收到 `XTRXLL_ERROR` 严重级
9. loglevel=NONE 时同一失败路径静默
10. `set_loglevel/get_loglevel` 往返（NONE）
11. `xtrxll_open(NULL)` 无设备时 `== -ENODEV`
> 第 11 项按 discovery 结果分支（有硬件时改为断言 open 成功并 close），保证断言总数恒定。

`test_ohos_offline.c`（鸿蒙特有）：
1. `dlsym(RTLD_DEFAULT, "xtrxllpciev0_init") != NULL` —— 证明 PCIe 传输**编入** libxtrxll.so（XTRXLL_STATIC），
   而非运行时 dlopen 的独立插件（若为动态插件，该符号只存在于被单独加载的 .so 中，此处不可见）
2. `dlsym(RTLD_DEFAULT, "xtrxll_open") != NULL` —— 测试确实绑定在打包产物上
3. 库（含折叠入的插件）可加载运行
4. 无 XTRX 驱动时 discovery 无错误
5. 无 XTRX 时 discovery 返回 0 设备
6. 重复 discovery 稳定返回 0
7. 失败的传输 open 不泄漏文件描述符

两个程序均真实链接 libxtrxll 并调用其公共符号（R34），CI L1e 破坏性反向验证（移走 lib/ 或 include/）会使本测试失败。

## 关键命令
```bash
# 语言预检
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight libxtrxll 0.0.1-git20201202.1b6eddf --src <源码目录>
# 初始化
OHC_PROJECT_DIR=<worktree> python3 $SKILL_ROOT/scripts/ohc-run.py init-build libxtrxll 0.0.1-git20201202.1b6eddf --url=<官方 tarball>
# 本地验证（真机）
conan create . -pr:h=ohos -pr:b=ohos --build=missing
```

## 注意事项
- 本机为 HarmonyOS 真机（`uname -a` → `HarmonyOS ... HongMeng Kernel 1.12.0 ... aarch64`），
  `os=OHOS/arch=armv8/compiler=clang 15` 与 CI 一致，故 `conan create` 的结论可迁移到 CI clean 环境。
- 动态库保留 `.so`（非系统同名库，R26 不适用；`ls /lib/libxtrxll*` 无同名项）。
- 纯库包（R38）：包内 `lib/xtrxll/` 下的 `test_xtrxll`/`test_xtrxflash` 是上游 install 规则带来的
  **测试工具**，不通过 `cpp_info.bindirs` 声明，故**不需要** `commands.json`。
- `cd` 进 test_package 单独构建会在归档内留下 `build/` 残留，已清理；`build` 目录不在提交内容中。

---

### 对话 #1
- 2026-10-04：完成 libxtrxll 0.0.1-git20201202.1b6eddf 鸿蒙适配（路径 A 基础适配）。
  查重通过（archives 与制品仓均无 libxtrxll）。上游 myriadrf/libxtrxll commit 1b6eddf（原 xtrx-sdr，已改名）。
  零源码补丁：CMake 4.x policy 下限 + 全树 PIC + 关闭可选 USB3380 插件 + 保持静态插件注册。
  同族先例 liblms7compact 0.0.1-git20190125.bfd5418（xtrx-sdr/liblms7002m）已在仓内。
  本机 HarmonyOS 真机 conan create 全绿，test_package 18/18 断言通过（消费者集成 11 + 鸿蒙特有 7）。
---

**编译结束**: 2026-10-04 22:54
**最终状态**: built

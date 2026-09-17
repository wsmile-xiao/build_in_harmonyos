# ns-3 3.48 HarmonyOS PC 适配笔记

## 适配概述

- 三方库：ns-3（nsnam 离散事件网络仿真器）
- 上游版本：3.48（tag `ns-3.48`，2026-06-02 发布）
- 上游仓库：https://github.com/nsnam/ns-3-dev-git（镜像 https://gitlab.com/nsnam/ns-3-dev）
- 适配路径：路径 A（基础适配）
- 构建策略：交叉编译（ohos-aarch64 profile）。C++20；模块裁减至 `core;network;point-to-point`（依赖闭包自动补上 stats）。
- 依赖：无外部 conan 依赖（可选依赖 GSL/GTK3/SQLite/Eigen/libxml2 全裁剪；Python 绑定关闭）。

## 源码获取与校验

- 下载：官方 https://www.nsnam.org/releases/ns-3.48.tar.bz2（46,672,472 B）
- sha256（本地计算）：`5700ceecef2c9bc862502914b2237fe798d4c7ae07652247050e300e49407c4d`
- 双源核对：GitLab mirror（gitlab.com/nsnam/ns-3-dev tag ns-3.48）archive 解压后，对 VERSION、
  CMakeLists.txt、src/CMakeLists.txt、src/core/CMakeLists.txt、build-support/macros-and-definitions.cmake、
  build-support/custom-modules/ns3-compiler-and-linker-support.cmake 共 6 个关键文件逐一 sha256，
  **全部一致** → 下载源可信、内容未被篡改。

## 关键技术点（踩坑记录）

1. **Clang 版本 FATAL 检查**：ns-3 3.48 要求 Clang ≥ 17.0.0
   （`build-support/custom-modules/ns3-compiler-and-linker-support.cmake:23-26`，
   顶层 `CMakeLists.txt:15` 定义 `Clang_MinVersion`）。HarmonyOS 工具链为 clang 15.0.4，
   **必须 patch** 顶层 `set(Clang_MinVersion 17.0.0)` → `15.0.0`（补丁 0001）。

2. **C++ 标准门槛 C++23 → C++20**：`build-support/macros-and-definitions.cmake:390` 把
   `CXX_UNSUPPORTED_STANDARDS` 含 20、并设 `CMAKE_CXX_STANDARD_MINIMUM 23`；clang15 无
   `-std=c++23`。补丁 0002 将门槛降为 C++20（源码实际只需 C++20：
   `std::remove_cvref_t`、`std::bind_front`、`operator<=>`）。同时 recipe 用
   `tc.blocks.remove("cppstd")` + `CMAKE_CXX_STANDARD=20` 覆盖 profile 的 `cppstd=17`
   （否则 conan 的 cppstd block 会写普通变量压过 variables）。

3. **write_lock 平台判定**：`build-support/custom-modules/ns3-lock.cmake:124` 仅识别
   LINUX/APPLE/WIN32/BSD，`CMAKE_SYSTEM_NAME=HarmonyOS` 直接 `message(FATAL_ERROR "Platform
   not supported")`。补丁 0003 在判定中加入 OHOS/HarmonyOS。

4. **libc++15 缺 `std::array::operator<=>`**：`src/network/utils/ipv6-address.h:413`
   `m_address <=> other.m_address` 在 libc++15（LLVM16 才加）编译失败
   （`invalid operands to binary expression`）。补丁 0004 改为逐字节比较。

5. **共享库缺 SONAME 致 DT_NEEDED 记绝对路径（关键）**：HarmonyOS 无 CMake
   `Platform/HarmonyOS.cmake`，`CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` 为空 → 产出的
   `libns3.48-*.so` 不带 DT_SONAME，内部依赖被记录为**绝对构建路径**
   （`.../b/build/lib/libns3.48-*.so`）。消费者运行时会把包内副本与构建目录副本**同时加载**，
   ns-3 的日志组件静态注册被重复执行 → `NS_FATAL, terminating`
   （`Log component "ApplicationContainer" has already been registered once`）。
   修复：recipe `generate()` 显式设 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG/C_FLAG = "-Wl,-soname,"`
   （仓内 accessibility/azure-core-cpp/adwaita-qt/accel-ppp 同类手法），使 NEEDED 记录裸库名、
   由运行时库路径唯一解析。

6. **cpp_info.libs 必须与产物实际库名一致**：产物名为 `libns3.48-<module>.so`，故
   `cpp_info.libs = ["ns3.48-point-to-point","ns3.48-network","ns3.48-stats","ns3.48-core"]`
   （原写 `ns3-point-to-point` 等会在 CMakeDeps 阶段报
   `Library 'ns3-point-to-point' not found in package`）。顺序按模块依赖
   （point-to-point → network → stats → core）。

7. **可选依赖全裁剪**：GSL/GTK3/SQLite3/Eigen3/libxml2 在 macros-and-definitions.cmake 中均为
   QUIET 查找，找不到只记录 REASON 并 disable，不 FATAL。libxml2 仅服务于统计输出（stats 模块），
   本轮不用。Python 绑定默认 OFF。

8. **warnings-as-errors**：默认 ON，clang15 编译 ns-3 3.48 新代码可能触发新警告导致构建失败，
   置 OFF（如实记录于 manifest）。

9. **HMDFS 注意**：修改源码后需 sleep 15-30s 再编译（写读延迟）。

## 测试

- 上游 test.py：需 `NS3_TESTS=ON` 生成测试二进制，本适配按编译目标最小化裁剪（NS3_TESTS=OFF），
  测试二进制不编入产物（与 MANIFEST.yml 声明一致）。为核验适配正确性，离线以**相同源码 + 4 个补丁 +
  ohos-aarch64 工具链**启用 `NS3_TESTS=ON` 构建后逐套件运行 test-runner：启用模块共 **52 个测试套件**，
  **51/51 计入用例全部通过**；另有 1 个 example-as-test（core-fatal-command-line-duplicate-option）
  依赖 examples 构建与 `./ns3` 包装脚本，本适配裁剪、不计入用例数。
- 适配后测试：test_package 消费者冒烟 1 项（2 节点 point-to-point 发 100B 包，断言接收 1 包
  且事件循环真实推进；ctest 1/1 + 直接运行 rc=0），由 `conan create` 自动执行。

## 预留

- 若后续需要统计输出，可 `-DNS3_SQLITE=ON -DNS3_EIGEN=ON` 或引入 libxml2，配方已留接口。
- 若需上游测试随包构建，可 `-DNS3_TESTS=ON`（examples 亦需开启），配方已留接口。

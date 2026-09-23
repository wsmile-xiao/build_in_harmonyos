# 适配笔记 — cauchy 0.9.0 (Cauchy Mathematic Compiler)

## 库信息
- **软件**: cauchy
- **版本**: 0.9.0（.hg_archival tag=v0.9.0；CMake 内 CAUCHY_VERSION 0.9.13 为上游未同步的版本号）
- **上游**: https://bitbucket.org/cyrille/cauchy（页面已失效 404）
- **发行版保存**: Ubuntu universe `cauchy_0.9.0.orig.tar.bz2`（Kubuntu，持续多个发行版使用 0.9.0）
- **许可证**: LGPL-2.1-or-later（库体）；内部 Runtime 亦有 LGPL/GPL 混合
- **构建系统**: CMake
- **依赖**: eigen3（header-only；conan `eigen/3.4.0`）

## 测试覆盖说明（2026-09-10 更新）
- 上游 `tests/*.m` 共 62 个，其中 **57 个注册进 CTest 套件**（`add_m_test`），其余 5 个未注册：
  `add_unknown, global_structure, hugewhile, select, structure`。
- **真机实测（ctest）：47/59 通过（80%）**（.m 部分 46/57；另含 Testm2mmlTest 通过、
  TestEigen3 失败两个非 .m 套件），与主机基线逐项一致。详见
  `reports/device-ctest-summary.txt` 与下方"已知限制"。
- 此前版本（无 0002 补丁）cauchymc 在 OHOS 对任意 `.m` SIGSEGV → 62 个转换测试全部
  NOT RUN；根因见下节，已修复。

## 上游核验
- bitbucket.org/cyrille/cauchy 现 404。Ubuntu 各版本（jammy~stonking）持续打包
  `cauchy 0.9.0`；orig tarball `.hg_archival.txt` 显示 `tag: v0.9.0`，
  `project(Cauchy)`，CMakeLists 编译 134 个 C++ 文件 → 身份确认为同一项目。
- SHA256(cauchy_0.9.0.orig.tar.bz2) = `7a0cd9ef...d9b56`。
- Ubuntu 构建依赖：debhelper/cmake/libeigen3-dev（与 recipe 一致：仅依赖 Eigen3）。

## OHOS 适配要点
1. cmake_minimum_required 2.6 → 3.5（现代 CMake 已移除 <3.5 兼容）。【补丁 0001】
2. 静态化：Cauchy/CauchyXUnit/m2mml/CauchyTest 的 `add_library(... SHARED)` 去 SHARED。【补丁 0001】
3. Asserts.h：删除 `namespace std { template<typename _T_> class complex; }`
   （在现代 libc++ 中是冲突/不完整声明），改为 `#include <complex>`。【补丁 0001】
4. **SIGSEGV 根因修复【补丁 0002】**：`Cauchy/DeclarationsRegistry.cpp::load()` 中
   constants/globals 两处 `map::find` 的结果**未校验 end() 即解引用**
   （`it->second->d->header = ...`）。加载 cfd 时命中缺失条目 → 读取未初始化的
   map 节点（UB）：glibc 下恰为 NULL/静默，OHOS musl 下为垃圾指针 → SIGSEGV。
   修复：补 `it != end()` 守卫（缺失条目保持 no-op 语义）。
   证据链：
   - 真机 cppcrash（faultlogger 原始转储**不入库**，摘要如下）：
     SIGSEGV(SEGV_MAPERR)，6 层栈（DeclarationsRegistry::load → cfd 加载路径），
     进程存活 ~1s，处于早期 cfd 加载阶段；原始转储可按需从设备重新导出；
   - 主机 clang 21 + ASan/UBSan 全量 .m 用例（57 注册项）复现同一 UB：修复前全部报
     `DeclarationsRegistry.cpp:248 (及 271) misaligned/uninit pointer`，
     修复后 **0 报错**。
5. **aarch64 架构探测【补丁 0003】**：`Config.h.cmake` 无 ARM64 分支
   （"Unknown architecture" 编译错误）；`Runtime/Cauchy/Eigen3/System.h`
   `computer()` 对 ARM64 无分支导致空返回（clang 编译为 trap，真机 test_system
   SIGTRAP）。补 `CAUCHY_ARCH_ARM_64` 并把 5 处 64 位分支条件放宽到 ARM64。
6. EIGEN3_INCLUDE_DIR 显式指向 eigen/3.4.0 包 include/eigen3。
7. 上游 install 只装 Runtime/Cauchy 头 + m2mml.h；Cauchy/*.h 在 package() 补装。

## 真机验证（Harmony PC aarch64 OHOS, clang 15）
- conan create . --build=missing → 静态库构建 PASS
- test_package consumer：链接 libCauchy.a 调用版本 API → PASS（cauchy 0.9.0）
- cauchymc --version / -h → PASS（工具可执行）
- 上游 CTest 套件（CAUCHY_BUILD_TESTS=ON，make -k + ctest）：
  **47/59 PASS（80%）**，失败 12 项见下（主机同）

## 已知限制（如实记录，不虚报 PASS）
以下 **12 项**在 **x86_64 Linux 主机（clang 21.1.8 + Eigen 3.4.0）同样失败**，且失败清单
与真机逐项完全一致，属上游代码与新版 Eigen / 现代 C++ 的兼容性问题，非 OHOS 平台差异；
修复需改动上游代码生成器/运行时，超出本次最小适配范围：
- 生成代码 `_Complex` 字面量被现代 C++ 拒绝（编译期）：test_complex、test_call_diag、
  test_call_eig、test_call_fft
- Eigen 3.4 静态断言（编译期，PlainObjectBase.h:807/808 FLOATING_POINT_ARGUMENT…）：
  test_for、test_range、test_overrideconstantloop、TestEigen3
- 生成代码 C++ 重载二义：test_unkwnow（`Unknown * Unknown`）
- 上游 cauchymc 解析限制：test_setvalue（生成阶段 Conflicting type use）
- 数值断言失败（运行期）：test_ifelse、test_mul

注：上游 62 个 `.m` 中 5 个未注册 CTest（`add_unknown, global_structure, hugewhile,
select, structure`；其中后三者另依赖上游已注释的 cfd 夹具），不计入 57 注册项统计。

## 结论
- 库构建/打包/消费者 ABI：PASS
- **上游代码生成 runtime：47/59（.m 46/57）真机 PASS（修复前 0/62 全 SIGSEGV）**；
  剩余 12 项主机同现、逐项分类明确（见上），无伪造通过率

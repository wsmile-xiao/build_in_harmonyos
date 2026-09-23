# svector 1.4.0 适配笔记

## 软件信息
- 软件：svector 1.4.0（上游 martinus/svector，MIT）
- 定位：紧凑 SVO（small vector optimization）优化的 C++17 vector，单头文件库
- 构建系统：CMake 仅用于安装（INTERFACE target）；上游测试由 meson 驱动（wrap 拉取 doctest/fmt）
- 任务号：#5460（活动：开源鸿蒙PC专项积分赛-依赖）；分支 feat/svector-1.4.0；worktree ~/qzy/svector

## W0/W0b
- W0 preflight：PASS（conanfile 无依赖；header-only）
- W0b：本仓库无 svector 历史归档；lang-preflight PASS（cpp↔cpp；CMakeLists.txt project，55 源文件 cpp 占比 89%）
- recipe-search：无相似配方；采用仓库 v12.21 headeronly 模板 + 已合入 frozen 1.1.1 的 header-only 先例

## 源码检查（上游 v1.4.0 tarball，SHA256 b340399e1b6205d3cfc413b245fde2b5bbc6938b88a12ebf6daf4dc9f98ddccf）
- 单头文件 include/ankerl/svector.h；CMake INTERFACE 安装 include/ 与 cmake config
- 风险点（排除）：无编译步骤 → 无交叉编译补丁需求；patches 为空
- 上游测试依赖 doctest 2.5.3 与 fmt 11.2.0（均为 wrap 网络拉取，未内嵌）

## 上游测试统计与执行（R51）
- 静态清点：test/unit/ 共 34 个文件，其中 30 个含 TEST_CASE，合计 133 个 TEST_CASE；4 个文件为纯辅助
- 实际执行（设备直编方案，绕开 meson 的网络 wrap 拉取）：
  每个 TU 以 `clang++ -std=c++17 -DDOCTEST_CONFIG_IMPLEMENT_WITH_MAIN` 编译，链接辅助对象
  Counter.cpp、fuzz/api.cpp、app/ui/Periodic.cpp、app/ui/ProgressBar.cpp 及 fmt 的 format.cc/os.cc 目标文件；
  30/30 个 TU 全部编译运行成功，doctest 全部报告 SUCCESS：133/133 用例执行通过，0 失败 0 跳过
- 记录：~/tmp/uc2/svector/upstream_tests.log（PASS 行含每 TU doctest 汇总）

## 适配后测试（消费者，test_package）
- test_svector.cpp：16 项 CHECK 断言，覆盖 SVO 内联路径、堆增长、erase、非平凡元素（std::string）
- test.sh：对编译出的消费者二进制执行 E077 四步签名后运行（设备强制签名）
- conan create（G2）内全部通过

## OHOS 平台要点
- 测试期自行编译的二进制同样必须签名（E077）；binary-sign-tool 调用时剔除 LD_LIBRARY_PATH
  （防止 Conan 环境的工具链 libc++ 遮蔽系统 OHOS libc++ 的 std::__h 符号）

## 验证记录
- conan-verify（2026-09-06）：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（reports/conan-verify-report.md）；
  G2 干净构建含 test_package 消费者测试 16/16 断言通过
- G2 知识图谱命中 E540（shadow-ci/runner-path-prepend，仅环境提示，非本配方缺陷）
- status：built（上传发布须等合并后 release 流水线）
---

**编译结束**: 2026-09-06 10:28
**最终状态**: built

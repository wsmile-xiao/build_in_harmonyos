# catch 1.12.2 适配笔记

## 软件信息
- 软件：catch 1.12.2（上游 catchorg/Catch2 tag v1.12.2，经典 1.x 单头文件线，BSL-1.0）
- 定位：C++ 原生 header-only 单元测试/TDD/BDD 框架
- 构建系统：上游 CMake 仅服务于自测（CatchSelfTest 工程）；分发包本身 header-only
- 任务号：#6212（活动：开源鸿蒙PC专项积分赛）；分支 feat/catch-1.12.2；worktree ~/qzy/catch

## W0/W0b
- W0 preflight：PASS（零依赖，header-only）
- W0b：本仓库无 catch 历史归档（catch2/2.13.10-r0 为不同包名，已合入，作为同类框架先例参照）；
  lang-preflight 首跑因传入错误 src 路径（Catch2-1.12.2，不存在）误写 env_unsupported 终态，
  已用正确路径（catch-1.12.2.work）重跑 PASS（cpp↔cpp，109/126 cpp 占比 87%），
  误判终态已按 §12.7 口径用 result --force 覆盖为 partial
- recipe-search：无 catch 相似配方；配方镜像已合入 catch2/2.13.10-r0（header-library 模式）

## 源码检查（上游 v1.12.2 tarball，SHA256 27bf01d20692e534a8963f96c6ca797df2b4ba6551db0379510c376558d75e3c）
- 单头文件 single_include/catch.hpp；231 个树条目（含 docs/projects/SelfTest 等）
- 无编译产物 → 无交叉编译补丁需求；patches 为空
- 上游自带 conanfile.py（Conan 1.x API，header_only()），本次以 Conan 2 语法重写并保持包名小写 catch

## 上游测试统计与执行（R51）
- 静态清点：projects/SelfTest 的 23 个 `.cpp` 合计 191 个真实注册入口。
  细分为 180 TEST_CASE、2 TEST_CASE_METHOD、2 CATCH_TEST_CASE、3 SCENARIO、1 SCENARIO_METHOD、2 METHOD_AS_TEST_CASE、1 REGISTER_TEST_CASE；统计包含条件编译分支和手动注册入口。
- 实际执行（设备 CMake 构建 SelfTest 目标后签名运行）：
  - CMake 4.1.2 拒绝 cmake_minimum_required(3.0) → 以官方开关 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 配置通过
    （仅用于自测构建，不改上游源码，配方不使用）
  - 默认配置二进制注册并执行 111 用例（静态 191 与执行 111 的差异为 80 个按 C++ 标准版本/特性宏条件未进入该二进制的声明）
  - 运行结果：test cases 111 | 109 passed | 2 failed as expected；
    assertions 853 | 850 passed | 3 failed as expected；退出码 0
  - "failed as expected" 为上游自带的失败路径自测（框架故意验证失败报告机制），属预期行为
- 记录：~/tmp/uc2/catch/selftest_build.log、selftest_run.txt

## 适配后测试（消费者，test_package）
- test_catch.cpp：CATCH_CONFIG_MAIN + 2 个 TEST_CASE（含 SECTION 与 Approx），真实调用框架宏；
  运行器实际输出 "All tests passed (9 assertions in 2 test cases)"
- CMakeLists.txt：find_package(Catch) + Catch::Catch（cmake_file_name/cmake_target_name 已在配方声明）
- run_check.sh：运行签名后的二进制并 grep "All tests passed"（断言运行器汇总）
- conan create（G2）内全部通过；消费者二进制按 E077 四步签名（工具缺失环境降级为直接运行）

## OHOS 平台要点
- 测试期自行编译的二进制必须签名（E077）；binary-sign-tool 调用剔除 LD_LIBRARY_PATH
- cmake_layout 下 test() 的 CWD 是构建目录：引用源码目录内脚本必须用 __file__ 绝对路径推导

## 验证记录
- conan-verify（2026-09-06）：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（reports/conan-verify-report.md）
- status：built（上传发布须等合并后 release 流水线）
---

**编译结束**: 2026-09-06 02:41
**最终状态**: built

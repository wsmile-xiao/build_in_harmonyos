# kcp 2.1.1 — OHOS 适配笔记

## 源码核对

- 上游：https://github.com/skywind3000/kcp
- 版本标签：`2.1.1`（GitHub 标签不带 `v` 前缀）
- 源码归档：`https://github.com/skywind3000/kcp/archive/refs/tags/2.1.1.tar.gz`
- SHA-256：`54d3c80928d206529f67cba6f96f2c98007182b46e3112819b200d914f96e425`
- 许可证：MIT

## 构建方案

上游使用 CMake，项目只声明 C 语言；开启 `BUILD_TESTING` 后再启用 C++
并生成 `kcp_test`。recipe 通过 `CMakeToolchain` 传递 shared/fPIC、安装目录和
测试开关，`package()` 使用上游 install 规则安装 `ikcp.h`、`libkcp` 和 CMake
导出目标，并补充许可证文件。

配方构建阶段在目标可运行时直接执行上游 `kcp_test`。该测试包含三个网络延迟
模拟场景；test_package 则从消费者视角链接 `kcp::kcp`，以双端内存队列验证分片
发送和重组。

CI #43345 暴露了上游测试在 OHOS worker 上的自动化问题：`LatencySimulator` 使用
平台相关的 `rand()` 生成丢包/延迟序列，默认模式在一个包进入 `dead_link` 后没有
终止条件，最终被 CI 外层 14400 秒超时杀死；测试末尾的 `scanf` 也不适合非交互
构建。配方通过 `patches/0001-stabilize-upstream-test.patch` 只修改测试代码：
保留三种模式和 10% 往返丢包口径，改用跨 libc 一致的周期序列，增加每模式 120
秒上限，并移除交互等待；库源码和安装内容不变。

## 平台判断

`ikcp.c`/`ikcp.h` 仅依赖标准 C、内存分配和时间/系统类型头文件；OHOS clang
命中上游的 GNU 编译器分支，不需要平台宏补丁。上游 CMakeLists 的最低版本为
4.0，设备侧应以现场 CMake 版本和配置日志为准。

## 当前验证状态

设备验证已完成以下事实核对：设备 Python 3.12.8、Conan 2.29.1、CMake 4.1.2；
官方源码归档 SHA-256 校验通过；原生 CMake 构建通过；上游 `kcp_test` 的
default、normal、fast 三个场景为 3/3；Conan G0–G4、L2、L4、L5 通过；
test_package 以设备 Conan 真实编译并运行，13 条消费者断言通过；W3 本地 CI
模拟通过。

finish 的内嵌 G0 预检因 CMake 配方没有原始 tarball 而不适用，归档校验和仓库级
知识完整性检查还会报告既有仓库缺口；这些属于统一工作流登记的 finish 白名单，
不改变本包的 Conan/W3 结果。finish 产生的跟踪文件仅作为设备端副作用证据，已在
设备任务步骤内捕获并恢复，未作为 PR 内容带回。

---

**编译结束**: 2026-09-09
**最终状态**: built

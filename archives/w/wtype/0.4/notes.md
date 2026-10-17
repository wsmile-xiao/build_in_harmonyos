# wtype 0.4 HarmonyOS PC 适配记录

## 上游与归档

- 上游：<https://github.com/atx/wtype>，标签 `v0.4`
- 源码归档：GitHub 官方源码包，SHA-256 `da91786d828b6a6e29b884bc510473939eda052658ebef87d7bdeafa6a8746f9`
- Conan 依赖：`wayland/1.24.0`、`libxkbcommon/1.8.0`
- 构建：Meson；命令行工具包安装到 `bin/wtype`

## HarmonyOS 构建处理

wtype 自带 `virtual-keyboard-unstable-v1.xml`，但 Meson 在构建时调用
`wayland-scanner` 生成协议 C 代码和头文件。仓库中 `wayland/1.24.0` 的
scanner 动态链接 Conan 缓存内的库，在 OHOS 构建沙箱不能运行；因此按
`wayland-protocols/1.47` 的已验证方案，从官方 Wayland 1.24.0 源码构建静态
scanner，再用它配置和构建 wtype。扫描器使用设备提供的静态 Expat。

应用依赖设为静态链接，避免运行时从 Conan 缓存加载共享对象。

## 测试盘点

上游 v0.4 发布归档没有 `tests/` 目录，也没有 Meson test target。配方实际执行
`meson test`，Meson 返回 `No tests defined.`（上游用例数 0）。HarmonyOS 的执行沙箱允许在 Conan build
目录直接启动 wtype，但拒绝从 package folder 或用户临时目录执行该 ELF
（`Operation not permitted`）。因此消费者测试检查安装产物是可执行的 AArch64
ELF、仅依赖系统 `libc.so` 且没有 Conan-cache RPATH；另外在设备允许执行的
Conan build 目录运行 wtype，验证未知 keysym 在 Wayland 连接前被拒绝。

HarmonyOS 6.0 ARM64 真机 Conan `create` 和消费者测试已通过；消费者测试 9 项断言通过。
依赖构建时，`libxkbcommon/1.8.0` 上游 20 项测试中 19 项通过，`context` 在
沙箱中 SIGSEGV。其现有 Conan 配方将该项记录为环境限制并继续打包。

这项设备测试验证构建产物的解析行为和打包文件的架构/依赖元数据；它不代表
从安装目录直接启动已通过，也不验证实际按键注入。

设备没有 Wayland socket，因此此次验收覆盖构建、打包和二进制/参数解析兼容；
实际键盘注入需要具备 virtual-keyboard 协议的 Wayland compositor。

## 验证结果

2026-09-26 在 HarmonyOS 6.0 ARM64 真机上通过仓库 Conan 配方验证（G1–G4）、`conan create` 消费者测试和 W3 本地 CI；W3 自动结果为 `exit_code=0`，完整日志与校验值保存在 `reports/`。消费者测试的 9 项断言通过，其中包含 HarmonyOS ARM64 ELF/运行环境检查，以及未知 keysym 在 Wayland 连接前被拒绝的测试。上游没有 Meson 测试目标，`meson test` 报告 `No tests defined.`。

设备没有 Wayland compositor/socket，因此没有验证真实按键注入。完整 `finish` 流程仍提示归档打包物与 staging 验证标记缺失，且隔离执行时知识图谱校验报告既有缺项；这些不改变 W3/Conan 测试结果，也不代表归档已达到 PR 提交就绪状态。
---

**编译结束**: 2026-09-26 14:58
**最终状态**: built

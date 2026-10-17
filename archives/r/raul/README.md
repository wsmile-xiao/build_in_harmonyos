# raul

Raul（Real-time Audio Utility Library）是 David Robillard 开发的实时音频工具库，
LV2 生态中 Ingen、Patchage 等程序的公共基础依赖。2.0.0 起为纯头文件 C++17 库，
提供实时安全的基础设施：无锁环形缓冲（RingBuffer）、计数信号量（Semaphore）、
原子双缓冲（DoubleBuffer）、实时安全延迟回收（Maid/managed_ptr）、LV2/OSC 风格
的受限标识符与路径（Symbol/Path）、数组容器（Array）、UNIX/TCP 套接字封装
（Socket）与子进程启动（Process）。

- 官网/仓库: https://gitlab.com/drobilla/raul
- 许可证: GPL-3.0-or-later（.reuse/dep5 元数据为 CC0-1.0）
- 构建系统: Meson

## OHOS 适配要点

- 纯头文件库：上游 Meson 无库目标，仅安装头文件（`include/raul-2/raul/*.hpp`）
  与 pkg-config（`raul-2.pc`）；Conan 配方以 `package_type = "header-library"`
  打包，`tool_requires("meson/1.11.0")` 驱动上游构建系统。
- OHOS 适配版 Conan 的 MesonToolchain 将 `os=OHOS` 自动映射为
  `system=harmonyos`（conan/tools/meson/helpers.py），无需手写 cross file。
- 平台差异：OHOS 安全策略拒绝 AF_UNIX bind（`/tmp` 只读 EROFS，可写目录亦
  EPERM；TCP 回环正常），上游 `socket_test` 的 UNIX 用例不可执行。补丁 0001 在
  bind 因平台策略失败时按 meson 约定以退出码 77 跳过（SKIP），其他 errno 仍失败。
- 上游 11 个测试（10 个单元测试 + 头文件自包含检查）在 `conan create` 中经
  `meson test` 真机执行。

## 依赖关系

- 编译依赖：无第三方依赖（仅系统 pthread/threads）
- 运行依赖：无
- 构建工具：meson/1.11.0（Conan 制品仓，OHOS aarch64 二进制）

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 2.0.0 | built | 首次适配；上游 11 个 Meson 测试真机执行，test_package 40 项消费者断言 |

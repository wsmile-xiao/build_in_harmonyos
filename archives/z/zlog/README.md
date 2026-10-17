# zlog

可靠、高性能、线程安全、配置灵活的纯 C 日志库，HarmonyOS PC 适配归档。

- 上游：https://github.com/HardySimpson/zlog
- 许可证：Apache-2.0
- 构建：CMake（配方 `archives/z/zlog/1.2.18/conanfile.py`）
- 能力：分级日志（DEBUG~FATAL）、多分类（category）、格式模板、按大小/日期滚动（rotater）、线程安全、
  轻量 MDC/级别过滤，附 `zlog-chk-conf` 配置校验工具；产物 `libzlog.so` / `libzlog.a` / `include/zlog.h`

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.2.18 | built | 2026-09-08 | OHOS aarch64，Conan 配方收敛为官方归档来源（ARCHIVE-SPEC v3.0） |

## OHOS 适配要点

- 上游 `CMakeLists.txt` 为 `cmake_minimum_required(VERSION 2.8.5)`，CMake ≥ 3.27 已移除 2.x 兼容；
  配方在 `generate()` 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，补丁同步抬升最低版本。
- 上游 `src/version.h` 内部版本字符串与 tag 不同步（tag 1.2.18 而 version.h 为 1.2.12）；
  补丁 `0001-fix-ohos-build.patch` 将版本字符串同步为 1.2.18。
- 源码由配方从官方归档（`source_tarball_url`）获取并校验 SHA-256，不向仓库提交上游源码树。
- 链接 `pthread` 与 `m`（OHOS/Linux/FreeBSD）。

## 依赖关系

- 编译依赖：无第三方 Conan 依赖（纯 C，仅依赖 CMake 工具链与 POSIX 线程）。
- 运行依赖：libc / libm / libpthread。

## 参考资料

- 官网/仓库：https://github.com/HardySimpson/zlog
- 使用指南：`doc/UsersGuide-EN.txt`（上游文档）
- 适配笔记：`archives/z/zlog/1.2.18/notes.md`

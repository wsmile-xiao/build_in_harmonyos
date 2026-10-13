# Lazarus — LCL 与命令行构建工具

Lazarus 是 Free Pascal 的 RAD 开发环境，提供 LCL 组件库与 `lazbuild` 命令行构建工具。本仓库提供可在 HarmonyOS PC（OHOS aarch64）上运行的 `lazbuild` 与 `nogui` LCL。

## 功能概述

- `lazbuild`：按 `.lpi`/`.lpk` 项目/包定义调用 FPC 构建，无 GUI 依赖（上游即以 `LCL_PLATFORM=nogui` 构建）。
- `nogui` LCL 组件库与组件单元（`components/`、`packager/` 等）。
- 配套工具：`lazres`（资源编译）、`lrstolfm`、`updatepofiles`。

## OHOS 适配要点

- FPC 3.2.2 无 `ohos` 目标，产物目标为 `aarch64-linux`；LCL 通过 `dlopen` 加载 widgetset，链接 OHOS musl `libc.so`，故为动态可执行文件。
- `tool_requires(fpc/3.2.2)`；无其它第三方依赖。
- **不交付 RAD IDE 的 GUI**：OHOS PC 无 X server（GTK/Qt 无法开显示），且 FPC 的 GTK2 绑定请求 glibc 时代 soname、OHOS GTK2 闭包不完整。

## 使用示例

~~~bash
lazbuild --version
lazbuild --lazarusdir=$PREFIX/share/lazarus myproject.lpi
~~~

在 conan 中作为构建工具链的一部分使用：

~~~python
def build_requirements(self):
    self.tool_requires("fpc/3.2.2")
    self.tool_requires("lazarus/4.8")
~~~

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|---|---|---|---|
| 4.8 | built | 2026-09-26 | lazbuild + nogui LCL；修复 FPC -Fu 顺序 / OHOS sysroot / glibc 启动 shim |

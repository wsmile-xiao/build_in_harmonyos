# FPC - Free Pascal Compiler

FPC 是开源的 Object Pascal 编译器，支持多目标平台与架构；本仓库提供可在 HarmonyOS PC（OHOS aarch64）上运行的 `fpc`。

## 功能概述

- 编译 Object Pascal / Delphi 方言程序，自带 RTL 与大量包单元（rtl / fcl / gtk2 / cairo / paszlib / chm 等）。
- 提供 `fpc` 命令行前端及 `fpcmake` / `fpcmkcfg` / `ppudump` / `fpcres` 等工具。
- 作为下游 `lazarus` 的编译工具链（`tool_requires`）使用。

## OHOS 适配要点

- FPC 3.2.2 **无原生 `ohos` 目标**，目标平台为 `aarch64-linux`；官方编译器二进制静态链接，可直接在 OHOS aarch64 运行。
- 包内 `bin/fpc` 是可重定位 shell 启动器，按自身路径设置 unit 目录，并强制 `-Aelf -Xi`（内部汇编器/链接器），不依赖宿主 GNU binutils。
- 同时交付上游 `rtl/` 源码子树，供下游 lazarus 的 `FPCDIR` 检查（Makefile 要求 `$(FPCDIR)/rtl` 存在）。

## 使用示例

~~~pascal
program HelloWorld;
begin
  WriteLn('Hello from FPC on HarmonyOS!');
end.
~~~

~~~bash
fpc hello.pas
./hello
~~~

在 conan 中作为工具链使用：

~~~python
def build_requirements(self):
    self.tool_requires("fpc/3.2.2")
~~~

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 3.2.2 | built | 2026-09-25 | 官方 aarch64-linux 发行组装 + 可重定位启动器 + rtl 源码 |

## 依赖关系

- 编译依赖：无（配方不含第三方 conan 依赖）。
- 运行依赖：无（编译器静态链接；测试产物在 `-Xi` 下静态链接）。

## 参考资料

- 官网：https://www.freepascal.org/
- 源码：https://downloads.freepascal.org/fpc/dist/3.2.2/source/

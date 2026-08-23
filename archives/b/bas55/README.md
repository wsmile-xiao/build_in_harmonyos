# bas55

bas55 是 ECMA-55 Minimal BASIC 编程语言的实现，提供解释器与行号重排
编辑器。本归档将上游 release `2.0` 打包为 `bas55/2.0`。

## 功能概述

- ECMA-55 Minimal BASIC 解释器（`bas55 prog.bas` 运行程序）
- 内置编辑器模式（无参数启动），支持行号重排
- 附带 NBS Minimal BASIC 标准测试程序集（SIEVE / HAMURABI / BAGELS 等）

## OHOS 适配要点

- 无第三方依赖，仅链接系统 libm 与 libc，二进制动态链接 libc.so
- HMDFS 适配：独立构建目录 + `/bin/sh` + `CONFIG_SHELL=/bin/sh`
- 补丁：configure 临时目录（E081/E011）、`round_to_int` 非有限值 UB、
  p124 测试按上游 p117 先例放宽为 informative 判定
- 上游 205 个测试用例在设备实测 205/205 通过

## 依赖关系

无运行时第三方依赖（GNU readline / libedit 为可选编辑增强，本适配未启用）。

## 参考资料

- Homepage: https://jorgicor.niobe.org/bas55
- 上游源码: https://github.com/jorgicor/bas55
- 适配笔记: `archives/b/bas55/2.0/notes.md`

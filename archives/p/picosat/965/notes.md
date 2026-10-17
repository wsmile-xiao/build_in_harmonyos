# picosat 965 适配笔记

## 编译环境

- 构建系统: makefile (custom configure.sh + makefile.in)
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: built
- 上游版本: 965 (VERSION 文件内容为 965)
- 源码: https://fmv.jku.at/picosat/picosat-965.tar.gz (64,386 字节)

## 编译步骤

上游不是 autotools/cmake，而是自带 `configure.sh + makefile.in`：

```bash
CC="clang" CFLAGS="-O2 -DNDEBUG -Wall -Wextra -fPIC" sh ./configure.sh
# Debug 用 sh ./configure.sh -g；shared=True 时追加 --shared
make -j1 CC="clang"
```

`configure.sh` 用 sed 把 `@CC@/@CFLAGS@/@TARGETS@` 替换进 `makefile.in` 生成小写 `makefile`；
`make` 先经 `mkconfig.sh` 生成 `config.h`，再编译 `picosat.o/version.o` 打包
`libpicosat.a`，并链接 `picosat/picomcs/picomus/picogcnf` 四个 CLI。
配方构建全部默认 TARGETS 以验证工具链可用，但只把库和头文件装包。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 无 `/bin/sh`，直接 `./configure.sh` 可能找不到解释器 | 上游 shebang 写死 `#!/bin/sh` | 一律用 `sh ./configure.sh` 显式调用，不依赖 exec 位 |
| 2 | 上游 `makefile` 用 `./mkconfig.sh` 生成 `config.h`，HMDFS 可能缺 exec 位 | 硬编码直接执行 | 构建时把 `./mkconfig.sh` 改写为 `sh ./mkconfig.sh`（纯调用方式修正，未改源码逻辑） |
| 3 | 上游 `makefile.in` 硬编码 `ar`/`ranlib`，忽略 `AR=` 传参 | 上游写法 | 依赖真机 PATH 中的工具链（与官方 CI 同源），`CC` 仍显式透传 |
| 4 | 上游无测试目录、无 check/test target | 965 确实无自带测试 | 判 `no_tests`，在 `build()` 留源码树审计日志，`test_package` 另做消费者 API 测试 |

## 源码修改

无补丁。`patches/` 目录未创建，`conandata.yml` 的 `patches` 为空。

## 依赖版本

无运行时依赖，仅需 libc。构建时仅需 POSIX sh、make、clang。

## 验证结果

本地未跑 conan（按本任务规程，真机预检由 HMBS 后台执行）。待真机返回后填写：

```bash
# 预期：conan create 通过，含以下机器证据
# HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":7,"passedCount":7}
# HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...,"discovered":0,"executed":0,...}
```

消费者测试 `test_picosat.c` 共 7 个显式检查：version 非空、两次 init 非空、
单子句 SAT 可满足、deref(1)==1、variables>=1、矛盾子句 UNSAT。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libpicosat.a | 静态库（含 shared=True 时另有 lib/libpicosat.so） |
| include/picosat.h | 公共 API 头文件 |
| licenses/LICENSE | MIT 许可证原文 |

CLI（picosat/picomcs/picomus/picogcnf）参与构建验证，未装包；
本适配聚焦库用法，故未建 `commands.json`。

## 注意事项

- 版本号沿用上游 `965`（无点分），`conan_ref` 为 `picosat/965`。
- `configure.sh` 的 `-static` 会往 CFLAGS 加 `-static`，配方不传此项以免静态链接工具链异常。
- 本地 Windows 检出上游 main 时 `archives/g/gama` 下有个带回车文件名，
  已用 sparse-checkout 排除，不影响本配方。

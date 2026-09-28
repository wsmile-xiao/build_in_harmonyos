# DRAFT-libsir-2.2.6-makefile-command-v-sh-alias-sh

> Source event: `libsir/2.2.6` OHOS runner 探索性编译（2026-09-27）。
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## 问题

libsir 上游 `sircommon.mk` 顶层用如下方式解析 shell：

```makefile
SHELL := $(shell env sh -c 'PATH="$$(command -p getconf PATH 2> /dev/null):$${PATH:-/bin:/usr/bin}" command -v sh')
```

在 OHOS runner 上，`command -v sh` 的命令替换结果为 `alias sh=sh`（环境为 `sh`
定义了别名，`command -v` 输出别名定义而非路径）。于是 make 的 `SHELL` 变量变为
`alias sh=sh`，每条 recipe 都以非法前缀执行：

```text
/bin/sh: alias: -c: invalid alias name
/bin/sh:   make --no-print-directory \: inaccessible or not found
make: *** [Makefile:564: plugins] Error 127
```

编译直接失败，且错误形态（`alias: -c: invalid alias name`）很容易被误判为
"上游 Makefile 语法问题"或"本库源码编译错误"。

## 根因

OHOS runner 环境为 `sh` 定义了别名，`command -v sh` 输出 `alias sh=sh`（别名定义）
而不是 `/bin/sh` 路径。make 的 `SHELL` 赋值直接用了该命令替换输出，导致 recipe
的 shell 前缀非法。

> 与 `DRAFT-hsdlib-0.4.1-makefile-ohos-os-branch-shebang` 区分：hsdlib 是
> 硬编码 `SHELL := /bin/bash` 且 OHOS 无该路径（`No such file or directory`）；
> 本例是 `command -v sh` 解析结果被别名污染，两条知识互补不重复。

## 解决方案

调用 make 时显式覆盖 `SHELL=/bin/sh`，绕过上游 shell 探测逻辑：

```bash
make -j1 SHELL=/bin/sh all
```

配方侧固化（conanfile.py `build()`/`package()`）：

```python
with chdir(self, self.source_folder):
    self.run("make -j1 SHELL=/bin/sh all", env="conanbuild")
```

不需要改动上游源码；若要固化修复，可给 Makefile 打最小补丁将 SHELL 替换为
`/bin/sh`（fallback）。

## 验证

- 修复前：`make -n` 输出 `alias: -c: invalid alias name`；`make -p` 显示
  `SHELL := alias sh=sh`。
- 修复后：`make -j1 SHELL=/bin/sh all` 全量构建成功（静态库 libsir_s.a、
  动态库 libsir.so、example、tests、9 个插件），上游测试 36/36 通过。

## 适用边界

- 适用：所有用 `command -v sh`（或类似 shell 探测）解析顶层 SHELL 的自定义
  Makefile 项目在 OHOS runner 上构建。
- 反例：CMake/autotools 项目不走该 SHELL 解析路径，不受影响；hsdlib 那种
  硬编码 `/bin/bash` 的问题走另一条知识（draft-hsdlib）。

## 限制

- `SHELL=/bin/sh` 覆盖是调用侧修复，若 CI/下游也直接调用 `make` 不带 SHELL，
  仍需在配方或调用方统一处理。

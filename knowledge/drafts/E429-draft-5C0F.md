# E429 — Conan 构建环境导出的 CFLAGS 遮蔽上游 Makefile 的条件赋值默认值，导致项目自带 -I 包含路径丢失

## 错误特征

编译在第一个以尖括号 + 子目录形式引用的**项目内部**头文件处失败：

```
src/server.h:7:10: error: 'hiredis/async.h' file not found with <angled> include; use "quotes" instead
#include <hiredis/async.h>
1 error generated.
make: *** [Makefile:95: src/webdis.o] Error 1
```

典型特征是：头文件明明在源码树里（`src/hiredis/async.h`），但编译器说找不到 —— 因为本该由
`-Isrc` 提供的搜索路径没有出现在编译命令行上。

## 触发条件

- 构建系统：手写/裸 Makefile（`Makefile` 内用 `CFLAGS ?=` / `CFLAGS +=` 组织默认编译参数）
- 阶段：compilation（`make` 调起 cc/clang 的第一个源文件即失败）
- 前置：recipe 通过**构建环境或 Toolchain 注入 CFLAGS**（Conan 的 `[buildenv]`/`tools.build:cflags`/Autotools
  Toolchain 都会注入），且未同时复述 Makefile 自身的默认值

## 根因分析

`CFLAGS ?= ...` 是 make 的**条件赋值**：仅当变量此前未定义时才赋值。Makefile 默认值（含项目自身的
`-Isrc`、`-Isrc/xxx` 等内部包含路径）在「环境已导出 CFLAGS」时**完全不会生效**，而环境变量里的 CFLAGS
（`-fPIC -O2` 之类）会取而代之。于是编译器只拿到基础设施的通用 flag，项目内部头文件搜索路径全部丢失。

这不是源码缺陷、也不是平台差异：同一份 Makefile 在开发者 shell（未导出 CFLAGS）下正常，在 recipe 环境下必失败，
因此在 Linux 上也一样复现。

实证（webdis 0.1.22）：
- 失败命令：`clang -c -fPIC -O2 -I<libevent> -O3 -o src/webdis.o src/webdis.c` ← 无 `-Isrc`
- 成功命令：`clang -c -std=c99 -Wall -Wextra -Isrc -Isrc/jansson/src -Isrc/http-parser … -o src/webdis.o src/webdis.c`

## 解决方案

### 推荐方案（priority 1）

在 recipe 的 `build()` 中**显式复述上游 Makefile 的默认 CFLAGS**（含全部 `-I`），再拼接 Conan 工具链与依赖
提供的 flag；不要依赖 Makefile 自身的 `?=` 默认值：

```python
upstream_cflags = "-std=c99 -Wall -Wextra -Isrc -Isrc/jansson/src -Isrc/http-parser " \
                  "-D_POSIX_C_SOURCE=200809L -Wno-pragmas -fPIC"   # 从上游 Makefile 原样抄录
cflags = " ".join(x for x in (upstream_cflags, toolchain_cflags, dep_cflags) if x)
self.run(f'make CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{ldflags}" -j1', cwd=self.source_folder)
```

同类情形：上游在 Makefile 内用 `+=` 追加的**目标文件列表**（如 `FORMAT_OBJS += xxx.o`）同样只在自己的探测
分支里生效，must-pass 时也要一并显式传入。

### 禁止做法

- ❌ 直接 sed/改写下游源码里的 `#include <subdir/header.h>` 为相对路径来绕过 `-I` 缺失 —— 掩盖根因、
  污染源码，补丁无法上游化（违反 P005）。

## 验证

```bash
# 1) 确认编译命令里缺少项目自带的 -I
make -n | grep -c -- '-Isrc'
# 2) 确认失败首行是"项目内部头文件找不到"
grep -m1 -E "file not found with <angled> include|No such file or directory" build.log
# 3) 修复后复验：同一命令应出现完整 -I 列表，且编译通过
```

## 关联条目

- 原则：P014（环境变量与构建系统语义冲突陷阱）—— 本条是该原则在「recipe 注入 CFLAGS」场景的具体形态
- 相似：E063（-Werror 与 CFLAGS/Makefile）、E021（configure 探测与 Makefile 约定）
- 来源事件：webdis/0.1.22 OHOS 适配首次 `make` 失败（`src/server.h:7` `hiredis/async.h` not found）

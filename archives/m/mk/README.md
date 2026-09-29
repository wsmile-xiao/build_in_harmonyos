# mk (mk-configure) 0.40.0 for HarmonyOS

## 概述

mk-configure 是一个构建系统，用 bmake（NetBSD make 的可移植版本）+ POSIX shell + awk 写成，
为 C/C++ 工程提供 `mkc.*.mk` / `mkc_imp.*.mk` include 库、`mkcmake` 顶层命令以及
`mkc_check_*` 系列探测工具。**它不是 C/C++ 库，自身不产出 .so/.a/可执行二进制**——
安装的是 makefile 库、POSIX shell 脚本与 man 页。

| 项目 | 值 |
|------|-----|
| 包名 | mk（上游项目名 mk-configure） |
| 版本 | 0.40.0 |
| 上游仓库 | https://github.com/cheusov/mk-configure |
| 上游 tag | `mk-configure-0.40.0` → commit `4442e64ed8486e77afa8a091182aea8583e40445` |
| 源码 | https://github.com/cheusov/mk-configure/archive/refs/tags/mk-configure-0.40.0.tar.gz |
| sha256 | `7daaa79467389cd3bb7875ad24d0e56ba460b8f6165e138eb222620caf67f903` |
| 许可证 | BSD-2-Clause |
| 分类 | build-tool |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS（HongMeng Kernel 1.12.0，aarch64，Toybox userland） |
| `uname -s` | `HarmonyOS` |
| 编译器 | clang 15.0.4（target triple `aarch64-unknown-linux-ohos`） |
| 构建系统 | make（NetBSD **bmake**；顶层命令 `mkcmake`） |

## 依赖

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| bmake | 20200710 | tool_requires + requires | 构建 mk-configure 需要 bmake；安装后的 `mkcmake` 是 bmake 的薄封装，运行期同样需要 |
| bmkdep | 20140112 | tool_requires | 提供 mkdep 变体（`mkdep`/`bmkdep`/`nbmkdep`/`makedepend` 任一即可） |
| awk | 系统自带 | 运行期 | `mkc_which` 自动探测；OHOS 上为 `/data/service/hnp/bin/awk`（GNU Awk） |

## 编译步骤

```bash
# 1. 准备 bmake（并提供 sys.mk）
conan install --requires=bmake/20200710 -r=ohpcd -g VirtualRunEnv
conan install --requires=bmkdep/20140112 -r=ohpcd

# 2. 构建（PREFIX 一旦确定必须与 install 保持一致：会被烘焙进生成脚本）
bmake all     PREFIX=<prefix>

# 3. 安装
bmake install PREFIX=<prefix>

# 4. 冒烟
PATH=<prefix>/bin:$PATH mkcmake all      # 在含 Makefile(.include <mkc.prog.mk>) 的工程目录内
```

## 鸿蒙适配要点

1. **平台识别**：`uname -s` 返回 `HarmonyOS`，`mk/mkc.init.mk` 将其规范化为 `OHOS`，
   并新增 `mk/mkc_imp.platform.OHOS.mk` 提供 `CC.OHOS/CXX.OHOS/CPP.OHOS`（OHOS 无裸 `cc/c++/cpp`）。
2. **id(1) 不可用**：设备用户库不含构建 uid，`id -un` 失败；其 stderr 会被 bmake 的 `!=`
   捕获进 make 输出，破坏 minitest 的 `expect.out` 比较 → 静默化处理。
3. **无硬链接**：HMDFS 上 `ln`（硬链接）报 `Operation not permitted`，`LINKS` 安装回退为
   同目录相对符号链接。
4. **无 chown(1)/chgrp(1)**：`/bin/sh` 只提供不可执行的别名，`mkc_install`（脚本内 `set -e`）
   在无法解析出可执行文件时跳过属主变更，否则安装静默中断、文件不落地。
5. **bmake 双角色**：既是构建工具，也是运行期依赖。

## 已知平台限制（与本包适配无关，属设备环境缺口）

- `makeinfo`（texinfo）不存在 → `tests/mkinstall`、`examples/files`、`examples/files2` 无法通过。
- `lua` 解释器与 `lua.pc` 不存在 → `tests/lua_dirs`、`examples/hello_lua*` 无法通过。
- OHOS libc 无 `fts.h`/`fts_*` → `tests/mkc_features`、`examples/fts` 无法通过。
- `libfl`（flex 运行库）不存在 → `examples/lexer` 无法通过。
- HMDFS 权限归一化（0700/0750→0770、0644→0660）→ `tests/mkc_install` 的权限断言无法成立。

## 测试

```bash
bmake all
bmake test              # = test-tests test-examples（上游 minitest：diff expect.out）
bmake test-tests/os_OHOS    # 本次新增的 OHOS 专用用例
```

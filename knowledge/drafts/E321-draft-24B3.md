# E321 — libtoolize aux-dir heuristic picks `..`/`../..` because of a stray `install.sh` in a parent dir (ltmain.sh lands in the wrong directory)

> **Contributor**: 24B3 | **Status**: DRAFT | **Created**: 2026-08-14

## 错误特征

`autoreconf -fi`（autotools 项目 bootstrap）失败，日志出现：

```text
libtoolize: putting auxiliary files in '../..'.
libtoolize: copying file '../../ltmain.sh'
...
configure.ac:19: error: required file './ltmain.sh' not found
autoreconf: error: automake failed with exit status: 1
```

`./configure` 可能已被生成，但 `ltmain.sh` 不在源码根目录，automake 报
`required file './ltmain.sh' not found`。

## 触发条件

- 构建系统: autotools（`AC_PROG_LIBTOOL` / `LT_INIT`，需要 libtoolize bootstrap）
- 阶段: configuration（`autoreconf -fi` / `./autogen.sh`）
- 触发前提：源码根目录此时还没有 `install-sh`/`install.sh`，且某个父目录
  （`.` → `..` → `../..` 的扫描路径）中存在 `install.sh`。OHOS 构建宿主
  `$HOME/tmp/install.sh`（历史包安装残留）即触发该问题。

## 根因分析

libtoolize 的辅助目录（aux dir）启发式与 Autoconf 相同：依次扫描
`. / .. / ../..`，第一个存在 `install-sh` 或 `install.sh` 的目录即被选为
aux dir（`func_require_aux_dir`）。当源码根目录尚无 `install-sh` 而
`$HOME/tmp`（= `../..`）存在 `install.sh` 时，libtoolize 把 `ltmain.sh`、
`config.guess` 等辅助文件复制到 `../..`，而非源码根目录。随后 automake
（`--add-missing`）在 `.` 找不到 `ltmain.sh` 即失败。

这与 E209（ltmain.sh 复制失败，根因为目录结构/版本不匹配）症状相似，
但根因是**父目录 `install.sh` 干扰 aux-dir 启发式**，修复方式不同。

## 解决方案

### 推荐方案
在运行 `autoreconf -fi` 前，先确保源码根目录存在 `install-sh`（或
`install.sh`），使 libtoolize 的启发式优先命中 `.`：

```bash
test -f install-sh || printf '#!/bin/sh\n' > install-sh
autoreconf -fi
```

Conan 配方在 `build()` 中、`autoreconf -fi` 之前写入占位 `install-sh`
（automake `--add-missing` 之后会覆盖/保留它，不影响构建）。abinword 系列
插件（clarisworks/pdb/t602）已采用此方案。

### 禁止做法
- ❌ 不删除宿主的 `$HOME/tmp/install.sh`（他人产物，且 /tmp 只读、跨任务污染）
- ❌ 不手工 `cp ltmain.sh .` 后继续而不理解根因（E209 的做法在此场景下
  虽可行但掩盖了启发式干扰，`config.guess`/`config.sub` 仍可能被写错目录）
- ❌ 不在 `autoreconf` 时依赖 CWD 之外的意外目录状态

## 验证
```bash
autoreconf -fi && ls ltmain.sh && test -x configure
```

## 关联条目
- 相关: E209（ltmain.sh 缺失/复制失败，不同根因）
- 相关: E114（HMDFS 目录权限导致的 configure/config.status 失败）

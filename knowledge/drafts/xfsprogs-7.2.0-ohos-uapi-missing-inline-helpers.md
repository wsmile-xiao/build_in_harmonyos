# OHOS SDK 的 UAPI 头缺 static inline 助手：以项目内 compat 头补齐

> Draft: `DRAFT-XFSPROGS-720-OHOS-UAPI-MISSING-INLINE-HELPERS`
> Stem: `xfsprogs-7.2.0-ohos-uapi-missing-inline-helpers` — 与同名 `.kv` 配套
> 实例来源: xfsprogs 7.2.0 适配（补丁 `0005-include-fsmap_compat.h.patch` + `0007/0010/0011` 调用方切换）
> 关联知识: E386（OHOS/HMDFS 构建环境差异）、E490（autotools 脚本适配）

## 基本信息

- **ID**: DRAFT-XFSPROGS-720-OHOS-UAPI-MISSING-INLINE-HELPERS
- **严重度**: 2
- **类别**: headers, kernel, ohos, portability, compat
- **触发工具**: clang|ld|make|conan
- **阶段**: linking（发现点；根因在编译期头内容差异）

## 使用说明（这份知识怎么用）

- **适用**：项目 `#include <linux/xxx.h>` 并使用该头里的 `static inline` 助手，
  在 OHOS SDK sysroot 上编译通过但链接报 `undefined symbol: <helper>`。
- **不适用**：符号缺失来自库自身（`-l` 漏链接、库裁剪）——先确认宿主头里本来有这些 inline。
- **先做三步确认**：① `clang -H -E` 找到实际使用的 sysroot 头；
  ② `grep "static inline"` 确认助手缺失；③ 编译探针复现 undefined symbol。

## 输入输出定义

- **输入**：上游 UAPI 头中缺失的 `static inline` 助手清单（函数名、签名、实现体）。
- **输出**：
  - 项目内 compat 头（单文件，含 `#include <linux/xxx.h>` + 复制的最小实现）；
  - 调用方 include 切换（只改真正使用助手的文件）；
  - 可被 `refresh-patch --auto` 生成为"新建文件补丁 + 替换行补丁"。

## 错误特征（逐字实测）

```
ld.lld: error: undefined symbol: fsmap_sizeof
>>> referenced by fsmap.c:496 (io/fsmap.c)
ld.lld: error: undefined symbol: fsmap_advance
>>> referenced by fsmap.c:563 (io/fsmap.c)
```

对照：上游 Linux UAPI `include/uapi/linux/fsmap.h` **有**：

```c
/* Size of an fsmap_head with room for nr records. */
static inline __kernel_size_t
fsmap_sizeof(unsigned int nr)
{
	return sizeof(struct fsmap_head) + nr * sizeof(struct fsmap);
}

/* Start the next fsmap query at the end of the current query results. */
static inline void
fsmap_advance(struct fsmap_head *head)
{
	head->fmh_keys[0] = head->fmh_recs[head->fmh_entries - 1];
}
```

而 OHOS SDK sysroot 的 `linux/fsmap.h`：`grep "static inline"` **无输出**。

## 根因

UAPI 头不只是结构体/宏，还常带少量 `static inline` 助手；SDK 打包时这些
"非 ABI 必需"的函数被裁掉。调用方编译期拿到的是隐式声明（或新版代码预期的
声明），最终在链接期成为 undefined symbol。

## 影响范围

- 所有使用 `<linux/*.h>` inline 助手的项目（`fsmap`、`ethtool`、`nl80211`、
  `sev-guest` 等命名空间最常见）；
- 反向风险：未来 SDK 补齐同名 inline 时，项目 compat 头会重复定义——
  须在注释标注"适用 SDK 版本"，升级时复核。

## 推荐方案

**方法**: `project-local-compat-header-for-missing-uapi-inlines`

1. 定位并确认（见"使用说明"三步）。
2. 新建 `include/<topic>_compat.h`，内容 = 上游 UAPI 头 + 缺失 inline 的**原文复制**：

```c
/* SPDX-License-Identifier: GPL-2.0 WITH Linux-syscall-note */
/*
 * OHOS SDK 的 <linux/fsmap.h> 缺少上游 UAPI 提供的 fsmap_sizeof()/
 * fsmap_advance() inline 助手；此处按 Linux include/uapi/linux/fsmap.h
 * 原文复制，供本平台构建使用。
 */
#ifndef XFS_FSMAP_COMPAT_H
#define XFS_FSMAP_COMPAT_H

#include <linux/fsmap.h>
/* ... 上游 static inline 原文 ... */
#endif
```

3. 把**真正使用助手**的调用方从 `#include <linux/fsmap.h>` 改为 `#include "fsmap_compat.h"`。
4. R8 合规要点：**不用平台宏**（无 `__OHOS__`）、**不改系统头**、
   **不写空壳 stub**（复制的是有实质逻辑的上游实现）；注释写明出处/原因/适用 SDK。
5. 交付形态：新建文件补丁 + 若干一行替换补丁（refresh-patch 可直接生成）。

## 验证命令

```bash
# 1) 找 sysroot 实际头路径
clang -H -E -xc /dev/null -include linux/fsmap.h 2>&1 | grep fsmap

# 2) 确认 inline 缺失（期望无输出）
grep -n "static inline" $SYSROOT/usr/include/linux/fsmap.h

# 3) 复现 undefined symbol（旧调用方编译链接）
# 4) 修复后：xfs_io/xfs_scrub/xfs_spaceman 链接通过；版本探针 rc=0
```

## 取证记录

- 包: xfsprogs 7.2.0（补丁 `0005` 新建 `include/fsmap_compat.h`；
  `0007-io-fsmap.c.patch`、`0010-scrub-spacemap.c.patch`、`0011-spaceman-freesp.c.patch` 切换 include）
- 报错原文: 首次 `make` 日志（`ld.lld: undefined symbol: fsmap_sizeof/fsmap_advance`）
- 上游依据: Linux `include/uapi/linux/fsmap.h`（函数原文与签名来源于此）

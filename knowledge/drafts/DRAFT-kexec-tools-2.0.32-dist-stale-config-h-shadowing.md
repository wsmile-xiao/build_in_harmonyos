# E-DRAFT: dist tarball 误带 include/config.h 开发残留——-I 顺序遮蔽 builddir 生成物，zstd.h not found

- **触发实例**：kexec-tools 2.0.32 适配（2026-09-18，分支 feat/kexec-tools-2.0.32）
- **错误签名**：`../kexec-tools-2.0.32/kexec/zstd.c:17:10: fatal error: 'zstd.h' file not found`
- **类别**：autotools/packaging/include-order（dist 残留问题域的 make 期静默变体）
- **严重度**：2（确定性编译失败，报错与真因相距两个间接层）

## 症状

configure 全绿（`checking for zstd.h... no` → `/* #undef HAVE_LIBZSTD */`），
make 编译绝大多数 .c 正常，唯独：

```text
kexec/zstd.c:17:10: fatal error: 'zstd.h' file not found
#include <zstd.h>
```

zstd.c 开头明明有 `#ifdef HAVE_LIBZSTD` 守卫——为什么没挡住？

## 根因（三层间接）

1. **tarball 里藏着开发机 config.h**：kexec-tools 2.0.32 官方 tarball 的
   `include/config.h`（2025-10-16 时间戳）带着打包机的检测结果
   `#define HAVE_LIBZSTD 1`——include/Makefile 的 dist 列表误收了它
   （config.h 是 configure 产物，本不该进 dist）。
2. **-I 顺序**：上游 Makefile 的 INCLUDES 是
   `-I$(srcdir)/include -Iinclude/`——**源码树在前**，builddir 的
   新鲜 config.h（`/* #undef HAVE_LIBZSTD */`）被遮蔽。
3. **误判展开**：zstd.c 的 `#ifdef HAVE_LIBZSTD` 命中陈旧宏 →
   `#include <zstd.h>` → 本机无 zstd 头文件 → fatal error。

## 定位技巧（从报错到真因）

```bash
# 报错行只说 zstd.h not found——先查宏来源：
grep -rn "define HAVE_LIBZSTD" <srcdir>/include/config.h   # 命中！残留实锤
grep "HAVE_LIBZSTD" <builddir>/include/config.h            # #undef——builddir 是对的
# -I 顺序确认（源码树在前=遮蔽生效）：
make -n | head -1 | tr ' ' '\n' | grep -n -- '-I'
```

## 修复

删除源码树 `include/config.h`（整文件 82 行删除补丁，portability）：

```text
patches/0004-remove-stale-include-config-h.patch
```

删除零风险：AC_CONFIG_HEADERS([include/config.h]) 会在 builddir 重新生成。

## 与既有条目的关系

- `DRAFT-autotools-tarball-in-tree-residue-vpath-configure`：同域（dist 残留）
  但那是 **config.status → configure 硬错误**（"source directory already
  configured"，configure 阶段炸）；本条是 **config.h → make 期静默语义污染**
  （configure 成功、make 才炸、报错行与真因相距两个间接层）。
- 通用性：任何 dist 列表误收 configure 产物且 srcdir include 优先的包可复用
  （判据：tarball 内 config.h 带 `#define HAVE_*` 与 builddir `#undef` 矛盾）。

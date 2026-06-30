# E099: fbida GNUmakefile 缺少 libexif 的 pkg-config 配置

> **结构化数据**: [graph/draft/E099-fbida-libexif.kv](../../graph/draft/E099-fbida-libexif.kv) | **原则**: P-PATCH-001, P-DEPENDENCY-001
> **严重度**: 🟡 warning | **分类**: build_system | **自动修复**: ✅ semi-auto

---

## 错误特征

```
exiftran.c: fatal error: libexif/exif-data.h: No such file or directory
thumbnail.cgi.c: undefined reference to `exif_data_new_from_file'
make: *** [exiftran] Error 1
```

## 根因

fbida 的 GNUmakefile 中 exiftran 和 thumbnail.cgi 目标缺少 libexif 的 pkg-config 配置：
1. libexif 库已安装，头文件和库文件都存在
2. 但 GNUmakefile 中的 exiftran 和 thumbnail.cgi 目标没有添加 libexif 的编译和链接选项
3. 需要在相应的目标规则中添加：
   - `CFLAGS += $(shell $(PKG_CONFIG) --cflags libexif)`
   - `LDLIBS += $(shell $(PKG_CONFIG) --libs libexif)`

这是 fbida 构建脚本的一个缺陷。

## 解决方案

**推荐方案**：修改 GNUmakefile

```bash
# Step 1: 备份原文件
cp GNUmakefile GNUmakefile.orig

# Step 2: 为 exiftran 目标添加 libexif 配置
# 在 GNUmakefile 中找到 exiftran 目标规则（约第 149 行），添加：
exiftran      : CFLAGS += $(shell $(PKG_CONFIG) --cflags pixman-1 libexif)
exiftran      : LDLIBS += $(shell $(PKG_CONFIG) --libs   pixman-1 libexif)

# Step 3: 为 thumbnail.cgi 目标也添加 libexif 配置
thumbnail.cgi : CFLAGS += $(shell $(PKG_CONFIG) --cflags libexif)
thumbnail.cgi : LDLIBS += $(shell $(PKG_CONFIG) --libs   libexif)

# Step 4: 验证修改
grep -A2 "exiftran:" GNUmakefile | grep libexif
```

**备选方案**：使用环境变量

```bash
export CFLAGS="-I/usr/local/include $(pkg-config --cflags libexif)"
export LDFLAGS="-L/usr/local/lib $(pkg-config --libs libexif)"
make exiftran
```

## 补丁示例

```patch
--- a/GNUmakefile
+++ b/GNUmakefile
@@ -149,8 +149,8 @@
 exiftran      : CFLAGS  += $(shell $(PKG_CONFIG) --cflags pixman-1)
 exiftran      : LDLIBS  += $(shell $(PKG_CONFIG) --libs   pixman-1)
-exiftran      : LDLIBS  += -ljpeg -lexif -lm
+exiftran      : CFLAGS  += $(shell $(PKG_CONFIG) --cflags libexif)
+exiftran      : LDLIBS  += $(shell $(PKG_CONFIG) --libs   libexif) -ljpeg -lm
```

## 验证命令

```bash
# 检查 libexif 是否安装
pkg-config --exists libexif && echo "libexif found"

# 检查头文件路径
pkg-config --cflags libexif
# 输出: -I/usr/local/include

# 检查库文件路径
pkg-config --libs libexif
# 输出: -L/usr/local/lib -lexif

# 查看编译错误
make exiftran 2>&1 | grep "exif-data.h"
```

## 涉及软件

fbida 2.14 及相关版本、所有编译 exiftran 和 thumbnail.cgi 的项目。

## 相关模式

- [E006](E006.md) — 依赖版本不匹配
- [E008](E008.md) — 缺少库链接
- [E097](E097-fbida-autoconf.md) — fbida 自定义 autoconf 系统（前置原因）

---
*doc/draft/E099-fbida-libexif.md · knowledge graph v2 · 2026-06-12*
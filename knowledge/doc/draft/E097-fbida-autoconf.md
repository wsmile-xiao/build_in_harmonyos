# E097: fbida 使用自定义 autoconf 系统（非标准 autotools）

> **结构化数据**: [graph/draft/E097-fbida-autoconf.kv](../../graph/draft/E097-fbida-autoconf.kv) | **原则**: P-BUILD-001, P-PORTABILITY-001
> **严重度**: 🟡 warning | **分类**: build_system | **自动修复**: ❌ manual

---

## 错误特征

```
make: *** No rule to make target 'configure'
GNUmakefile: include mk/Autoconf.mk
make: mk/Autoconf.mk: No such file or directory
make config needed
```

## 根因

fbida 使用自定义的 autoconf 系统（mk/Autoconf.mk），不是标准的 autotools：
1. 没有 ./configure 脚本，而是使用 GNUmakefile 和 mk/Autoconf.mk
2. 配置命令是 `make config`，而不是 `./configure`
3. 配置过程通过 scripts/ 目录下的脚本完成

这是 fbida 项目特有的构建方式，需要按照其文档进行配置。

## 解决方案

**推荐方案**：使用 fbida 标准的配置命令

```bash
# Step 1: 运行配置
make config

# Step 2: 检查生成的配置
cat Make.config

# Step 3: 如需修改，设置环境变量
export HAVE_LINUX_FB_H=no
make config
```

**备选方案**：手动创建 Make.config

```bash
cat > Make.config << 'EOF'
RESOURCES := /usr/share/fbida
JPEG_VER := 62
HAVE_LINUX_FB_H := no
HAVE_MOTIF := no
HAVE_LIBSANE := no
HAVE_GLIBC := yes
EOF
```

## 验证命令

```bash
# 检查是否有 configure 脚本
ls -la configure 2>&1
# 输出: No such file (不存在)

# 检查构建系统
head -20 GNUmakefile | grep -i autoconf
# 输出: include mk/Autoconf.mk

# 检查配置命令
grep -r "make config" README 2>&1 | head -5
```

## 涉及软件

fbida 及其衍生项目、所有使用类似自定义 autoconf 系统的项目。

## 相关模式

- [E004](E004.md) — 非标准构建系统
- [E005](E005.md) — 缺少 Makefile
- [E098](E098-fbida-jpeg-ver.md) — JPEG_VER 版本检测失败（前置依赖）
- [E099](E099-fbida-libexif.md) — GNUmakefile 缺少 libexif 配置（前置依赖）

---
*doc/draft/E097-fbida-autoconf.md · knowledge graph v2 · 2026-06-12*
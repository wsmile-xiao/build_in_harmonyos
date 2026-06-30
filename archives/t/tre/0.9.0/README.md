# TRE 0.9.0 — 鸿蒙 (OpenHarmony) aarch64 预编译包

## 软件简介

TRE 是一个轻量级、兼容 POSIX 的正则表达式库，支持：
- **精确匹配**: 标准 BRE/ERE 正则语法
- **近似匹配**: 允许指定编辑错误数量的模糊搜索（tre 独有特性）
- **宽字符支持**: wchar_t/wint_t 多字节字符处理
- **agrep 工具**: 类 grep 的命令行搜索工具，支持近似匹配

**上游主页**: https://laurikari.net/tre/
**许可证**: BSD-style (2-clause)

## 版本信息

- 软件版本: 0.9.0
- 构建日期: 2026-05-26
- 目标平台: OpenHarmony / HarmonyOS (aarch64)
- 编译器: clang 15.0.4
- 构建系统: autotools（需 autoreconf -fi）
- 状态: 已发布 (published)

## 构建方法

tre-0.9.0 的源码 tarball **不包含预生成的 configure 脚本**，需要 autoreconf 步骤。完整构建流程：

```bash
# 1. 解压源码
tar xzf tre-0.9.0.tar.gz && cd tre-0.9.0

# 2. 应用源码补丁（移除 NLS、禁用 gettext）
patch -p1 < 0001-Makefile.am-remove-po.patch
patch -p1 < 0002-configure.ac-disable-nls.patch

# 3. 重新生成构建系统文件
autoreconf -fi

# 4. 修复 HMDFS 兼容性问题（umask 和临时目录）
sed -i 's/umask 077/umask 022/g' configure
sed -i 's|mktemp -d "./confXXXXXX"|mktemp -d "$TMPDIR/confXXXXXX"|g' configure

# 5. 配置、编译、安装
./configure --prefix=/storage/Users/currentUser/usr/local CC=clang CXX=clang++
make -j1
make install
```

详细重建步骤见 `rebuild_hints.yaml`。

## 产物清单

### 预编译包

| 文件名 | 大小 | 内容 |
|--------|------|------|
| `tre-0.9.0-ohos-aarch64.tar.gz` | 364KB | agrep + libtre.so.5 + 头文件 + tre.pc |
| `tre-0.9.0-ohos-aarch64-debug.tar.gz` | 166KB | 调试符号 |

### 安装内容

```
bin/agrep             — 命令行搜索工具 (35264 字节)
lib/libtre.so.5.0.0   — 共享库 (76160 字节)
lib/libtre.so.5       → libtre.so.5.0.0 (符号链接)
lib/libtre.so         → libtre.so.5.0.0 (符号链接)
lib/pkgconfig/tre.pc  — pkg-config 元数据
include/tre/tre.h     — TRE 主头文件
include/tre/regex.h   — POSIX regex.h 兼容头文件
include/tre/tre-config.h — 配置头文件
```

### 补丁文件 (6个)

| 序号 | 文件 | 说明 |
|------|------|------|
| 0001 | Makefile.am.patch | 移除 po 从 SUBDIRS |
| 0002 | Makefile.in.patch | autoreconf 重新生成（移除 po） |
| 0003 | config.h.in.patch | autoreconf 重新生成 |
| 0004 | configure.patch | autoreconf 重新生成 + umask/mktemp 修复 |
| 0005 | configure.ac.patch | 禁用 AM_GNU_GETTEXT，添加 NLS stubs |
| 0006 | configure~.patch | 原始 configure 备份 |

## 测试结果

### 自动化测试 (make check)

| 测试套件 | 结果 | 详情 |
|----------|------|------|
| agrep | ✅ 通过 | 1/1 |
| retest | ✅ 通过 | 全部正则测试 |
| test-str-source | ✅ 通过 | 全部 |
| wretest | ⚠️ 部分失败 | 4/53447 (0.0075%)，OHOS locale 限制 |

### 手动功能验证

- **agrep**: 8 项测试全部通过（精确/正则/近似/反向/大小写）
- **libtre API**: 4 项测试全部通过（基本正则/分组捕获/大小写/中文）
- **pkg-config**: 版本号和路径正确

## 已知限制

1. **wretest locale 限制**: OHOS 缺少 en_US.ISO-8859-1 和 ja_JP.eucJP locale，
   导致宽字符多字节编码测试 4/53447 失败。不影响核心正则功能。
2. **G0 自动干净构建验证**: tarball 无 configure 脚本，
   G0 自动验证无法运行 autoreconf 步骤，需手动验证。
   已记录在 rebuild_hints.yaml，手动验证通过。
3. **tre.h 与系统 regex.h 冲突**: 同时包含 tre/tre.h 和系统 regex.h 会导致类型重定义。
   建议通过 POSIX regex API（系统 regex.h）或单独使用 tre/tre.h。

## 知识沉淀

5 条关键知识已记录在 manifest.yaml 的 knowledge_gained 字段：
- HMDFS umask 077 权限问题 (ref:E097)
- autotools NLS 禁用方案 (ref:E097)
- dnl 在 AC_CONFIG_FILES 内非注释 (ref:local)
- wretest locale 限制 (ref:E099)
- tarball 缺 configure 需 autoreconf (ref:E097)
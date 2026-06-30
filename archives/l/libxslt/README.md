# libxslt

## 简介

libxslt 是 GNOME 项目开发的 XSLT 1.0 标准 C 语言实现库，用于 XML 文档转换。它是 libxml2 的配套库，提供了高效的 XSLT 转换引擎和命令行工具。

## 功能概述

### 栓心组件
- **libxslt 库**：XSLT 1.0 核心转换引擎
- **libexslt 库**：XSLT 扩展功能集（日期、数学、字符串等）
- **xsltproc**：命令行 XSLT 转换工具

### 主要功能
- XSLT 1.0 标准完整实现
- XPath 表达式支持（依赖 libxml2）
- XSLT 扩展模块（EXSLT）
- 多种输出格式支持（XML、HTML、文本）
- 高性能转换引擎

## OHOS 适配

### 适配要点
1. **平台检测修复**
   - 需应用 `config.guess` 补丁识别 HarmonyOS 平台（E007）
   - 需应用 `config.sub` 补丁验证 `aarch64-unknown-linux-ohos` 三元组（E072）
   - 补丁文件：`0002-config.guess.patch`, `0003-config.sub.patch`

2. **编译配置**
   - 使用 `--without-python` 禁用 Python 绑定（避免需要 python-dev）
   - 需设置 `PKG_CONFIG_PATH` 以找到 libxml2
   - 需设置 `TMPDIR=~/tmp` 避免 HMDFS 权限问题

3. **已知问题**
   - HMDFS 文件系统可能导致 configure 权限问题（需手动编译绕过）
   - 运行时需要 libxml2.so 动态库（当前 libxml2 编译为静态库）
   - make check 可能因 HMDFS 限制无法执行（建议手动验证）

### 与 Linux 的差异
- 平台三元组不同：`aarch64-unknown-linux-ohos` vs `aarch64-linux-gnu`
- 需要额外的 config.guess/config.sub 补丁
- HMDFS 文件系统限制需要特殊处理

## 依赖

### 编译依赖
| 软件 | 版本要求 | 状态 |
|------|----------|------|
| libxml2 | >= 2.9.0 | ✅ 已预编译（2.15.3） |
| pkg-config | >= 0.29 | ✅ 已预编译 |

### 运行依赖
| 软件 | 版本要求 | 说明 |
|------|----------|------|
| libxml2.so | >= 2.9.0 | ⚠️ 当前为静态库，需确保动态库可用 |

### 安装依赖
```bash
# 安装编译依赖（预编译包）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libxml2 2.15.3

# 设置环境变量
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
```

## 编译版本

| 版本 | 状态 | 日期 | 补丁数 | 说明 |
|------|------|------|--------|------|
| 1.1.39 | ✅ published | 2026-05-21 | 3 | 最新版本，已通过质量门禁 |

## 安装方法

### 通过 cmd-pkgs 安装（推荐）
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libxslt 1.1.39
```

### 安装验证
```bash
# 验证 pkg-config
pkg-config --modversion libxslt    # 应输出 1.1.39
pkg-config --modversion libexslt   # 应输出 0.8.21

# 验证命令行工具
xsltproc --version                 # 应输出版本信息

# 验证头文件和库
ls ~/usr/local/include/libxslt/    # 应有 21 个头文件
ls ~/usr/local/lib/libxslt.so*     # 应有动态库
```

## 使用注意事项

1. **运行时依赖**
   - xsltproc 需要 libxml2.so 动态库
   - 当前 libxml2 编译为静态库版本，需确保动态库可用
   - 建议：安装 libxml2 时同时安装动态库版本

2. **功能验证**
   ```bash
   # 简单转换测试
   echo '<?xml version="1.0"?><doc>test</doc>' > test.xml
   echo '<?xml version="1.0"?><xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:template match="/"><output><xsl:value-of select="doc"/></output></xsl:template></xsl:stylesheet>' > test.xsl
   xsltproc test.xsl test.xml      # 应输出 <output>test</output>
   ```

3. **开发使用**
   ```bash
   # 编译链接 libxslt
   gcc -c myapp.c $(pkg-config --cflags libxslt)
   gcc myapp.o -o myapp $(pkg-config --libs libxslt)
   ```

## 参考

- [libxslt 官方网站](https://gitlab.gnome.org/GNOME/libxslt)
- [libxslt 文档](https://gitlab.gnome.org/GNOME/libxslt/-/blob/master/README)
- [XSLT 1.0 规范](https://www.w3.org/TR/xslt/)
- [EXSLT 扩展](http://exslt.org/)
- [libxml2 依赖](../libxml2/README.md)
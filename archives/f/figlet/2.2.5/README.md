# figlet 2.2.5 — OpenHarmony 编译记录

## 基本信息
- **软件**: figlet
- **版本**: 2.2.5
- **构建系统**: Makefile（纯 Makefile 项目，无 configure）
- **目标平台**: OpenHarmony aarch64
- **编译器**: clang 15.0.4
- **编译日期**: 2026-05-11

## 软件简介

figlet 是一个将普通文本转换为大型 ASCII 艺术字符的程序。它可以将输入文本渲染为由键盘字符组成的"签名"，广泛用于终端欢迎消息、邮件签名和文档装饰。

## 编译指导

### 源码获取
```bash
# 官方源码
http://www.figlet.org/pub/figlet/program/unix/figlet-2.2.5.tar.gz
```

### 编译命令
```bash
# 解压源码
tar -xzf figlet-2.2.5.tar.gz
cd figlet-2.2.5

# 应用补丁（如需要）
patch -p1 < 0001-utf8.h.patch

# 编译（figlet 无 configure 步骤）
make PREFIX=/usr/local

# 安装到临时目录
make install PREFIX=/usr/local DESTDIR=/path/to/staging

# 安装到正式目录
make install PREFIX=/usr/local
```

### 编译环境要求
- C 编译器: clang 或 gcc
- 构建工具: make
- 无外部依赖

## 补丁清单

### 0001-utf8.h.patch
**类型**: 平台兼容性修复  
**说明**: 添加 `#include <sys/cdefs.h>` 解决 `__BEGIN_DECLS`/`__END_DECLS` 宏未定义问题

**修改内容**:
```diff
--- a/utf8.h
+++ b/utf8.h
@@ -17,6 +17,7 @@
 #define _UTF8_H_
 
 #include <sys/types.h>
+#include <sys/cdefs.h>
 
 #include <wchar.h>
```

**适用条件**: 使用 clang 编译器编译 OpenHarmony 平台时需要

## 已知限制

1. **编译警告**: 存在 22 个 K&R 风格函数原型弃用警告（C2x 标准将不支持，但不影响功能）
2. **硬编码路径**: 默认字体路径硬编码为 `/usr/local/share/figlet`，运行时需用 `-d` 参数指定实际安装路径
3. **无 configure**: figlet 使用纯 Makefile，无 autoconf/configure 步骤

## 功能验证

### 验证命令

```bash
# 查看版本信息
figlet -I 2    # 输出: /usr/local/share/figlet (字体目录)
figlet -I 1    # 输出: 20205 (版本 infocode)

# 基本输出测试
figlet -d /path/to/fonts "Hello"

# 使用不同字体
figlet -d /path/to/fonts -f slant "Test"
figlet -d /path/to/fonts -f banner "Welcome"

# 列出可用字体
figlist -d /path/to/fonts

# 字体验证工具
chkfont /path/to/fonts/standard.flf
```

### 测试结果

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 版本信息 | ✅ | infocode 20205 正确 |
| ASCII 输出 | ✅ | 基本文本转换正常 |
| 字体切换 | ✅ | 支持 18 种字体 |
| 字体验证 | ✅ | chkfont 工具正常 |

### 可用字体列表

| 字体名称 | 风格 |
|----------|------|
| standard | 标准字体 |
| banner | 横幅风格 |
| big | 大字体 |
| block | 块状字体 |
| bubble | 气泡字体 |
| digital | 数字风格 |
| lean | 倾斜字体 |
| mini | 迷你字体 |
| script | 手写体 |
| shadow | 阴影字体 |
| slant | 斜体 |
| small | 小字体 |

## 编译产物

| 文件 | 大小 | 说明 |
|------|------|------|
| figlet-2.2.5-ohos-aarch64.tar.gz | 803KB | 主安装包（已 strip） |
| figlet-2.2.5-ohos-aarch64-debug.tar.gz | 132KB | 调试符号包 |
| install-figlet-2.2.5.sh | 1.4KB | 安装脚本 |

### 包含文件
- **可执行文件**: figlet, chkfont, figlist, showfigfonts
- **字体文件**: 18 个 .flf 字体文件
- **手册页**: figlet.6, chkfont.6, figlist.6, showfigfonts.6

## 参考资料

- 官方网站: http://www.figlet.org/
- 源码下载: http://www.figlet.org/pub/figlet/program/unix/
- GitHub Mirror: https://github.com/cmatsuoka/figlet
- 许可证: MIT / BSD style
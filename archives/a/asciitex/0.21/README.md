# asciiTeX 0.21

> Generate ASCII-art representations of mathematical equations

## 简介

asciiTeX 是一个命令行工具，用于将 LaTeX 数学公式渲染为 ASCII 艺术形式。它是 eqascii（由 Przemek Borys 开发）的分支，由 Bart Pieters 维护。该工具支持常见的数学表达式语法，包括分数、上下标、根号、求和、极限等，输出为纯文本的 ASCII 艺术图形，适合在终端环境中展示数学公式。

## OHOS 适配要点

1. **禁用 GTK GUI模式**：使用 `--disable-gtk` 配置选项跳过 GTK2 依赖，仅编译命令行工具
2. **修复 SYNTAX_ERR_FLAG 重复定义**：头文件 `asciiTeX_struct.h` 中定义了全局变量，多文件包含导致链接错误，需改为 `extern` 声明
3. **umask 077 权限修复**：HMDFS 文件系统下 configure 脚本设置的 umask 077 导致文件不可读，需修改为 umask 022
4. **静态链接**：作为终端工具，使用 `-static` 标志进行静态链接（R26 规范）

## 依赖

无外部依赖（禁用 GTK 后）。

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | - | 禁用 GTK 后无外部依赖 |

## 功能验证

```bash
# 版本信息
asciiTeX -v

# 渲染数学公式
asciiTeX 'y=x^2'
# 输出:
#      2
# y = x

# 复杂公式
asciiTeX '\frac{a}{b}'
```

## 补丁说明

| 补丁 | 说明 |
|------|------|
| 0001-src-asciiTeX.c.patch | 添加 SYNTAX_ERR_FLAG 全局定义 |
| 0002-src-asciiTeX_struct.h.patch | 将 SYNTAX_ERR_FLAG 改为 extern 声明 |

## 参考

- [项目主页](https://asciitex.sourceforge.net/)
- [SourceForge 下载](https://downloads.sourceforge.net/project/asciitex/asciiTeX-0.21.tar.gz)

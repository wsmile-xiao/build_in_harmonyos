# man2html

> Convert nroff man pages to HTML (Perl program)

## 简介

man2html 是一个 Perl 程序，用于将格式化的 nroff 手册页输出转换为 HTML 格式。它由 Earl Hood 开发，是 v3 系列版本，要求 Perl 5 运行环境。

该工具读取标准输入（nroff 格式化的 man page）并输出 HTML 到标准输出，常用于在 Web 浏览器中查看 man pages。

## OHOS 适配要点

- **纯 Perl 脚本工具**：无需 C/C++ 编译，构建系统为 custom（install.me Perl 安装脚本）
- **系统依赖**：需要 perl 运行时（鸿蒙设备需预装 perl，非 Conan 包依赖）
- **安装方式**：`perl install.me -batch -binpath <dir> -manpath <dir> -perlpath <perl>`
- **#! 行重写**：install.me 会将 man2html 脚本的 `#!` 行修改为指向实际 perl 路径

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| perl | 5.x | 系统运行时依赖，需在 PATH 中可用 |

## 功能验证

```bash
# 将 man page 转换为 HTML
echo '.TH TEST 1' | man2html

# 查看自带文档
man2html -help
```

## 参考

- [Savannah 项目主页](https://savannah.nongnu.org/projects/man2html/)
- [Homebrew formula](https://formulae.brew.sh/formula/man2html)
- [源码下载](https://www.mhonarc.org/release/misc/man2html3.0.1.tar.gz)

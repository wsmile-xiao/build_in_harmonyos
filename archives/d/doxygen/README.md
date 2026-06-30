# doxygen

## 简介

Doxygen 是一个文档生成工具，可以从 C++、C、Java、Python 等源代码中生成文档。它支持 HTML、LaTeX、RTF、PDF 等多种输出格式。

## 已编译版本

- **1.17.0** (2026-05-27) — built

## 构建系统

- **类型**: cmake
- **依赖**: libiconv

## 安装说明

```bash
# 使用 cmd-pkgs 安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- doxygen 1.17.0
```

## 验证

```bash
doxygen --version
# 输出: 1.17.0
```

## 参考资料

- 官方网站: https://www.doxygen.nl/
- GitHub: https://github.com/doxygen/doxygen
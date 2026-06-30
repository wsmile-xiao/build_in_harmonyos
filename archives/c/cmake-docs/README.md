# CMake Documentation

独立的 CMake HTML 文档包，从 CMake 源码构建，支持离线浏览和搜索。

## 简介

CMake 官方文档的 HTML 版本，包含完整的命令、变量、模块、策略、手册等参考内容，适合离线查阅。

## OHOS 适配

- 从 CMake 源码的 `Help/` 目录构建，使用 Sphinx 生成 HTML
- 需创建 `conf.py` 配置文件（基于 `Utilities/Sphinx/conf.py.in`）
- 添加 cmake 扩展到 `sys.path`
- cmake.org 下载源码比 GitHub 更稳定

## 依赖

构建依赖：
- Python 3.12+
- Sphinx 9.1.0+
- sphinx-rtd-theme 3.1.0+

## 文档内容

- **总页面数**：2060 个 HTML 页面
- **包含内容**：
  - 命令参考（command/）
  - 变量参考（variable/）
  - 模块文档（module/）
  - 策略文档（policy/）
  - 手册文档（manual/）
  - 属性文档（prop_*/）
  - 环境变量文档（envvar/）
  - 生成器文档（generator/）
  - CPack 生成器文档（cpack_gen/）
  - 发布说明（release/）
  - 用户指南（guide/）

## 使用方法

解压后用浏览器打开 `html/index.html`：

```bash
tar xzf cmake-docs-3.30.0-html.tar.gz
# 用浏览器打开 html/index.html
```

## 特性

- 完整的 CMake 3.30.0 官方文档
- 支持搜索功能（searchindex.js）
- 紧凑的全局索引（genindex.html）
- Read the Docs 主题风格
- 离线可用，无需网络连接

## 参考

- CMake 官网：https://cmake.org/
- CMake 文档：https://cmake.org/documentation/
- 源码仓库：https://github.com/Kitware/CMake
# venc-pyc

## 简介

venc-pyc 是 [VenC](https://framagit.org/denissalem/VenC)（一个 Python 静态
博客生成器）的**预编译 Python bytecode 子包**。Alpine 打包生态中 `venc`
主包安装 `venc3/` 模块，`venc-pyc` 子包额外生成
`__pycache__/*.cpython-*.pyc` 供 python3 直接加载，在保持脚本可审计的同时
提升冷启动性能。

本归档按路径 A 将 venc-pyc 3.2.7 作为**独立 Conan 包**归档，源码来源为
VenC 3.2.7 的 PyPI sdist（同一上游项目 framagit.org/denissalem/VenC）。

## 特性

- 静态博客生成器：生成 HTML 站点、RSS/Atom feed、主题系统
- 预编译 bytecode：包内含 `__pycache__/*.cpython-*.pyc`（独立包同时保留
  运行所需模块文件 `venc3/**/*.py`，自包含可运行）
- 低依赖：仅需 python3 与 pyyaml、unidecode（纯 Python 运行时包）
- src layout（src/venc3/），flit_core PEP 517 构建

## 安装

### 预编译包安装（推荐：Conan）

```bash
conan install --requires=venc-pyc/3.2.7 --build=missing
```

### 手动安装（源码）

```bash
python3 -m pip install venc-3.2.7.tar.gz   # PEP 517 / flit_core
# 或直接使用包内模块：python3 -c "import venc3"
```

## 使用方法

```bash
# 显示版本
venc -v

# 查看帮助
venc -h

# 新建博客
venc -nb <博客目录>

# 导出博客
venc -xb <博客目录>
```

## 依赖

- python3（运行时解释器）
- pyyaml（运行时 Python 包：博客配置解析）
- unidecode（运行时 Python 包：slug/转写处理）

## 许可证

GPL-3.0（Copyright Denis Salem，见上游 LICENSE.md）

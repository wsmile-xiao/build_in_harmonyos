# cfgv 3.4.0 适配笔记

## 软件简介

cfgv 是 Anthony Sottile 开发的纯 Python 配置验证库。它提供声明式 schema 定义
（`Map`、`Required`、`Optional`、`Conditional`、`Array` 等）和 `validate()`、
`apply_defaults()`、`remove_defaults()` 函数，用于校验嵌套字典/列表结构并产生
人类可读的错误消息（`ValidationError`）。

cfgv 是 `pre-commit` 框架的底层依赖之一，也被 `all-repos` 间接依赖。

## 构建系统

- **后端**: setuptools（setup.py + setup.cfg，无 pyproject.toml）
- **包类型**: py_modules = cfgv（单文件模块 cfgv.py）
- **Python 版本**: >=3.8
- **C 扩展**: 无
- **许可证**: MIT

## 依赖

- **运行时依赖**: 无
- **开发依赖**: covdefaults, coverage, pytest

## 适配说明

cfgv 是纯 Python 单文件模块，无平台特定代码，无 C 扩展。适配方式与 pyparsing
一致：使用 `pip install . --prefix=... --no-deps --no-build-isolation` 从本地
源码构建安装。

### 构建流程

```bash
# 1. 下载源码 tarball
curl -fsSL -o cfgv-3.4.0.tar.gz \
  "https://github.com/asottile/cfgv/archive/refs/tags/v3.4.0.tar.gz"

# 2. 校验 SHA256
sha256sum cfgv-3.4.0.tar.gz
# 期望: a8a4e4ad5618b6e65af563b14f46ccb1e45f5725c3b733d0ba15bb2a3b5bf9fd

# 3. Conan 本地构建（从源码 pip install，非远程下载）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

### 质量门禁

- **R32**: settings.os 判断使用 `in ("Linux", "OHOS")`
- **R33**: build() 使用 sys.executable，不依赖 shell 环境变量
- **R34**: test_package 实质性测试 — 7 个 smoke test 覆盖模块导入、
  MISSING 哨兵、ValidationError、validate/Map/Required/Optional、
  check_one_of、Array 嵌套验证
- **R39**: conandata.yml URL 指向 GitHub 官方源

## 遇到的问题

无。cfgv 是纯 Python 库，构建和测试均一次通过。

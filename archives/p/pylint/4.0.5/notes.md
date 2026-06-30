# pylint 4.0.5 适配笔记

## 编译环境
- 构建系统: python (pip install)
- 编译日期: 2026-06-09
- 编译器: Python 3.12.8
- 状态: published

## 编译步骤

1. 下载源码包从 PyPI
2. 解压源码到构建目录
3. 使用 pip 安装依赖到 `$DEFAULT_PREFIX/lib/python3.12/site-packages`
4. 使用 pip install 安装 pylint 到 staging 目录

```bash
# 安装依赖
python3 -m pip install astroid isort mccabe platformdirs tomlkit dill --target=$DEFAULT_PREFIX/lib/python3.12/site-packages

# 安装 pylint 到 staging 目录
python3 -m pip install . --target=$TEST_PREFIX/$DEFAULT_PREFIX/lib/python3.12/site-packages --no-deps
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | Python SSL 模块配置问题 | 使用 curl 手动下载源码包，然后使用 file:// URL |
| 2 | 嵌套源码检测错误 | 脚本误将 doc 目录当作源码 | 手动设置正确的源码目录 |
| 3 | bin 目录位置错误 | pip 将入口点放在 site-packages/bin | 手动移动 bin 目录到正确位置 |

## 源码修改

无补丁，纯 Python 包直接安装。

## 依赖版本

- astroid 4.1.2
- isort 8.0.1
- mccabe 0.7.0
- platformdirs 4.10.0
- tomlkit 0.15.0
- dill 0.4.1

## 验证结果

```bash
$ pylint --version
pylint 4.0.5
astroid 4.1.2
Python 3.12.8 (main, Dec 11 2024, 01:25:28) [Clang 15.0.4]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pylint-4.0.5-ohos-aarch64.tar.gz | ~1.5MB | 预编译包 |

## 注意事项

- pylint 是纯 Python 包，无需编译
- 需要确保 PYTHONPATH 包含安装路径
- 入口点脚本需要在正确的 bin 目录中

---

**编译结束**: 2026-06-09 11:36
**最终状态**: published
---

**编译结束**: 2026-06-09 11:38
**最终状态**: built

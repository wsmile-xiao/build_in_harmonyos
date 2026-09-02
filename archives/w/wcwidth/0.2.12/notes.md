# wcwidth 0.2.12 适配笔记

## 概要

wcwidth 0.2.12 是纯 Python setuptools 库，用于计算 Unicode 字符和字符串在终端中的显示宽度。本次按 Python 生态路径适配，不涉及 C/C++ 编译、平台补丁或二进制签名。

## 源码

- URL: https://files.pythonhosted.org/packages/d7/12/63deef355537f290d5282a67bb7bdd165266e4eca93cd556707a325e5a24/wcwidth-0.2.12.tar.gz
- SHA256: f01c104efdf57971bcb756f054dd58ddec5204dd15fa31d6503ea57947d97c02
- 构建系统: setuptools

## 构建与测试

使用 Python 3 与 `pip wheel --no-deps --no-build-isolation` 构建，再安装到 Conan 包的 `lib/pythonX.Y/site-packages`。上游测试命令为：

```text
python3 -m pytest -o addopts='' -q
```

上游测试目录包含 `tests/test_core.py`、`tests/test_emojis.py` 和 `tests/test_ucslevel.py`，实测收集 36 项，全部通过（36/36）。`-o addopts=''` 仅清除上游 tox.ini 中需要额外 pytest-cov 插件的覆盖率参数，没有修改测试源码、断言或测试数据。

消费者测试额外验证版本、窄字符、宽字符、组合字符和字符串宽度，共 6 项，全部通过。

## 适配结论

纯 Python 包不依赖 OHOS 特定 ABI；Conan 配方只声明 `os` 与 `arch`，通过 `PYTHONPATH` 导出安装后的 site-packages。没有新增 patches/，也没有命令行工具，因此不创建 commands.json。
---

**编译结束**: 2026-09-02 12:57
**最终状态**: built

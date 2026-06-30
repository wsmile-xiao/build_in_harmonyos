# img2pdf 0.6.3 适配笔记

## 编译环境
- 构建系统: custom (Python package)
- 编译日期: 2026-05-21
- 编译器: Python 3.12
- 状态: built

## 编译步骤

img2pdf 是一个纯 Python 包，使用 pip 安装：

```bash
# 修改 setup.py 和 pyproject.toml 移除 pikepdf 依赖
# 因为 qpdf 预编译包有问题，pikepdf 无法安装

python3 -m pip install . --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX --no-build-isolation
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pikepdf 无法安装 | qpdf 预编译包库路径错误 (`../libqpdf/libqpdf.so`) | 移除 pikepdf 依赖，img2pdf 可在没有 pikepdf 的情况下运行（部分功能受限） |

## 源码修改

- `patches/0001-remove-pikepdf-dependency.patch`
  - setup.py: 移除 `"pikepdf"` 依赖
  - pyproject.toml: 移除 `"pikepdf"` 依赖

## 依赖版本

- Python 3.12.9
- Pillow 12.2.0 (已安装)

## 验证结果

```bash
$ img2pdf --version
img2pdf 0.6.3

$ img2pdf --help
# 显示完整帮助信息，功能正常
```

## 交付物

| 文件 | 说明 |
|------|------|
| img2pdf.py | Python 模块 (178KB) |
| img2pdf | 命令行脚本 |
| img2pdf-gui | GUI 脚本 |

## 注意事项

1. 此版本移除了 pikepdf 依赖，部分高级 PDF 功能可能受限
2. 如需完整功能，需先修复 qpdf 预编译包问题，然后重新安装 pikepdf
3. qpdf 预编译包问题：二进制文件硬编码了 `../libqpdf/libqpdf.so` 相对路径
---

**编译结束**: 2026-05-22 10:35
**最终状态**: built

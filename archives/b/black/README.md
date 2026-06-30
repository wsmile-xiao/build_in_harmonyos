# black

> Black — 不妥协的 Python 代码格式化器

## 简介

Black 是 Python 代码格式化器。它通过将代码重新格式化为统一风格来提高代码可读性。Black 使用确定性规则格式化代码，不需要配置选项。

## OHOS 适配要点

- 纯 Python 项目，使用 pip --target 安装到 staging 目录
- GitHub tarball 缺少 src/_black_version.py，需手动创建补丁
- 需设置 SETUPTOOLS_SCM_PRETEND_VERSION 环境变量
- 无 ELF 二进制文件，无需签名/strip/RPATH

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python 3 | 3.12.8 | 运行时依赖 |

## 功能验证

```bash
black --version
```

## 参考

- [官方文档](https://black.readthedocs.io/)
- [源码仓库](https://github.com/psf/black)

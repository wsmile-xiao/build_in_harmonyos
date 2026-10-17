# distro

## 简介

distro（python3-distro）是一个纯 Python 的 OS 平台信息 API，用于识别 Linux 发行版信息，是 `platform.linux_distribution()` 的替代方案。

## 可用版本

| 版本 | 状态 | 构建系统 |
|------|------|----------|
| 1.9.0 | built | Python setuptools |

## OHOS 适配

- 纯 Python 包，无 C/C++ 编译步骤
- 无第三方 Python 运行时依赖
- 默认读取 `/etc/os-release`
- 可通过 `UNIXCONFDIR` 环境变量配置发行版信息文件路径
- 提供 `distro` 命令行入口

## 依赖

无第三方运行时依赖；构建阶段需要 setuptools。

## 功能验证

```bash
python3 -c "import distro; print(distro.__version__)"
distro --help
```

## 参考

- 上游仓库：https://github.com/python-distro/distro
- PyPI：https://pypi.org/project/distro/

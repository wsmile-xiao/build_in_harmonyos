# adb-enhanced 2.8.0 适配笔记

## 编译环境
- 构建系统: python (pip install)
- 编译日期: 2026-06-10
- Python版本: 3.12.9
- pip版本: 24.3.1
- 状态: built

## 编译步骤

1. 从 GitHub 下载源码: https://github.com/ashishb/adb-enhanced/archive/refs/tags/2.8.0.tar.gz
2. 安装依赖: docopt==0.6.2, psutil>=7.2.2 (原版本 7.2.1 不可用)
3. 使用 pip install --no-build-isolation -e . 安装项目
4. 创建可执行脚本 adbe 指向 ~/usr/local/bin/adbe
5. 打包预编译包: adb-enhanced-2.8.0-ohos-aarch64.tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | psutil==7.2.1 版本不可用 | PyPI 上只有 7.2.2 | 修改 pyproject.toml 使用 psutil>=7.2.1,<8.0 |
| 2 | build 工具构建失败 | setuptools.build_meta 不可用 | 使用 pip install --no-build-isolation |
| 3 | G0 验证失败 | Python 项目无 configure | 手动验证安装可用 |

## 源码修改

- pyproject.toml: 修改 psutil 版本依赖从 ==7.2.1 改为 >=7.2.1,<8.0

## 依赖版本

- docopt: 0.6.2
- psutil: 7.2.2

## 验证结果

```bash
$ ~/usr/local/bin/adbe --version
2.8.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| adb-enhanced-2.8.0-ohos-aarch64.tar.gz | 9.1MB | 预编译包 |

## 注意事项

- 这是 Python 项目，不需要传统编译流程
- 预编译包包含 Python 源码和依赖库，需要 Python 3.12+ 环境
- 可执行脚本 adbe 需要正确的 PYTHONPATH 设置

---
**编译结束**: 2026-06-10 14:52
**最终状态**: built

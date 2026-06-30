# black 26.5.1 适配笔记

## 编译环境
- 构建系统: pip (Python项目)
- 编译日期: 2026-06-13
- 编译器: clang/clang++ (用于可能的原生扩展)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build black 26.5.1 --url=https://github.com/psf/black/archive/refs/tags/26.5.1.tar.gz`
2. 创建 `src/_black_version.py` 文件（内容: `version = "26.5.1"`）
3. `SETUPTOOLS_SCM_PRETEND_VERSION=26.5.1 pip install . --target=$STAGING_PREFIX/lib/python3.12/site-packages`
4. 将 site-packages/bin/ 下的脚本移到 bin/ 并修复 shebang

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | src/_black_version.py 缺失 | GitHub tarball 无 git 元数据，hatch-vcs 无法生成此文件 | 手动创建 src/_black_version.py: `version = "26.5.1"` |
| 2 | 版本检测失败 | setuptools-scm 无法检测版本 | 设置 SETUPTOOLS_SCM_PRETEND_VERSION=26.5.1 |

## 源码修改

- `src/_black_version.py`: 新增文件，内容为 `version = "26.5.1"`（GitHub tarball 缺少此文件）

## 依赖版本

- python3: 3.12.8
- pip: 24.3.1

## 验证结果

```bash
black --version
black, 26.5.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| black-26.5.1-ohos-aarch64.tar.gz | ~12MB | Release包 |
| black-26.5.1-ohos-aarch64-debug.tar.gz | ~12MB | Debug包 |

## 注意事项

- 纯 Python 项目，pip --target 安装方式
- GitHub tarball 缺少 src/_black_version.py，需手动创建
- 需设置 SETUPTOOLS_SCM_PRETEND_VERSION
---
**编译结束**: 2026-06-13 20:23
**最终状态**: built

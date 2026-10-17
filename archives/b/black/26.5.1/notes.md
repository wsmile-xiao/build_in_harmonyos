# black 26.5.1 适配笔记

## 编译环境
- 构建系统: pip (Python项目, hatchling backend)
- 编译日期: 2026-09-18
- 编译器: N/A (纯Python项目，无C/C++编译)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build black 26.5.1 --url=https://files.pythonhosted.org/.../black-26.5.1.tar.gz`
2. 在 build() 中创建 `src/_black_version.py`（GitHub tarball 缺少此文件）
3. `pip install hatchling hatch-vcs hatch-fancy-pypi-readme`（构建依赖）
4. `SETUPTOOLS_SCM_PRETEND_VERSION=26.5.1 pip wheel . --no-deps --no-build-isolation`
5. `pip install --no-compile --target <site-pkg> <wheel>`（连带安装全部运行时依赖）
6. 复制 site-pkg 到 `lib/python3.X/site-packages/`（排除 pip 生成的 bin/）
7. 创建 `bin/black` wrapper 脚本

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | src/_black_version.py 缺失 | GitHub tarball 无 git 元数据，hatch-vcs 无法生成此文件 | 在 build() 中直接创建 `src/_black_version.py: version = "26.5.1"` |
| 2 | 版本检测失败 | setuptools-scm 无法检测版本 | 设置 SETUPTOOLS_SCM_PRETEND_VERSION=26.5.1 |
| 3 | 构建隔离超时 | pip build isolation 下载 hatchling 等依赖超时 | 使用 --no-build-isolation 并预装构建依赖 |
| 4 | test_package 报 ModuleNotFoundError: No module named 'click' | pip wheel --no-deps 只打包 black 本身，运行时依赖（click/mypy-extensions/packaging/pathspec/platformdirs/pytokens）未随包分发 | build() 中 `pip install --no-compile --target` 安装 wheel 及全部运行时依赖，package() 复制进 site-packages（排除 pip 生成 bin/，保留自研 wrapper） |

## 源码修改

- 无补丁。在 conanfile.py 的 build() 方法中直接创建 `src/_black_version.py`

## 依赖版本

- python3: 3.12.9
- pip: 26.1.2
- 运行时依赖（打包进 site-packages）: click 8.5.0, mypy-extensions 1.1.0, packaging 26.3, pathspec 1.1.1, platformdirs 4.11.9, pytokens 0.4.1

## 验证结果

```bash
$ conan create archives/b/black/26.5.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
...
black/26.5.1 (test package): RUN: ".../bin/black" --version
python -m black, 26.5.1 (compiled: no)
Python (CPython) 3.12.9
```

功能验证（wrapper 直接调用）：
```bash
$ <pkg>/bin/black t2.py  # 格式化测试
1 file reformatted.
```

上游测试套件（tests/, pytest）依赖大量 dev 包，未在 CI 环境运行；以 `--version` + 实际格式化冒烟验证代替（见 test_package/MANIFEST.yml 说明）。

## 交付物

| 文件 | 说明 |
|------|------|
| black-26.5.1-ohos-aarch64.tar.gz | Release包 (site-packages + bin wrapper) |

## 注意事项

- 纯 Python 项目，使用 pip wheel 构建方式
- GitHub tarball 缺少 src/_black_version.py，在 build() 中创建
- 需设置 SETUPTOOLS_SCM_PRETEND_VERSION
- 构建依赖需预装 (hatchling, hatch-vcs, hatch-fancy-pypi-readme)
- 运行时依赖必须随包分发（pip install --target），不能依赖目标机全局 pip 环境
---
**编译结束**: 2026-09-18
**最终状态**: built

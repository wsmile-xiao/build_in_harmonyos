# dtfabric 20251118.1 适配笔记

> 注: 20251118.1 是因 conan 制品仓已发布 20251118 后修订 settings(L0p)而递增的
> conan 版本号;上游源码包仍为 dtfabric-20251118.tar.gz(__version__="20251118")。

## 编译环境
- 构建系统: custom(pip install)
- 编译日期: 2026-08-28
- 编译器: N/A(纯 Python,无 C/C++)
- 状态: built

## W0 依赖预检
dtfabric 无 conan 依赖(requirements 留空),PyYAML 是 pip 运行时依赖而非 conan 包,无 conan 侧阻塞。

## 编译步骤

conan build 流程:

1. `conan source` → `get()` 从 PyPI(files.pythonhosted.org)拉取 dtfabric-20251118.tar.gz,strip_root 解压。
2. `build()`:
   - `pip install setuptools wheel --quiet`(准备纯 Python 构建后端)
   - `pip install . --target=staging --no-build-isolation --no-deps`(装包到 build_folder/staging,--no-deps 避免联网装 PyYAML 等运行时依赖,--no-build-isolation 复用当前环境)
3. `package()`: 将 staging 目录整体 `copy()` 到 package_folder;复制 LICENSE 到 licenses/。

实际 conanfile.py 关键片段:
```python
staging = os.path.join(self.build_folder, "staging")
self.run(f"{sys.executable} -m pip install setuptools wheel --quiet", cwd=self.source_folder)
self.run(f"{sys.executable} -m pip install . --target={staging} --no-build-isolation --no-deps", cwd=self.source_folder)
```

## 遇到的问题与解决方案

无

## 依赖版本
- Python >= 3.10(本机 /data/service/hnp/python.org/python_3.12/bin/python3.12)
- PyYAML(pip 运行时依赖,非 conan recipe 依赖)
- setuptools / wheel(pip 构建后端,build() 内联网/本地安装)

## 验证结果

```bash
$ cd archives/d/dtfabric/20251118.1 && conan create . --build=missing
...
dtfabric/20251118.1: Already installed! (1 of 1)
======== Launching test_package ========
...
======== Testing the package: Executing test ========
dtfabric/20251118.1 (test package): Running test()
dtfabric/20251118.1 (test package): RUN: /data/service/hnp/python.org/python_3.12/bin/python3.12 .../test_package/test_all.py
dtfabric version: 20251118
Module import test: PASSED
CLI stdout: usage: validate-definitions.py [-h] [PATH]
Validates dtFabric format definitions.
...
CLI tool test: PASSED
All dtfabric tests PASSED
===EXIT=0===
```

另跑 ohc 质量门禁:
```bash
$ python3 scripts/ohc-run.py verify-build dtfabric 20251118.1
  ℹ️ G1: 二进制完整性...
  ✅   G1: ✅0 ⚠️0 ❌0
  ℹ️ G2: 功能可用性...
  ✅   G2: ✅0 ⚠️1 ❌0
  ℹ️ G3: 可移植性...
  ✅   G3: ✅0 ⚠️0 ❌0
  ℹ️ G4: 档案完整性...
  ✅   G4: ✅0 ⚠️2 ❌0
  ✅   质量报告: PASS
```
G1/G2/G3 的 ⚠️ 均因本包为纯 Python(无 ELF 二进制,G2 取 bin/ 下脚本 --version 失败属预期),无 ❌。W3 conan create 全绿,test_package 模块导入+CLI 均通过。

## 上游测试用例

上游 `tests/` 目录含 unittest TestCase 子类,由 `run_tests.py`(unittest.TestLoader().discover)加载,框架为 **unittest**(非 pytest)。测试依赖 `mock`(test_requirements.txt)。

实跑命令与结果(Python 3.12.8,鸿蒙环境):
```bash
$ cd <源码根> && PYTHONPATH=. ./run_tests.py
Using Python version 3.12.8 (main, Dec 11 2024, 01:25:28) [Clang 15.0.4 ...]
... (188 个测试逐条 ok) ...
----------------------------------------------------------------------
Ran 188 tests in 0.410s

OK
$ echo $?
0
```

结果:**188 tests,全部 OK,exit 0**。覆盖 tests/data_types.py、tests/reader.py、tests/registry.py、tests/runtime/*.py 等模块。无失败、无跳过、无错误。

---

**编译结束**: 2026-08-28
**最终状态**: built

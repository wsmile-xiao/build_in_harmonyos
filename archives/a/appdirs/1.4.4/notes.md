# appdirs 1.4.4 — 适配笔记

## 概述
- 上游: https://github.com/ActiveState/appdirs (tag 1.4.4, 2020-05)
- 类型: 纯 Python 单模块库（`appdirs.py`，py_modules=["appdirs"]），无 C/C++ 代码
- 依赖: 零（仅 sys/os stdlib），PyPI requires_dist 为空
- SHA-256 (GitHub tag tarball): 6db10570b4f0176a05924c20745ff73385497e57829634fb3e756e15636ff408

## 适配要点
1. 纯 Python noarch → `package_type = "python-require"`，package() 用 shutil.copy2
   将 `appdirs.py` 拷贝到 `lib/python3.12/site-packages/`（同 python-magic/rich
   noarch 模式；pip/setuptools 构建在本环境不可用）。
2. 无需任何源码补丁：模块仅用 stdlib，Python 3.12 下无 import 障碍
   （unittest 已在 py2.7 分支处理 unittest2 回退，py3 直接用 unittest）。
3. package_info() 注入 runenv/buildenv PYTHONPATH（aiohttp 教训：只打印不够）。
4. R38: 无 console_scripts / scripts= / bin/ 产物 → 纯库包，不创建 commands.json。

## 上游测试
- 唯一测试源: `test/test_api.py`（unittest，Test_AppDir 类）
- 用例: test_metadata / test_helpers / test_dirs（3 个）
- 实测: `python3 -m unittest -v test.test_api` → 3/3 OK, rc=0
- 双口径: source_declared_total=3, configured_executable_total=3,
  executed_passed_total=3, failed=0, uninstantiated=0 → 3/3 = 100%

## 环境
- Python 3.12.9, Conan 2.29.1, profile ohos-aarch64
- /tmp 只读（E002）→ 临时目录用 $HOME/tmp
---

**编译结束**: 2026-09-20 20:39
**最终状态**: built

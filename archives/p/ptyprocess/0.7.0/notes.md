# ptyprocess 0.7.0 适配笔记

## 编译环境
- 构建系统: python3 / flit_core
- 编译日期: 2026-09-08
- 编译器: N/A（纯 Python）
- 状态: built
- 目标: HarmonyOS PC arm64 / Python 3.12

## 编译步骤
1. 使用 PyPI 官方源码归档：`ptyprocess-0.7.0.tar.gz`。
2. 执行语言预检：任务语言 `python`，源码识别为 `python`，通过。
3. 执行上游完整测试：`python3 -m unittest discover -s tests -p 'test_*.py' -v`，14/14 passed。
4. 构建 wheel：`python3 -m pip wheel --no-deps -w $TMPDIR/ptyprocess-wheel .`，生成 `ptyprocess-0.7.0-py2.py3-none-any.whl`。
5. Conan recipe 在 `build()` 中重建 wheel，`package()` 解压 wheel 到 `lib/pythonX.Y/site-packages`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 初次语言预检识别为 mixed | 初始化脚本误将 `docs/` 提升为源码根目录 | 改用 PyPI sdist 解压出的真实项目根目录重跑预检 |
| 2 | wheel 输出到 `/tmp` 失败 | 当前环境 `/tmp` 只读 | 使用 `$TMPDIR` 与 Conan `build_folder` |

## 源码修改
无源码修改、无补丁。

## 依赖版本
- Python 3.12
- flit_core >=2,<4（上游 pyproject.toml 构建依赖）
- pytest（仅用于上游测试，不是运行时依赖）

## 验证结果
```text
python3 -m unittest discover -s tests -p 'test_*.py' -v
14 passed, 1 warning in 12.54s

python3 -m pip wheel --no-deps -w $TMPDIR/ptyprocess-wheel .
ptyprocess-0.7.0-py2.py3-none-any.whl generated successfully
```

## 测试统计
- 上游测试：5 个测试文件，14/14 通过，未修改上游测试。
- 适配新增：1 个消费者测试文件 `test_package/smoke.py`，覆盖 import、`PtyProcess` 和 `PtyProcessUnicode` 的真实子进程交互；另新增独立 `test_package/test_ohos.py` 鸿蒙专用测试，仅在 OHOS/HarmonyOS Python 运行时执行，验证 PTY 输出与退出状态。

## 注意事项
- 运行时需要支持 POSIX PTY 的 Python 环境；Conan 包通过 `PYTHONPATH` 注入安装路径。
- `bc` 缺失时，上游 `test_spawn.py` 中的两个条件测试会跳过；本次环境完整套件仍为 14/14 通过。
---

**编译结束**: 2026-09-08 02:09
**最终状态**: built

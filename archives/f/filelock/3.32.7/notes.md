# filelock 3.32.7 — 适配笔记

## 概述
- 上游: https://github.com/tox-dev/py-filelock（PyPI sdist 3.32.7）
- 类型: 纯 Python src/ 布局包，零运行时依赖（仅 stdlib）
- License: MIT
- SHA-256 (PyPI sdist): 37b8a3d9811b0f9aef7e5ec5c71bb320de52df51e6ca9bcd6f5ad81187660da7

## 适配要点
1. copytree staging → lib/python3.12/site-packages/filelock（WR-008 模式）。
2. 无源码补丁：模块仅用 os/sys/pathlib/threading，Python 3.12 无兼容问题。
3. R38: 无 console_scripts、无 bin/ 产物 → 纯库包，不创建 commands.json。
4. 作为 cachecontrol[filecache]（filelock>=3.8.0）与 lastversion 依赖闭包移植。

## 上游测试（设备实测 2026-09-26）
- 入口: `python3 -m pytest tests/`；pytest 9.1.1 + conan 闭包实测：
  901 passed / 235 failed / 66 skipped / 307 errors（4 分 27 秒）。
- 归因: 失败与错误全部因测试专用插件缺失（pytest-asyncio/pytest-mock 未安装；
  test_virtualenv.py 另需 virtualenv，--ignore 排除）；同步非 mock 锁语义用例
  全部通过，未见实现缺陷信号。日志见 run 证据 dep-upstream/upstream-filelock.log。
- 等效验证: test_package 消费者测试覆盖锁核心语义。

## 环境
- Python 3.12.9, Conan 2.x, profile ohos-aarch64

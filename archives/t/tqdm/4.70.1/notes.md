# tqdm 4.70.1 — 适配笔记

## 概述
- 上游: https://github.com/tqdm/tqdm（PyPI sdist 4.70.1）
- 类型: 纯 Python 包，非 Windows 平台零运行时依赖（colorama 仅 Windows）
- License: MPL-2.0 AND MIT
- SHA-256 (PyPI sdist): cefd0eca11b2a37a3aee776544d4f4ae913f02688135b5556b8788dfa474afc4

## 适配要点
1. copytree staging → lib/python3.12/site-packages/tqdm（WR-008 模式），无源码补丁。
2. 已知上游差异：sdist 内模块 __version__ 报 4.70.0（上游 bump 遗漏，PKG-INFO 为
   4.70.1）——消费测试按 4.70 系列断言，差异如实记录。
3. 上游 console_scripts 入口 tqdm（tqdm.cli:main）未承载：lastversion 只消费
   tqdm.tqdm/trange 库 API；不伪造工具面，无 commands.json。

## 上游测试（设备实测 2026-09-26）
- 入口: `python3 -m pytest tests/`（需 -o addopts= 清空 pyproject 的
  --asyncio-mode=strict）；实测 158 passed / 10 failed / 11 skipped（37.6 秒）。
- 归因: 9 例 asyncio 用例缺 pytest-asyncio；1 例 test_pipes 因 toybox PATH 无
  'ls'（FileNotFoundError）——环境/测试依赖归因，非实现缺陷。
- 日志见 run 证据 dep-upstream/upstream-tqdm.log。
- 等效验证: test_package 消费者测试（非 TTY 流降级、format_meter、update）。

## 环境
- Python 3.12.9, Conan 2.x, profile ohos-aarch64

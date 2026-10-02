# feedparser 6.0.11 — 适配笔记

## 概述
- 上游: https://github.com/kurtmckee/feedparser（PyPI sdist 6.0.11）
- 类型: 纯 Python 包，唯一运行依赖 sgmllib3k
- License: BSD-3-Clause
- SHA-256 (PyPI sdist): c9d0407b64c6f2a065d0ebb292c2b35c01050cc0dc33757461aaabdc4c4184d5

## 适配要点
1. copytree staging → lib/python3.12/site-packages/feedparser（WR-008 模式），
   无源码补丁。
2. 选版说明：6.0.11 是最后以 sgmllib3k 为依赖的系列（6.0.12+ 改依赖
   feedparser-sgmllib）；lastversion 3.6.12 的依赖生态按 sgmllib3k 闭包适配。
3. R38: 纯库无 commands.json。

## 上游测试（设备实测 2026-09-26）
- 入口: `python3 tests/runtests.py`（sdist 的 tests/ 为 corpus+unittest harness，
  无 test_*.py，pytest 收集 0）；实测 4343 用例 4341 passed / 2 failed（14.5 秒）。
- 归因: 2 失败为同一 corpus 用例（xml_declaration_unexpected_character）的
  strict/loose 双跑，sgmllib3k 1.0.0 end_title 属性路由与 LooseFeedParser 预期
  不一致的边缘 sanitize 场景；其余全部通过。
- 日志见 run 证据 dep-upstream/upstream-feedparser.log。
- 等效验证: test_package 消费者测试（离线 parse + sgmllib3k 联动）。

## 环境
- Python 3.12.9, Conan 2.x, profile ohos-aarch64

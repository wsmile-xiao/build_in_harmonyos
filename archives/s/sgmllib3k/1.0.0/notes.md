# sgmllib3k 1.0.0 — 适配笔记

## 概述
- 上游: https://pypi.org/project/sgmllib3k/（无独立 VCS 仓，PyPI 为官方发布渠道）
- 类型: 纯 Python 单模块（sgmllib.py），零运行时依赖（仅 re/string/io stdlib）
- License: BSD（upstream setup.py classifier）
- SHA-256 (PyPI sdist): 7868fb1c8bfa764c1ac563d3cf369c381d1325d36124933a726f29fcdaa812e9

## 适配要点
1. copy2 sgmllib.py → lib/python3.12/site-packages/（appdirs 单模块模式），无补丁。
2. R38: 纯库包，无 commands.json。
3. 作为 feedparser 6.0.x 的唯一运行依赖移植（6.0.12+ 上游改依赖 feedparser-sgmllib，
   lastversion 3.6.12 生态按 sgmllib3k 闭包适配）。

## 上游测试（NO_UPSTREAM_TESTS）
- 已核验 sdist 内容：仅 sgmllib.py + setup 元数据，无 tests/ 目录、无测试声明。
- 测试以消费者测试承载（SGMLParser 子类、事件分发、实体解码——feedparser 使用
  模式同款）。

## 环境
- Python 3.12.9, Conan 2.x, profile ohos-aarch64

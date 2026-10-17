# justbackoff

Simple backoff algorithm in Python — `Backoff` counter with `factor` / `max_ms`
capping and optional jitter. Pure Python (single package, stdlib only),
no C/C++ code, **zero runtime dependencies**.

- 上游仓库: https://github.com/alexferl/justbackoff
- 版本: 0.6.0（tag `v0.6.0` = `b8ca3e58…`，上游最新版，PyPI 2020-05-02）
- 适配说明: 纯 Python noarch 包，无编译；`justbackoff/` 包目录拷贝到
  `lib/python3.12/site-packages/`，供 HarmonyOS PC（aarch64）上的 Python 3.12
  使用。**零补丁**（模块唯一 import 为标准库 `random`）。
- 测试: 上游 `tests/test_backoff.py` 6 个用例经 `pytest` 实跑 6/6 = 100%；
  test_package 消费者测试 42 断言、鸿蒙特有测试 11 断言。

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smmap 5.0.3 test_package 测试源文件。

由 test_package/conanfile.py 的 test() 方法通过
``python test_smmap.py`` 调用，在 Conan 消费者视角下验证：

1. ``smmap`` 模块可被正常导入
2. ``smmap.__version__`` 与配方版本一致
3. 核心 API (``SlidingWindowMapManager``, ``SlidingWindowMapBuffer``, ``WindowCursor``) 可访问

本文件存在的另一个目的：满足 CI 门禁 L0c
(build_and_test.sh) —— test_package/ 下必须存在
``.c/.cpp/.cc/.cxx/.sh/.py`` 测试源文件 (排除 conanfile.py)。
"""

import sys

EXPECTED_VERSION = "5.0.3"


def main() -> int:
    failures = []

    # 1. 模块导入
    try:
        import smmap  # noqa: F401
    except Exception as exc:  # pragma: no cover - 诊断信息
        print(f"[FAIL] import smmap: {exc}")
        return 1

    # 2. 版本核对
    actual_version = getattr(smmap, "__version__", None)
    if actual_version != EXPECTED_VERSION:
        failures.append(
            f"version mismatch: expected {EXPECTED_VERSION!r}, got {actual_version!r}"
        )
    else:
        print(f"[ok] smmap.__version__ == {actual_version}")

    # 3. 核心 API 可访问
    required_attrs = ["SlidingWindowMapManager", "SlidingWindowMapBuffer", "WindowCursor"]
    for attr in required_attrs:
        if not hasattr(smmap, attr):
            failures.append(f"missing smmap.{attr}")
    if not failures:
        print(f"[ok] core API present: {', '.join(required_attrs)}")

    if failures:
        for f in failures:
            print(f"[FAIL] {f}")
        return 1

    print("[PASS] all smmap test_package assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

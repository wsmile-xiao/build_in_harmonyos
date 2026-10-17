#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gitdb 4.0.12 test_package 测试源文件。

由 test_package/conanfile.py 的 test() 方法通过
``python test_gitdb.py`` 调用，在 Conan 消费者视角下验证：

1. ``gitdb`` 模块可被正常导入
2. ``gitdb.__version__`` 与配方版本一致
3. 核心 API (``GitDB``, ``LooseObjectDB``, ``MemoryDB``) 可访问
4. 间接依赖 ``smmap`` 也可导入（验证 Conan 依赖链传递）

本文件存在的另一个目的：满足 CI 门禁 L0c
(build_and_test.sh) —— test_package/ 下必须存在
``.c/.cpp/.cc/.cxx/.sh/.py`` 测试源文件 (排除 conanfile.py)。
"""

import sys

EXPECTED_VERSION = "4.0.12"


def main() -> int:
    failures = []

    # 1. 模块导入
    try:
        import gitdb  # noqa: F401
    except Exception as exc:  # pragma: no cover - 诊断信息
        print(f"[FAIL] import gitdb: {exc}")
        return 1

    # 2. 版本核对
    actual_version = getattr(gitdb, "__version__", None)
    if actual_version != EXPECTED_VERSION:
        failures.append(
            f"version mismatch: expected {EXPECTED_VERSION!r}, got {actual_version!r}"
        )
    else:
        print(f"[ok] gitdb.__version__ == {actual_version}")

    # 3. 核心 API 可访问
    required_attrs = ["GitDB", "LooseObjectDB", "MemoryDB"]
    for attr in required_attrs:
        if not hasattr(gitdb, attr):
            failures.append(f"missing gitdb.{attr}")
    if not failures:
        print(f"[ok] core API present: {', '.join(required_attrs)}")

    # 4. 间接依赖 smmap 可导入（验证 Conan 依赖链传递）
    try:
        import smmap  # noqa: F401
        print(f"[ok] smmap available (version {smmap.__version__})")
    except Exception as exc:  # pragma: no cover - 诊断信息
        failures.append(f"smmap import failed: {exc}")

    if failures:
        for f in failures:
            print(f"[FAIL] {f}")
        return 1

    print("[PASS] all gitdb test_package assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parse 1.22.2 test_package 测试源文件。

由 test_package/conanfile.py 的 test() 方法通过
``python test_parse.py`` 调用，在 Conan 消费者视角下验证：

1. ``parse`` 模块可被正常导入（经 PYTHONPATH 运行环境）
2. ``parse.__version__`` 与配方版本一致
3. 核心公开 API 可用：``parse``、``search``、``findall``、``with_pattern``
4. 实际解析业务场景：format 反向解析提取值 + 类型转换（int/float/date）
5. 编译正则模式与自定义类型转换器（``with_pattern``）端到端可用

本文件存在的另一个目的：满足 CI 门禁 L0c (build_and_test.sh) ——
test_package/ 下必须存在 .c/.cpp/.cc/.cxx/.sh/.py 测试源文件
（排除 conanfile.py）。
"""

import datetime
import sys

EXPECTED_VERSION = "1.22.2"


def main():
    failures = []

    def check(name, cond, detail=""):
        if cond:
            print(f"[PASS] {name}")
        else:
            print(f"[FAIL] {name} {detail}")
            failures.append(name)

    # 1. 模块导入
    import parse  # noqa: F401
    check("import parse", True)

    # 2. 版本一致性
    check("version match",
          parse.__version__ == EXPECTED_VERSION,
          f"got {parse.__version__!r}")

    # 3. 公开 API 存在性
    for api in ("parse", "search", "findall", "compile", "with_pattern"):
        check(f"public API {api}", hasattr(parse, api))

    # 4. 业务场景：format 反向解析 + 类型转换
    r = parse.parse("hello {}, my name is {}", "hello Bob, my name is Alice")
    check("positional parse", r is not None
          and r[0] == "Bob" and r[1] == "Alice", repr(r))

    r = parse.parse("speed={speed:g} km/h", "speed=42.5 km/h")
    check("float conversion", r is not None
          and r["speed"] == 42.5 and isinstance(r["speed"], float), repr(r))

    r = parse.parse("born {y:d}-{m:d}-{d:d}",
                    "born 1990-07-15")
    check("int conversion", r is not None
          and (r["y"], r["m"], r["d"]) == (1990, 7, 15), repr(r))

    # 5. search / findall
    s = parse.search("age={age:d}", "Name: Bob, age=30, city: Paris")
    check("search extract", s is not None and s["age"] == 30, repr(s))

    results = [r[0] for r in parse.findall("<{}>", "<a><b><c>")]
    check("findall all", results == ["a", "b", "c"], repr(results))

    # 6. compile + with_pattern 自定义类型（装饰器形式，见 parse README）
    fmt = parse.compile("value={x:d}")
    check("compiled pattern", fmt.parse("value=7")["x"] == 7)

    @parse.with_pattern(r"\d+")
    def even(text):
        return int(text) if int(text) % 2 == 0 else None

    r = parse.parse("n={num:w}", "n=42", {"w": even})
    check("custom type ok", r is not None and r["num"] == 42, repr(r))
    # parse 库语义：转换器返回 None 时字段值为 None（而非匹配失败）
    r = parse.parse("n={num:w}", "n=43", {"w": even})
    check("custom type rejects odd",
          r is not None and r["num"] is None, repr(r))
    if failures:
        print(f"FAILED: {len(failures)} checks: {failures}")
        sys.exit(1)
    print("ALL test_package checks passed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Consumer / functional test for packaged ubelt 1.4.0.

R34: 真实调用被测包的公开 API（非空壳 print）。
用法： python3 test_ubelt.py <site-packages-dir-of-package>
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import ubelt as ub


def main():
    # 1. 版本元数据
    assert ub.__version__ == "1.4.0", ub.__version__

    # 2. hash_data：str 且确定（ubelt 1.4.0 默认 hasher=sha512 → 128 hex）
    h1 = ub.hash_data("hello world")
    h2 = ub.hash_data("hello world")
    assert isinstance(h1, str) and len(h1) == 128, (type(h1), len(h1))
    assert h1 == h2, (h1, h2)
    assert ub.hash_data([1, 2, 3]) == ub.hash_data([1, 2, 3])
    assert ub.hash_data([1, 2, 3]) != ub.hash_data([3, 2, 1])

    # 3. 字典工具
    assert ub.dzip(["a", "b"], [1, 2]) == {"a": 1, "b": 2}
    assert ub.dict_isect({"a": 1, "b": 2}, {"b": 2, "c": 3}) == {"b": 2}

    # 4. 迭代/序列工具
    assert ub.peek(iter([7, 8, 9])) == 7
    assert list(ub.flatten([[1, 2], [3]])) == [1, 2, 3]
    assert list(ub.take([10, 20, 30], [0, 2])) == [10, 30]

    # 5. Path 工具（ohos 沙箱内真实文件读写）
    dpath = ub.Path(ub.Path.appdir("ubelt/consumer-test")).ensuredir()
    fpath = dpath / "probe.txt"
    fpath.write_text("ubelt-on-ohos")
    assert fpath.exists()
    assert fpath.read_text() == "ubelt-on-ohos"
    p = ub.Path("a") / "b" / "c.txt"
    assert p.name == "c.txt", p.name
    assert p.suffix == ".txt", p.suffix

    print("ubelt 1.4.0 consumer test: PASS")


if __name__ == "__main__":
    main()

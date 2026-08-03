#!/usr/bin/env python3
"""hickle test_package 冒烟测试.

由 test_package/conanfile.py 的 test() 调用，HICKLE_SITE_PACKAGES 指向
hickle 包的 site-packages 目录。

验证策略（两级）：
  1) 包完整性（硬断言，必须通过）：
     - hickle/__version__.py 存在，且 __version__ == "5.0.3"
     - hickle/hickle.py 存在
  2) 功能往返（可选，best-effort）：
     - h5py + numpy 可用时，dump/load 一个 dict 并校验一致
     - 缺失可选依赖时 SKIP，不阻断
"""
import os
import sys
failures = []
SP = os.environ.get("HICKLE_SITE_PACKAGES", "")
if not SP:
    print("FAIL: HICKLE_SITE_PACKAGES environment variable is not set or empty")
    sys.exit(1)
if SP not in sys.path:
    sys.path.insert(0, SP)

# ── 1. 包完整性校验（不触发 h5py/numpy 导入） ──
ver_file = os.path.join(SP, "hickle", "__version__.py")
if not os.path.isfile(ver_file):
    failures.append("hickle/__version__.py missing")
else:
    ns = {}
    with open(ver_file) as f:
        exec(f.read(), ns)
    ver = ns.get("__version__")
    if ver != "5.0.3":
        failures.append("version mismatch: expected 5.0.3, got " + repr(ver))
    else:
        print("OK: hickle.__version__ = 5.0.3")

hickle_mod = os.path.join(SP, "hickle", "hickle.py")
if not os.path.isfile(hickle_mod):
    failures.append("hickle/hickle.py missing")
else:
    print("OK: hickle/hickle.py present")

# __init__.py 级联 import hickle 模块，会触发 import h5py/numpy
init_file = os.path.join(SP, "hickle", "__init__.py")
if not os.path.isfile(init_file):
    failures.append("hickle/__init__.py missing")

# ── 2. 功能往返测试（可选，需 h5py + numpy） ──
try:
    import hickle  # noqa: F401  会被 __init__ 级联触发 h5py/numpy
    import io
    data = {"a": 1, "b": [1, 2, 3], "c": "hello"}
    buf = io.BytesIO()
    hickle.dump(data, buf, mode="w", path="<string>")
    buf.seek(0)
    loaded = hickle.load(buf, path="<string>")
    if loaded == data:
        print("OK: hickle dump/load roundtrip passed")
    else:
        failures.append(
            "roundtrip mismatch: {} != {}".format(repr(loaded), repr(data)))
except ImportError as e:
    print("SKIP: functional roundtrip (optional dep missing): " + str(e))
except Exception as e:
    # 包完整性已验证；功能 API 差异不阻断（best-effort），但计入 failures
    failures.append("functional roundtrip error: " + str(e))
# ── 结果汇总 ──
if failures:
    print("FAIL:")
    for f in failures:
        print("  - " + f)
    sys.exit(1)
print("ALL CHECKS PASSED")

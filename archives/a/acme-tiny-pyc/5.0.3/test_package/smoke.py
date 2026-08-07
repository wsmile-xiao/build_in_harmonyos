#!/usr/bin/env python3
"""acme-tiny-pyc 5.0.3 test_package 断言脚本（test_package 测试源，L0c 要求）。

由 test_package/conanfile.py 的 test() 调用；PYTHONPATH 由调用方注入包内
site-packages。断言点（对应 MANIFEST.yml assertion_count 中 test_package 部分）：
  1. import acme_tiny 且 main/get_crt 可调用
  2. 包内存在预编译 .pyc（__pycache__/acme_tiny.cpython-*.pyc）
  3. 包内 acme_tiny.py 与 .pyc 并存（独立包自包含策略）
  4. 直接从 .pyc 加载模块并确认 main/get_crt 可调用
  （CLI 断言 `acme-tiny -h` 由 test_package/conanfile.py 的 test() 单独执行）
"""
import glob
import importlib.util
import os
import sys

failures = []

# 1) import acme_tiny（关键入口）
try:
    import acme_tiny
    assert callable(acme_tiny.main), "acme_tiny.main not callable"
    assert callable(acme_tiny.get_crt), "acme_tiny.get_crt not callable"
    print("PASS import acme_tiny (main/get_crt callable)")
except Exception as exc:  # pragma: no cover
    failures.append("import acme_tiny failed: %s" % exc)

# 2) .pyc 存在（acme-tiny-pyc 的本质）
site_packages = os.environ.get("PYTHONPATH", "").split(os.pathsep)[0]
pycache = os.path.join(site_packages, "__pycache__")
pycs = sorted(glob.glob(os.path.join(pycache, "acme_tiny.cpython-*.pyc")))
if pycs:
    print("PASS .pyc present:", os.path.basename(pycs[0]))
else:
    failures.append("missing acme_tiny.cpython-*.pyc in " + pycache)

# 3) .py 与 .pyc 并存（独立包策略：保留运行所需模块文件 + 额外预编译 bytecode）
if os.path.isfile(os.path.join(site_packages, "acme_tiny.py")):
    print("PASS acme_tiny.py present (self-contained)")
else:
    failures.append("missing acme_tiny.py in " + site_packages)

# 4) pyc 直接加载并确认关键入口
if pycs:
    try:
        spec = importlib.util.spec_from_file_location("acme_tiny", pycs[0])
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert callable(mod.main) and callable(mod.get_crt)
        print("PASS pyc direct load (main/get_crt callable):",
              os.path.basename(pycs[0]))
    except Exception as exc:  # pragma: no cover
        failures.append("pyc direct load failed: %s" % exc)

if failures:
    for item in failures:
        print("FAIL:", item)
    sys.exit(1)
print("ALL test_package assertions passed")

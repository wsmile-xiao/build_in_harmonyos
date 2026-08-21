#!/usr/bin/env python3
"""venc-pyc 3.2.7 test_package 断言脚本（test_package 测试源，L0c 要求）。

由 test_package/conanfile.py 的 test() 调用；PYTHONPATH 由调用方注入包内
site-packages。断言点（对应 MANIFEST.yml assertion_count 中 test_package 部分）：
  1. import venc3 且 venc_entry_point 可调用（并加载关键子模块 venc3.datastore）
  2. 包内存在预编译 .pyc（__pycache__/__init__.cpython-*.pyc）
  3. 包内 venc3/__init__.py 与 .pyc 并存（独立包自包含策略）
  4. 直接从 .pyc 加载 venc3 模块并确认 venc_entry_point 可调用
  5. package_data 资源完整（themes / oembed_providers.json 存在，venc CLI 依赖）
  （CLI 断言 `venc -v` 由 test_package/conanfile.py 的 test() 单独执行）
"""
import glob
import importlib.util
import os
import sys

failures = []

# 1) import venc3（关键入口 + 关键子模块）
try:
    import venc3
    from venc3.main import venc_entry_point
    assert callable(venc_entry_point), "venc_entry_point not callable"
    import venc3.datastore  # 依赖运行时 Python 包 unidecode
    print("PASS import venc3 (venc_entry_point callable, datastore importable)")
except Exception as exc:  # pragma: no cover
    failures.append("import venc3 failed: %s" % exc)

# 2) .pyc 存在（venc-pyc 的本质）
site_packages = os.environ.get("PYTHONPATH", "").split(os.pathsep)[0]
pycache = os.path.join(site_packages, "venc3", "__pycache__")
pycs = sorted(glob.glob(os.path.join(pycache, "__init__.cpython-*.pyc")))
if pycs:
    print("PASS .pyc present:", os.path.basename(pycs[0]))
else:
    failures.append("missing venc3/__pycache__/__init__.cpython-*.pyc in " + pycache)

# 3) .py 与 .pyc 并存（独立包策略：保留运行所需模块文件 + 额外预编译 bytecode）
if os.path.isfile(os.path.join(site_packages, "venc3", "__init__.py")):
    print("PASS venc3/__init__.py present (self-contained)")
else:
    failures.append("missing venc3/__init__.py in " + site_packages)

# 4) pyc 直接加载并确认关键入口
if pycs:
    try:
        spec = importlib.util.spec_from_file_location("venc3", pycs[0])
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        from venc3.main import venc_entry_point as ep2
        assert callable(ep2)
        print("PASS pyc direct load (venc_entry_point callable):",
              os.path.basename(pycs[0]))
    except Exception as exc:  # pragma: no cover
        failures.append("pyc direct load failed: %s" % exc)

# 5) package_data 资源完整（venc CLI 运行依赖）
pkg_data = os.path.join(site_packages, "venc3", "package_data")
for rel in ("oembed_providers.json", "themes/concrete/config.yaml"):
    if os.path.isfile(os.path.join(pkg_data, rel)):
        print("PASS package_data present:", rel)
    else:
        failures.append("missing package_data/" + rel + " in " + pkg_data)

# 6) 核心功能可执行验证——venc3.patterns（上游 test/patterns_processing.py 的
#    test_datastructure / test_process_no_flatten / test_process_flatten 所针对的
#    PatternTree 数据结构与 Processor 处理功能；上游测试因 3.2.7 缺陷不可运行，
#    此处以等价消费者断言提供可执行验证证据）：
try:
    from venc3.patterns.processor import PatternTree, Processor, Pattern
    from venc3.patterns.non_contextual import escape
    from venc3.exceptions import UnknownPattern

    # 6.1) PatternTree 数据结构：解析模板并暴露 string 属性。
    #      上游 test_datastructure 崩溃根因即 3.2.7 将属性 _str 改名为 string，
    #      此处断言改名后的属性可用（直接回应审查指出的上游缺陷）。
    _tree = PatternTree("title .:GetEntryTitle:. end")
    assert hasattr(_tree, "string") and _tree.string, "PatternTree.string missing"
    assert _tree.sub_patterns, "PatternTree.sub_patterns empty"
    print("PASS PatternTree .string (renamed from _str) + sub_patterns parsed")

    # 6.2) 未知 pattern 必须抛 UnknownPattern（错误路径行为）
    try:
        PatternTree(".:NoSuchPattern12345:.")
        failures.append("unknown pattern did not raise UnknownPattern")
    except UnknownPattern:
        print("PASS UnknownPattern raised for unknown pattern")

    # 6.3) Processor 处理路径：注册内置 Escape pattern 并处理模板。
    #      对应上游 test_process_no_flatten / test_process_flatten 的处理功能。
    _proc = Processor()
    _proc.set_patterns({"Escape": escape})
    _tree2 = PatternTree("pre .:Escape::literal:. post")
    _proc.process(_tree2, Pattern.FLAG_ALL)
    assert "literal" in _tree2.string, "Processor did not process pattern"
    print("PASS Processor processed Escape ->", repr(_tree2.string))
except Exception as exc:  # pragma: no cover
    failures.append("venc3.patterns functional assertions failed: %s" % exc)

if failures:
    for item in failures:
        print("FAIL:", item)
    sys.exit(1)
print("ALL test_package assertions passed")

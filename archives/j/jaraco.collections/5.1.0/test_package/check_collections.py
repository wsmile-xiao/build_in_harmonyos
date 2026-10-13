#!/usr/bin/env python3
"""Consumer checks for the jaraco.collections package.

usage: check_collections.py <package-folder> <more-itertools-package-folder>

Checks (every one of them inspects the packaged artefacts):
  1. both site-packages directories exist (this package + the more-itertools
     runtime dependency).
  2. `import jaraco.collections` works AND the imported module really comes from
     this package's site-packages (not from some system installation).
  3. the three **bundled** runtime dependencies import and also come from this
     package's site-packages — i.e. the jaraco.* namespace packages merged
     correctly (jaraco.collections imports jaraco.text at import time).
  4. real API calls with asserted results: FrozenDict / DictStack / Projection /
     invert_map.
  5. FoldedCaseKeyedDict: case-folded lookup — this one specifically proves the
     bundled jaraco.text is actually used (it calls jaraco.text.FoldedCase).

（所有断言值均已在本地用解包后的源码 + 三个捆绑依赖跑通，再写进本脚本。）
"""
import os
import sys

fails = []
skips = []


def fail(msg):
    fails.append(msg)
    print("[FAIL] %s" % msg)


def ok(msg):
    print("[ok]   %s" % msg)


def skip(msg):
    skips.append(msg)
    print("[skip] %s" % msg)


def check_sites(pkg, mi):
    missing = [p for p in (pkg, mi) if not os.path.isdir(p)]
    if missing:
        fail("site-packages 目录缺失：%s" % ", ".join(missing))
        return False
    ok("两个 site-packages 均存在（包内 + more-itertools 依赖）")
    return True


def check_import(pkg):
    try:
        import jaraco.collections as mod
    except Exception as exc:  # noqa: BLE001
        fail("import jaraco.collections 失败：%s" % exc)
        return None
    real = os.path.realpath(os.path.dirname(mod.__file__))
    _pkg_root = os.path.realpath(pkg)
    if not (real == _pkg_root or real.startswith(_pkg_root + os.sep)):
        fail("导入到的 jaraco.collections 不在本包内：%s" % real)
        return None
    ok("import jaraco.collections 成功且来自本包（%s）" % real)
    return mod


def check_bundled(pkg):
    good = 0
    for name in ("jaraco.text", "jaraco.functools", "jaraco.context"):
        try:
            __import__(name)
            mod = sys.modules[name]
        except Exception as exc:  # noqa: BLE001
            fail("捆绑依赖 %s 无法导入：%s" % (name, exc))
            continue
        real = os.path.realpath(os.path.dirname(mod.__file__))
        _pkg_root = os.path.realpath(pkg)
        if not (real == _pkg_root or real.startswith(_pkg_root + os.sep)):
            fail("捆绑依赖 %s 不在本包内：%s" % (name, real))
            continue
        good += 1
    if good == 3:
        ok("3 个捆绑运行期依赖（jaraco.text / jaraco.functools / jaraco.context）"
           "均从本包 site-packages 导入 —— jaraco.* 命名空间合并成功")


def check_api(mod):
    if mod is None:
        return
    cases = []
    try:
        cases.append(("FrozenDict", mod.FrozenDict({"a": 1})["a"], 1))
    except Exception as exc:  # noqa: BLE001
        fail("FrozenDict 调用异常：%s" % exc)
    try:
        cases.append(("DictStack", mod.DictStack([{"a": 1}])["a"], 1))
    except Exception as exc:  # noqa: BLE001
        fail("DictStack 调用异常：%s" % exc)
    try:
        # Projection 的语义是「把一组键投影到另一个 mapping 上」（签名 Projection(keys, space)），
        # 并不对值施加函数 —— 依据 jaraco/collections/__init__.py 的 docstring 示例
        cases.append(("Projection(dict)",
                      dict(mod.Projection(["a", "c"], {"a": 1, "b": 2, "c": 3})),
                      {"a": 1, "c": 3}))
    except Exception as exc:  # noqa: BLE001
        fail("Projection 调用异常：%s" % exc)
    try:
        cases.append(("invert_map", mod.invert_map({"a": "b"}), {"b": "a"}))
    except Exception as exc:  # noqa: BLE001
        fail("invert_map 调用异常：%s" % exc)
    bad = [(n, got, want) for n, got, want in cases if got != want]
    if bad:
        for n, got, want in bad:
            fail("%s 结果不符：得到 %r，期望 %r" % (n, got, want))
        return
    ok("真实 API 调用通过：%s" % ", ".join(n for n, _g, _w in cases))


def check_folded_case(mod):
    if mod is None:
        return
    try:
        d = mod.FoldedCaseKeyedDict()
        d["Foo Bar"] = 1
        got = d["foo bar"]
        contains = "FOO BAR" in d
    except Exception as exc:  # noqa: BLE001
        fail("FoldedCaseKeyedDict 调用异常（捆绑的 jaraco.text 可能未生效）：%s" % exc)
        return
    if got != 1 or not contains:
        fail("FoldedCaseKeyedDict 大小写折叠行为不符：d['foo bar']=%r, 'FOO BAR' in d=%r"
             % (got, contains))
        return
    ok("FoldedCaseKeyedDict 大小写折叠查找正确 —— 证明捆绑的 jaraco.text 被真正使用")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    pkg_root, mi_root = sys.argv[1:3]
    pkg = os.path.join(pkg_root, "lib", "python3", "site-packages")
    mi = os.path.join(mi_root, "lib", "python3", "site-packages")
    if not check_sites(pkg, mi):
        print("checks=%d fails=%d skips=%d" % (5, len(fails), len(skips)))
        print("RESULT: FAIL")
        return 1
    for path in (mi, pkg):          # more-itertools 优先，再是本包（含捆绑依赖）
        sys.path.insert(0, path)
    mod = check_import(pkg)
    check_bundled(pkg)
    check_api(mod)
    check_folded_case(mod)
    print("checks=%d fails=%d skips=%d" % (5, len(fails), len(skips)))
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

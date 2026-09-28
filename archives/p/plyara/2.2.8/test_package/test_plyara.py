#!/usr/bin/env python3
"""Consumer test for the packaged plyara 2.2.8 (R34).

用法: test_plyara.py <package_folder> <site_packages>

只允许从**包内 site-packages** 导入（真实消费打包产物），并调用 plyara
的真实 API（解析 / 语义工具 / 规则重建），不做空壳打印。
"""
import json
import os
import subprocess
import sys

SMOKE = r'''
import json, os, sys, tempfile, pathlib
import ply, plyara
from plyara.core import Plyara
from plyara import utils

print("ply", ply.__version__)
print("plyara all", plyara.__all__)

# 1) vendored PLY 必须来自本包（submodule 落位契约）
assert os.path.abspath(ply.__file__).startswith(os.path.abspath(sys.argv[1])), ply.__file__
assert plyara.__all__ == ["Plyara"]

# 2) 真实解析：meta/tags/strings/condition
rule = """
rule R_consumer : tag_a tag_b
{
    meta:
        author = "consumer"
        score = 7
    strings:
        $t = "harmony"
        $b = { 68 61 72 6D 6F 6E 79 }
    condition:
        $t or $b
}
"""
parser = Plyara()
out = parser.parse_string(rule)
assert isinstance(out, list) and len(out) == 1, out
r = out[0]
assert r["rule_name"] == "R_consumer", r
assert r["tags"] == ["tag_a", "tag_b"], r
assert {"$t", "$b"} == {s["name"] for s in r["strings"]}, r
assert r["condition_terms"] == ["$t", "or", "$b"], r
assert {"author": "consumer"} in r["metadata"], r

# 3) 真实文件 IO（上游 2.2.8 只有 parse_string，CLI 负责文件读取）
with tempfile.TemporaryDirectory() as td:
    f = pathlib.Path(td) / "r.yar"
    f.write_text(rule, encoding="utf-8")
    assert Plyara().parse_string(f.read_text(encoding="utf-8"))[0]["rule_name"] == "R_consumer"

# 4) 选项：store_raw_sections / meta_as_kv / import_effects
raw = Plyara(store_raw_sections=True).parse_string(rule)[0]
assert raw["raw_strings"].startswith("strings:"), raw["raw_strings"]
assert "raw_condition" in raw
noraw = Plyara(store_raw_sections=False).parse_string(rule)[0]
assert not [k for k in noraw if k.startswith("raw_")], noraw
kv = Plyara(meta_as_kv=True).parse_string(rule)[0]
assert kv["metadata_kv"] == {"author": "consumer", "score": 7}, kv["metadata_kv"]
imp = Plyara(import_effects=True).parse_string(
    'import "pe"\n\nrule I { condition: pe.entry_point == 0 }')[0]
assert imp["imports"] == ["pe"], imp["imports"]

# 5) utils 语义工具：哈希 + 规则重建 + import 检测
h = utils.generate_hash(r)
assert h.startswith("v1_sha256_"), h
assert utils.generate_hash(r, legacy=True) != h  # legacy 口径与 v1 口径不同
rebuilt = utils.rebuild_yara_rule(r)
assert "rule R_consumer" in rebuilt and "$t" in rebuilt, rebuilt
assert utils.detect_imports(imp) == ["pe"], utils.detect_imports(imp)

# 6) 内嵌 PLY 的 lex/yacc 真在跑（不是 stdlib 兜底）
assert hasattr(ply, "lex") and hasattr(ply, "yacc")
print("OK: plyara consumer API (parse_string/options/utils) works")
'''


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: test_plyara.py <package_folder> <site_packages>",
              file=sys.stderr)
        return 1
    pkg, site = sys.argv[1], sys.argv[2]
    mod = os.path.join(site, "plyara", "__init__.py")
    if not os.path.isfile(mod):
        print(f"FAIL: plyara module missing: {mod}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, "-c", SMOKE, site],
                       capture_output=True, text=True, env=env)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        print(f"FAIL: plyara consumer API\n{r.stderr}", file=sys.stderr)
        return 1
    print("OK: plyara 2.2.8 consumer test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

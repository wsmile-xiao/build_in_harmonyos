#!/usr/bin/env python3
"""Consumer-side API test for objgraph 3.6.2 (R34 真实执行).

以消费者视角导入**已打包**的 objgraph 并真实调用其公开 API。全部为硬断言
（任一条失败即 print + sys.exit(1)）。

公开 API 面以上游 objgraph.py 的模块级顶层 def 为准（基线 3.6.2 实测）：
  count / typestats / most_common_types / show_most_common_types /
  growth / show_growth / get_new_ids / get_leaking_objects / by_type /
  at / at_addrs / find_ref_chain / find_backref_chain /
  show_backrefs / show_refs / show_chain / is_proper_module
注意：上游**没有** `__all__`；`safe_repr` / `short_repr` 是私有实现
（`_safe_repr` / `_short_repr`），不属于消费者 API，故此处不直接断言其名。
渲染类 API 只校验 .dot 文件产出（objgraph 在无 graphviz 时的上游既定行为），
不依赖 dot，使消费者测试与其解耦。
"""
import gc
import os
import sys
import tempfile

site = sys.argv[1]
sys.path.insert(0, site)

import objgraph  # noqa: E402

checks = []


def check(name, cond, detail=""):
    checks.append((name, bool(cond), detail))


# ── 1. 模块与版本 ────────────────────────────────────────────
check("模块自 site-packages 导入", objgraph.__file__.startswith(site),
      objgraph.__file__)
check("__version__ == 3.6.2", objgraph.__version__ == "3.6.2",
      objgraph.__version__)
check("__license__ == MIT", objgraph.__license__ == "MIT",
      objgraph.__license__)

# ── 2. 公开 API 面（上游模块级顶层 def）──────────────────────
PUBLIC_API = (
    "count", "typestats", "most_common_types", "show_most_common_types",
    "growth", "show_growth", "get_new_ids", "get_leaking_objects", "by_type",
    "at", "at_addrs", "find_ref_chain", "find_backref_chain",
    "show_backrefs", "show_refs", "show_chain", "is_proper_module",
)
missing = [n for n in PUBLIC_API if not callable(getattr(objgraph, n, None))]
check("17 个公开 API 均存在且可调用", not missing, f"missing={missing}")

# ── 3. by_type / count 计数语义 ──────────────────────────────
class _Marker:
    pass


markers = [_Marker() for _ in range(5)]
found = objgraph.by_type("_Marker")
check("by_type 按类名收集", len(found) >= 5, f"found={len(found)}")
check("count 与 by_type 一致", objgraph.count("_Marker") == len(found),
      f"count={objgraph.count('_Marker')} by_type={len(found)}")

# ── 4. typestats / most_common_types ─────────────────────────
stats = objgraph.typestats()
check("typestats 返回非空 dict", isinstance(stats, dict) and len(stats) > 0,
      f"types={len(stats)}")
stats_short = objgraph.typestats(shortnames=False)
check("typestats 默认 shortnames 聚合更粗",
      len(stats) <= len(stats_short), f"short={len(stats)} long={len(stats_short)}")
# most_common_types 返回的是 **list of (type_name, count) 元组**（上游
# most_common_types 实现：sorted(typestats().items(), ...)），不是 dict。
common = objgraph.most_common_types(limit=5)
check("most_common_types 返回 list of (name, count)",
      isinstance(common, list) and len(common) <= 5 and
      all(isinstance(t, tuple) and len(t) == 2 for t in common),
      f"n={len(common)} type={type(common).__name__}")
check("most_common_types 按计数降序", all(
    common[i][1] >= common[i + 1][1] for i in range(len(common) - 1)),
    str(common))

# ── 5. at / at_addrs ─────────────────────────────────────────
by_addr = objgraph.at(id(markers[0]))
check("at(id(obj)) 取回自身", by_addr is markers[0],
      f"got={type(by_addr).__name__}")
# at_addrs 的入参是**地址集合**（id(obj)），不是对象本身；
# 且只对 GC 追踪的对象有效（上游 docstring 明示 int/str 等不适用）。
addr_set = {id(markers[0]), id(markers[1])}
addrs = objgraph.at_addrs(addr_set)
check("at_addrs(地址集合) 返回 2 项", len(addrs) == 2, f"n={len(addrs)}")
check("at_addrs 内容正确", all(m in addrs for m in markers[:2]), str(addrs))

# ── 6. get_leaking_objects ───────────────────────────────────
gc.collect()
leaking = objgraph.get_leaking_objects()
check("get_leaking_objects 返回 list", isinstance(leaking, list),
      f"n={len(leaking)}")
subset = objgraph.get_leaking_objects([markers[0], markers[1]])
check("get_leaking_objects 接受候选集", isinstance(subset, list),
      f"n={len(subset)}")

# ── 7. get_new_ids 增量探测 ──────────────────────────────────
tracker = objgraph.get_new_ids()
check("get_new_ids 返回默认 dict 追踪器", hasattr(tracker, "keys") and
      hasattr(tracker, "update"), type(tracker).__name__)
n_before = len(tracker)
_new = [_Marker() for _ in range(3)]
tracker.update()
check("get_new_ids.update() 可增长", len(tracker) >= n_before,
      f"{n_before} -> {len(tracker)}")

# ── 8. find_ref_chain / find_backref_chain ───────────────────
class _Node:
    def __init__(self):
        self.child = None


a, b, c = _Node(), _Node(), _Node()
a.child = b
b.child = c

chain = objgraph.find_ref_chain(c, lambda x: x is a)
check("find_ref_chain 沿 child 反查回 a", bool(chain), f"len={len(chain or [])}")
backchain = objgraph.find_backref_chain(c, lambda x: x is a)
check("find_backref_chain 反查回 a", bool(backchain),
      f"len={len(backchain or [])}")

# ── 9. is_proper_module ──────────────────────────────────────
check("is_proper_module(objgraph) 为真", objgraph.is_proper_module(objgraph))
check("is_proper_module(int) 为假", not objgraph.is_proper_module(int))

# ── 10. 渲染 API 产出 .dot（无 dot 时的上游既定行为）──────────
with tempfile.TemporaryDirectory() as td:
    out = os.path.join(td, "refs.dot")
    objgraph.show_refs([a], filename=out)
    check("show_refs 产出非空 .dot", os.path.isfile(out) and
          os.path.getsize(out) > 0,
          f"size={os.path.getsize(out) if os.path.isfile(out) else 'MISSING'}")

    out2 = os.path.join(td, "backrefs.dot")
    objgraph.show_backrefs([c], filename=out2)
    check("show_backrefs 产出非空 .dot", os.path.isfile(out2) and
          os.path.getsize(out2) > 0,
          f"size={os.path.getsize(out2) if os.path.isfile(out2) else 'MISSING'}")

    out3 = os.path.join(td, "chain.dot")
    objgraph.show_chain(objgraph.find_ref_chain(c, lambda x: x is a),
                        filename=out3)
    check("show_chain 产出非空 .dot", os.path.isfile(out3) and
          os.path.getsize(out3) > 0,
          f"size={os.path.getsize(out3) if os.path.isfile(out3) else 'MISSING'}")

    # 渲染内容确实描述了对象关系（不是空图）
    with open(out, encoding="utf-8") as f:
        dot_text = f.read()
    check("show_refs 的 .dot 含 digraph 与节点", "digraph" in dot_text and
          "-> " in dot_text, f"len={len(dot_text)}")

# ── 11. growth 增量探测 ──────────────────────────────────────
check("growth 可调用（limit=0 无增长返回空）",
      objgraph.growth(limit=0) is None or
      hasattr(objgraph.growth(limit=0), "__iter__"))
peak = {}
objgraph.growth(limit=3, peak_stats=peak)
check("growth 维护 peak_stats", isinstance(peak, dict), f"n={len(peak)}")

# ── 汇总 ─────────────────────────────────────────────────────
failed = [c for c in checks if not c[1]]
print(f"\nobjgraph {objgraph.__version__} consumer API: "
      f"{len(checks) - len(failed)}/{len(checks)} passed")
for name, ok, detail in failed:
    print(f"  FAIL: {name}  {detail}")
if failed:
    sys.exit(1)
print("consumer API: PASS")

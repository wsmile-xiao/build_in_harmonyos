#!/usr/bin/env python3
"""Smoke test for xapian-bindings 1.4.26.

Verifies that:
1. The `xapian` Python package imports (the C++ extension loads)
2. A WritableDatabase can be created and a document added (functional test)
"""
import sys

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        failures.append(name)


print("[test] import xapian")
try:
    import xapian
    check("xapian import", True)
    check("xapian version", xapian.version_string() == "1.4.26",
          f"got {xapian.version_string()}")
except Exception as e:
    check("xapian import", False, str(e))
    # import 失败时 xapian 未绑定到命名空间，后续功能测试必然 NameError
    # 级联误报，立即退出避免淹没真实根因（AI 检视意见）
    print(f"\n{len(failures)} test(s) FAILED: {', '.join(failures)}")
    sys.exit(1)

print("[test] functional: in-memory database + document")
try:
    db = xapian.WritableDatabase("", xapian.DB_BACKEND_INMEMORY)
    doc = xapian.Document()
    doc.set_data("smoke test document")
    db.add_document(doc)
    db.flush()
    check("in-memory db create + add", True)
except Exception as e:
    check("in-memory db create + add", False, str(e))

print("[test] functional: search a document")
try:
    db2 = xapian.WritableDatabase("", xapian.DB_BACKEND_INMEMORY)
    doc2 = xapian.Document()
    doc2.set_data("hello world")
    doc2.add_posting("hello", 1)
    doc2.add_posting("world", 2)
    db2.add_document(doc2)
    enquire = xapian.Enquire(db2)
    qp = xapian.QueryParser()
    query = qp.parse_query("hello")
    enquire.set_query(query)
    mset = enquire.get_mset(0, 10)
    check("search returns 1 result", mset.size() == 1, f"got {mset.size()}")
except Exception as e:
    check("search returns 1 result", False, str(e))

if failures:
    print(f"\n{len(failures)} test(s) FAILED: {', '.join(failures)}")
    sys.exit(1)
print("\nAll tests passed.")

# -*- coding: utf-8 -*-
"""v12.22 知识库 metrics 闭环测试：
- sidecar v2（entries + pending）兼容 v1
- _touch_metrics / _record_outcome / settle_pending_outcomes
- driver 不再直写共享 .kv（PR 污染修复防回退）
- kb_report 兼容 v1/v2
"""
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {extra}")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="v1220_"))
    for k in ("OHC_PROJECT_DIR", "OHC_RESULT_OUT"):
        os.environ.pop(k, None)

    # 准备一个 gdir（knowledge/graph 形态：parent 目录下放 .metrics-local.json）
    gdir = tmp / "graph"
    gdir.mkdir(parents=True)

    from ohc import engine

    # ── T1: _touch_metrics 写 sidecar v2 ──
    engine._touch_metrics("E001", str(gdir))
    sc_path = tmp / ".metrics-local.json"
    check("T1 sidecar 存在", sc_path.exists())
    sc = json.loads(sc_path.read_text(encoding="utf-8"))
    check("T1 entries 结构", isinstance(sc.get("entries"), dict))
    check("T1 E001 有 last", "last" in sc["entries"].get("E001", {}))
    check("T1 E001 进 pending", sc.get("pending") == ["E001"])
    check("T1 无 tmp 残留", not (tmp / ".metrics-local.json.tmp").exists())

    # ── T2: 多条目 pending 顺序 ──
    engine._touch_metrics("E002", str(gdir))
    engine._touch_metrics("E001", str(gdir))  # 重复命中不重复入 pending
    sc = json.loads(sc_path.read_text(encoding="utf-8"))
    check("T2 pending 去重", sc["pending"] == ["E001", "E002"])

    # ── T3: v1 兼容读 ──
    v1 = tmp / ".metrics-local-v1.json"
    v1.write_text(json.dumps({"E009": "2026-08-01", "E010": "2026-08-02"}),
                  encoding="utf-8")
    got = engine._sidecar_load(str(v1))
    check("T3 v1 迁移 entries", set(got["entries"]) == {"E009", "E010"}
          and got["entries"]["E009"]["last"] == "2026-08-01")
    check("T3 v1 pending 为空", got["pending"] == [])

    # ── T4: _record_outcome 即时记账 + 移出 pending ──
    engine._record_outcome("E001", str(gdir), success=True)
    engine._record_outcome("E001", str(gdir), success=True)
    engine._record_outcome("E001", str(gdir), success=False)
    sc = json.loads(sc_path.read_text(encoding="utf-8"))
    e1 = sc["entries"]["E001"]
    check("T4 s=2 f=1", e1.get("s") == 2 and e1.get("f") == 1)
    check("T4 E001 移出 pending", "E001" not in sc["pending"]
          and sc["pending"] == ["E002"])

    # ── T5: settle(True) 批量结算 + 清空 pending ──
    engine.settle_pending_outcomes(str(gdir), success=True)
    sc = json.loads(sc_path.read_text(encoding="utf-8"))
    check("T5 E002 记 success", sc["entries"]["E002"].get("s") == 1)
    check("T5 pending 清空", sc["pending"] == [])

    # ── T6: settle 幂等（空 pending 早退不改文件）──
    mtime_before = sc_path.stat().st_mtime_ns
    engine.settle_pending_outcomes(str(gdir), success=True)
    check("T6 幂等早退",
          sc_path.stat().st_mtime_ns == mtime_before)

    # ── T7: settle(False) 失败记账 ──
    engine._touch_metrics("E050", str(gdir))
    engine.settle_pending_outcomes(str(gdir), success=False)
    sc = json.loads(sc_path.read_text(encoding="utf-8"))
    check("T7 E050 记 fail", sc["entries"]["E050"].get("f") == 1
          and sc["entries"]["E050"].get("s", 0) == 0)

    # ── T8: driver 不再直写共享 .kv（PR 污染修复防回退）──
    drv = (REPO / "scripts" / "ohc" / "driver.py").read_text(
        encoding="utf-8")
    check("T8 driver 无 kb_metrics 引用", "kb_metrics" not in drv)
    check("T8 driver 有即时记账",
          "_record_outcome" in drv)
    check("T8 driver 三出口结算",
          drv.count("settle_pending_outcomes") >= 3)

    # ── T9: kb_report 兼容 v1 / v2 ──
    from ohc import kb_report
    kvdir = tmp / "kb"
    kvdir.mkdir()
    (kvdir / "E001.kv").write_text(
        "id: E001\ntitle: x\nmetrics_confidence: high\n", encoding="utf-8")
    # v2
    rows = kb_report._parse_kv_metrics(
        kvdir, {"entries": {"E001": {"last": "2026-09-03", "s": 2, "f": 1}},
                "pending": []})
    check("T9 v2 last/s/f", rows[0]["last_used"] == "2026-09-03"
          and rows[0]["hits_success"] == 2 and rows[0]["hits_fail"] == 1)
    # v1（经 _load_sidecar_metrics 归一后传入——真实调用契约）
    rows = kb_report._parse_kv_metrics(
        kvdir, {"entries": {"E001": {"last": "2026-08-09"}}, "pending": []})
    check("T9 v1 last 兼容", rows[0]["last_used"] == "2026-08-09"
          and rows[0]["hits_success"] == 0)
    # 遗留 .kv 字段兜底
    rows = kb_report._parse_kv_metrics(kvdir, {})
    check("T9 kv 字段兜底", rows[0]["last_used"] == ""
          and rows[0]["confidence"] == "high")

    # ── T10: _load_sidecar_metrics v1→v2 归一 ──
    proj = tmp / "p"
    (proj / "knowledge").mkdir(parents=True)
    (proj / "knowledge" / ".metrics-local.json").write_text(
        json.dumps({"E009": "2026-08-01"}), encoding="utf-8")
    loaded = kb_report._load_sidecar_metrics(proj)
    check("T10 v1 归一为 v2", set(loaded.get("entries", {})) == {"E009"})

    print(f"\nv12.22: PASS={PASS} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

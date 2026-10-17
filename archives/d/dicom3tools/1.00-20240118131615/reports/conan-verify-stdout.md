# conan-verify stdout 留档

> 逐字留档：下方标记之间的内容与原始日志**逐字节相同**（未加工）。
> review-memory §19 禁止 PR 入库 `*.log`，故运行日志以本形态留档（原文件不入库）。

| 属性 | 值 |
| --- | --- |
| 原始文件 | `conan-verify-stdout.log` |
| 字节数 | 2485 |
| 行数 | 51 |
| sha256 | `17e64d326057eb5e1566c1209b2fe6233a855068445822913f5984537bdc45dc` |
| 采集命令 | `python3 scripts/ohc-run.py conan-verify dicom3tools 1.00-20240118131615 --project-dir <repo>` |
| 采集时间 | 2026-09-11（设备本地时间） |
| 采信轮提交 | `48813722e1ccb489db358f51e973a6376ced5c03` |

<!-- BEGIN VERBATIM LOG -->
  ℹ️ 🔍 Conan 配方验证: dicom3tools 1.00-20240118131615
  ℹ️    引用: dicom3tools/1.00-20240118131615@ohpcd/stable
  ✅   Conan: Conan version 2.29.1 (path: /storage/Users/currentUser/usr/local/bin/conan)
  ✅   Profile file: ci/conan/profiles/ohos-aarch64
  ℹ️ G1: 配方完整性检查...
  ✅   G1: PASS
  ℹ️ G0: 预构建风险评估 (知识图谱预查询)...
  ℹ️ G2: conan create (干净构建)...
  ℹ️   Running: /storage/Users/currentUser/usr/local/bin/conan create /storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/archives/d/dicom3tools/1.00-20240118131615 -pr:h=/storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/ci/conan/profiles/ohos-aarch64 -pr:b=/storage/Users/currentUser/ws/wt-dicom3tools-1.00-20240118131615/ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
  ✅   G2: PASS
  ℹ️ G3: 系统同名库隔离验证 (R26)...
  ✅   G3: PASS
  ℹ️ G4: 产物完整性检查...
  ℹ️ L2: 平台功能矩阵 (smoke test)...
  ℹ️ L4: 静态安全扫描 (checksec)...
  ℹ️ L5: 产物基线对比...
  ℹ️   报告: archives/d/dicom3tools/1.00-20240118131615/reports/conan-verify-report.md
  ✅ 
✅ 配方验证通过: dicom3tools 1.00-20240118131615
  ✅    可标记 status: published
  ℹ️ R46 兜底: --out/OHC_RESULT_OUT 均未设置，写入 ECS 消费端默认路径 /storage/Users/currentUser/ohpcd-ai-worker-result.json
  ✅ result.json 已生成: /storage/Users/currentUser/ohpcd-ai-worker-result.json
  ✅ R46 草稿已落盘: milestone=conan_verify_passed -> /storage/Users/currentUser/ohpcd-ai-worker-result.json
{
  "schema": "1.0",
  "pkg": "dicom3tools",
  "ver": "1.00-20240118131615",
  "status": "partial",
  "agent": "CD3B",
  "ts": "2026-09-11T17:16:59.129727+00:00",
  "summary": "[draft:conan_verify_passed] dicom3tools 1.00-20240118131615",
  "commit_hash": "48813722e1ccb489db358f51e973a6376ced5c03",
  "branch": "feat/dicom3tools-1.00-20240118131615",
  "error_type": "partial",
  "error_detail": "R46 生命周期草稿: conan_verify_passed（任务进行中，非终态）",
  "detected_language": null,
  "language_evidence": null,
  "checkpoints": [
    {
      "ts": "2026-09-11T17:16:59.129652+00:00",
      "message": "status=partial"
    },
    {
      "ts": "2026-09-11T17:16:59.129758+00:00",
      "message": "result.json"
    }
  ],
  "draft": true,
  "milestone": "conan_verify_passed",
  "feedback_pending": true
}
<!-- END VERBATIM LOG -->

# DRAFT-001：./config.status: subs1.awk: Permission denied

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `platform` | Updated: 2026-08-17
> 对应: `knowledge/drafts/DRAFT-001.kv`

---

**匹配关键词**：umask 077, mktemp, Permission denied, HMDFS

## 错误签名（error_signature）

```text
umask 077 && mktemp -d.*Permission denied.*HMDFS
```

## 错误摘录（error_excerpt）

```text
./config.status: subs1.awk: Permission denied
```

## 根因（root_cause）

HMDFS file system does not support file creation inside directories created by mktemp -d (0700 permissions).

## 推荐方案（rec_approach: `Remove umask 077 from configure and add chmod 0777 after mktemp -d.`）

---

*本文件由 `knowledge/drafts/DRAFT-001.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*

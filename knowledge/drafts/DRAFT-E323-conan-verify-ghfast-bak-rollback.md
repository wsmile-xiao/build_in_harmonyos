# DRAFT-E323-conan-verify-ghfast-bak-rollback：DRAFT-E323-conan-verify-ghfast-bak-rollback

> Status: **Draft**（待审核 promote）| severity: `3` | category: `framework|conan-verify` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-E323-conan-verify-ghfast-bak-rollback.kv`

---

## 触发面

- trigger_tool: `ohc-run.py`
- phase: `verify`

**匹配关键词**：ghfast-bak,conandata,恢复,回滚,镜像

## 错误签名（error_signature）

```text
已恢复上次崩溃残留的 conandata\.yml|patches: \{\}|GPR_ASSERT.*undeclared.*复发
```

## 根因（root_cause）

conan_verify.py G2 的镜像注入逻辑在 finally 中恢复了 conandata.yml 内容但不删除 .ghfast-bak 备份文件；下次 conan-verify 启动时的"崩溃恢复"逻辑检测到残留 bak 即用它覆盖 当前 conandata.yml，导致两次验证之间对 conandata 的任何修改（如补丁登记）被静默回滚， G2 表现为"补丁未应用"的复发错误

## 影响范围（affected_scope）

所有需要在 conan-verify 迭代间修改 conandata.yml 的适配任务；含 W3 前置的 finish 内嵌 conan-verify 同样受影响

## 推荐方案（rec_approach: `每次修改 conandata.yml 后运行 conan-verify 前，先删除残留的 conandata.yml.ghfast-bak；G2 失败且报错与上次相同（补丁似乎未应用）时，第一时间 diff conandata.yml 是否被回滚`）

每次修改 conandata.yml 后运行 conan-verify 前，先删除残留的 conandata.yml.ghfast-bak；G2 失败且报错与上次相同（补丁似乎未应用）时，第一时间 diff conandata.yml 是否被回滚

## 补充关键词

ghfast-bak, conandata, 回滚, 恢复, 崩溃残留, 镜像注入, patch not applied, G2

---

*本文件由 `knowledge/drafts/DRAFT-E323-conan-verify-ghfast-bak-rollback.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*

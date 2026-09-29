# DRAFT-E727-lang-preflight-binding-dir-hijack

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-E727-lang-preflight-binding-dir-hijack.kv`

**标题**：语言预检假终态：语言绑定目录（src/extensions/*/Makefile.PL）劫持 manifest 判定 + 任务卡语言未注入（默认 cpp）

**阶段: `preflight` · 触发: `lang-preflight` · 类别: `lang-detect, false-terminal, workflow, r47` · 严重级: `2`**

## 错误签名（error_signature）

```text
"语言不匹配: task=\\w+, detected=\\w+ → env_unsupported|Makefile.PL 存在；命中 manifest 路径: .*extensions.*（未排除）|detected_language.*perl.*env_unsupported"
```

## 根因（root_cause）

>
  lang_detect 的绑定目录排除表 _AUX_MANIFEST_DIRS 只含 bindings/binding/lang/docs/doc/
  examples/example/samples/test/tests，不含多语言绑定工程惯用的 extensions/（以及 bindings
  的其他拼写）。当统计层无 ≥70% 主体语言时按 manifest 判定：genders 的
  src/extensions/perl/Libgenders/Makefile.PL 命中 perl → detected=perl；同时 pipeline 阶段1
  调 lang-preflight 不带 --lang 且不注入 OHPCD_LANG → expected 落到工具默认 cpp。
  两者叠加 → 「语言不匹配」→ exit 2 并写终态 env_unsupported 进共享 result 槽
  （$HOME/ohpcd-ai-worker-result.json），按协议平台将按 detected_language 迁移/取消任务——
  实为假终态：主体是 autotools C 库（configure.ac/Makefile.am + c 占比在排除绑定目录后 89%）。
  与 overlay 已修的 py_ext/（tlsh）、third-party（lnav）、根级 setup.py（libyal）同族：
  「绑定/辅助目录不代表主体语言」，本形态是目录名 extensions 未入排除表。

## 方案（rec_approach）

exclude-binding-dirs-and-inject-task-lang

## 关键词

lang-preflight, R47, env_unsupported, Makefile.PL, extensions, 语言绑定目录, OHPCD_LANG, detected=perl, 语言不匹配, 共享 result 槽, _AUX_MANIFEST_DIRS, src/extensions

## 来源

本条目取自 `knowledge/drafts/DRAFT-E727-lang-preflight-binding-dir-hijack.kv`；promote 后对应 `knowledge/doc/E###.md`。

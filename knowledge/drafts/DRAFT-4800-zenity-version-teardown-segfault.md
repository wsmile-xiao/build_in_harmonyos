# DRAFT-4800-zenity-version-teardown-segfault：GTK4/libadwaita CLI tools whose handle-local-options prints --version and returns 0 segfault headless (Signal 11) during AdwApplication/GTK teardown; fix by _exit(0) right after the early-exit print

> Status: **Draft**（待审核 promote）| severity: `2` | category: `platform, runtime, gtk` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-4800-zenity-version-teardown-segfault.kv`

---

## 触发面

- trigger_tool: `zenity|glib|gtk4|libadwaita|meson|runtime`
- phase: `runtime`

**匹配关键词**：zenity, --version, segfault, Signal 11, teardown, g_application_run, adw_application, AdwApplication, headless, Broadway, no display, _exit(0), handle-local-options, GOption, GTK4, libadwaita

## 错误签名（error_signature）

```text
zenity --version prints version then Signal 11|Segmentation fault after printing version|g_application_run teardown crash headless
```

## 根因（root_cause）

zenity 4.x runs as an AdwApplication: main() constructs the app, then g_application_run() dispatches handle-local-options (which prints the version and returns 0), and CONTINUES into GApplication/AdwApplication shutdown (adw styles teardown, GTK deinit). On OHOS PC there is no window system (gtk4 is Broadway-only and no broadwayd is running headless), so the GTK/Adwaita teardown path dereferences display-less state and the process dies with Signal 11 AFTER the version string was already printed. The exit status becomes 139, which breaks smoke tests and packaging validation even though the tool itself works.

## 影响范围（affected_scope）

Any GTK4/libadwaita-based command-line tool that handles --version/--help in a GApplication local-options callback and returns normally on OHOS/headless targets (verified: zenity 4.2.2; same pattern expected for other libadwaita-1 consumers).

## 推荐方案（rec_approach: `exit-immediately-after-early-exit-print`）

In the local-options callback, replace `return 0` after the version print with `fflush(stdout); _exit(0);` (add #include <unistd.h>). _exit bypasses atexit/GTK teardown entirely, so the process exits 0 with the output flushed before any display-less teardown can crash. Option parsing helpers that run BEFORE g_application_run (GOption --help) are already safe headless and need no change.

## 修复命令（rec_command）

```text
apply patches/0002-zenity-exit-0-after-version-print.patch in archives/z/zenity/4.2.2/ and re-run the test_package smoke test
```

## 兜底方案（fallback_approach: `document-and-tolerate-exit-139`）

If patching is not acceptable, treat exit 139 with correct stdout as pass in the smoke test (compare printed version only), and document the teardown crash as a platform limitation; this is inferior because CI L-gates and downstream users see a crashing binary.

## 验证方式（verification_cmd）

```text
conan create archives/z/zenity/4.2.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 && conanrun zenity --version; echo exit=$?
```

---

*本文件由 `knowledge/drafts/DRAFT-4800-zenity-version-teardown-segfault.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*

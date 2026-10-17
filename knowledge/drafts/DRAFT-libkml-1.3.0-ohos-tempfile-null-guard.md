# DRAFT-libkml-1.3.0-ohos-tempfile-null-guard — OHOS 源码硬编码 /tmp 临时文件失败 + NULL 解引用修复边界

## 问题

鸿蒙 OHOS 系统 `/tmp` 为只读挂载（E002）。libkml 1.3.0 `src/kml/base/file_posix.cc`
`File::CreateNewTempFile()` 硬编码 `mkstemp("/tmp/libkmlXXXXXX")`，不读取 `$TMPDIR`，
导致临时文件创建失败；测试辅助 `KmlToKmz()` 对 `CreateTempFile()` 返回 NULL 未防护，
直接 `tempfile->name()` 空指针解引用 → 上游 `test_kml_file` SIGSEGV（exit 139）。

## 根因

- 环境层：OHOS /tmp 只读（E002 已覆盖，仅环境变量 `set-env-var` 方案）。
- 源码层：库源码硬编码 /tmp 且不读 `$TMPDIR`（E002 未覆盖）。
- 防护层：临时文件创建失败路径缺少 NULL 检查（E040 为 mandb 场景，不覆盖本组合）。

## 方案（可复用边界）

1. **源码级**：`CreateNewTempFile()` 优先读取 `$TMPDIR` 回退 `/tmp`，不硬编码设备特定路径。
2. **防护级**：临时文件创建失败（NULL）必须检查，不得直接解引用。
3. **测试**：新增经库 API 的 OHOS 特定临时文件 consumer 测试（建/写/读/存在/删）。

## 验证

- `patch --dry-run -p1` 两补丁干净应用。
- 上游测试重跑：130 运行 130 通过 0 失败 0 超时（此前 5 失败含 1 SIGSEGV）。
- `test_ohos_tempfile` 经 libkml API 本机运行 exit 0。
- conan create / conan-verify / W3 均 RC=0。

## 适用边界

适用源码硬编码 /tmp 且未读 `$TMPDIR` 的 C/C++ 库（CMake/make 系）与失败路径未防护的
上游测试；不适用于已通过环境变量 `TMPDIR` 即可修复的纯脚本场景（归 E002）。

## 查重差异

- E002：环境变量层（/tmp 只读 → set TMPDIR），未覆盖源码硬编码需打补丁。
- E040：mandb `get_man_owner` NULL → SIGSEGV，不同根因。
- E052/E060/E110：configure/config.status + HMDFS 临时目录，未覆盖源码级 `CreateNewTempFile`。

## 拟提升编号

待知识库主编确认最终 E 编号（不编造）。

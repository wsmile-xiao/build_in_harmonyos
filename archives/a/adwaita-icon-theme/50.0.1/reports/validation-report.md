# adwaita-icon-theme 50.0.1 验证报告

## 归档信息

- 软件：`adwaita-icon-theme`
- Conan 包版本：`50.0.1`
- 上游源版本：`50.0`
- 任务分支：`feat/adwaita-icon-theme-50.0.1`
- 关联 PR：<https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/9128>

## 验证结果

- HarmonyOS aarch64 真机：`currentUser@10.62.220.52:2222`
- Conan `create`：通过
- `test_package`：20/20 consumer checks passed
- 上游官方测试：0 项；上游为 Meson data-only 资源包，使用 `meson dist --no-tests`
- AtomGit CI：PR #9128 的 `conan-build-test`、L0、L1 均通过
- AI 代码审查：通过，未发现问题

## 关键覆盖

消费者测试覆盖 `index.theme`、Adwaita 图标目录、`folder-open.svg`、PNG、XCursor 源文件与 public alias、data-only `pkg-config` 文件及许可证。

在 OHOS/HMDFS 或 Windows destdir 无法创建 symlink 时，配方会将缺失的公开 alias 回填为与规范源文件字节一致的普通文件；测试同时接受有效 symlink 和一致的 regular-file fallback。

## 证据

- 真机日志目录：`/storage/Users/currentUser/ohos-test-runs/codex-adwaita-icon-theme-50.0.1-r1-20260905-171328`
- 设备日志：`/storage/Users/currentUser/ohos-test-runs/codex-adwaita-icon-theme-50.0.1-r1-20260905-171328/device-conan-create.log`

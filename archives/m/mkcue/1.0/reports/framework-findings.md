# mkcue 1.0 — 框架发现（SKILL / 工具链问题，供反馈）

本文件记录本次适配中发现的、属于 **SKILL 框架/工具**（而非上游或配方）的问题，
均已用真实命令与输出佐证。

## F1. `patch-autotools-ohos.pl` 对老版 config.guess 生成的分支缺少 `echo/exit`

- 现象：脚本报告 `[ok] Added HarmonyOS system identification`，但打补丁后
  `./build/config.guess` 仍报 `unable to guess system type`（exit 1）。
- 根因：脚本插入的分支写成
  `GUESS=${MACHINE}-unknown-linux-ohos`，依赖新版 config.guess 末尾统一
  `echo "$GUESS"`；mkcue 的 config.guess 是 **2002-10-21** 版，各 case 分支直接
  `echo …; exit 0`，末尾没有 GUESS 汇总，故分支命中后继续走到末尾报错。
- 佐证：`sh -x ./build/config.guess` 追踪可见 `+ MACHINE=aarch64` / `+ GUESS=aarch64-unknown-linux-ohos`
  之后仍进入结尾的 "unable to guess system type" heredoc。
- 建议：脚本按 config.guess 版本自适应——若文件不含 `echo "$GUESS"`，分支内直接
  `echo ${MACHINE}-…; exit 0`。
- 本次处理：手工把分支改为 `echo ${MACHINE}-unknown-linux-ohos; exit 0`（补丁 0001）。

## F2. `patch-autotools-ohos.pl` 的 config.sub 三处模式无法匹配老版 config.sub

- 现象：`config.sub: ohos-linux=0 ohos*=0 linux-ohos=0`，`Done. cg=1 sub=0 change(s)`，
  `Score: 1/5 → ❌ Some patches may have failed`；`config.sub aarch64-linux-ohos` 仍报
  `machine 'aarch64-unknown-linux' not recognized`。
- 根因：脚本依赖现代 config.sub 的三个锚点（`android-linux)` 三元组块、
  `gnu* | android*` OS 列表、`linux-uclibc*` 内核列表），**2002-09-05 版 config.sub
  三者都不存在**，且不认 `aarch64`/`arm64`。
- 本次处理：手工在 `maybe_os` 列表加 `linux-ohos*`、CPU 列表加 `aarch64 \| arm64`、
  在 `-linux*)` 前插入 `-linux-ohos*)`（避免被改写成 `linux-gnu`），生成补丁 0002。

## F3. 编辑追踪器把 `build/` 目录整体排除，导致 autotools 辅助脚本的改动不被 `refresh-patch` 采集

- 现象：`refresh-patch --auto mkcue 1` 只识别到 `configure`，漏掉
  `build/config.guess`、`build/config.sub`（它们才是 OHOS 适配的关键改动）。
- 根因：`scripts/ohc/edit_tracker.py` 的 `_SKIP_DIRS` 含 `"build"`，而本库的
  `build/` 恰恰是上游源码目录（`AC_CONFIG_AUX_DIR(build)` 存放 config.guess/sub/install-sh）。
  于是 init-build 的基线（39 个文件）不含这两个文件，哈希比对自然扫不到。
- 本次绕过：`ohc-run.py track-edit add mkcue 1.0 build/config.guess` 手工登记
  （因不在基线中，落入 `added` 列表；auto_mode 仍因 `orig_file.exists()` 生成正确 diff）。
- 建议：`_SKIP_DIRS` 的 `build` 应仅在识别为构建产物目录时排除（例如存在
  `CMakeCache.txt` / `*.o`），或提供 `--include-dir build` 覆盖。

## F4. `refresh-patch --all` 未实现（参数被接收但忽略）

- 现象：`refresh-patch --all mkcue 1.0` 直接打印 help 并返回 1；
  `refresh-patch --auto --all mkcue 1.0` 也只走"精准模式"（args.all_mode 在
  `refresh_patch.py:refresh_patch_cli` 中未使用）。
- 影响：当追踪器漏采文件（见 F3）时，没有"全量扫描"兜底通道。
- 建议：实现 `--all`（走 `_find_differences` 规则模式），或在 help 中移除该选项。

## F5. Conan 版本号正则要求 ≥2 字符，上游单字符版本（`1`）无法直接使用

- 现象：`conan create … --version 1` → `ERROR: Invalid package version '1'`（exit 1）。
- 根因：Conan `api/model/refs.py::validate_ref` 的正则为
  `^[a-z0-9_][a-z0-9_+.-]{1,100}$` → 首字符后**至少 1 个**字符，单字符版本非法。
  （制品仓同样拒绝：`conan download mkcue/1 -r=ohpcd` → `ERROR: error:invalid version`。）
- 本次处理：版本归一化为 `1.0`，目录 `archives/m/mkcue/1.0`，分支 `feat/mkcue-1.0`
  （CI L0n 要求分支名精确等于 `<pkg>-<version>`）。
- 建议：在版本号策略（SKILL §1.2 / ARCHIVE-SPEC）中明确"上游单字符版本 → `<N>.0`"
  的归一化规则，并在任务下发时使用归一化后的版本号，避免 L0n 与 conan 校验互相打架。

## F6. `conan-verify` 的 L2/L4/L5 因"无 cache 路径"整体跳过

- 现象：G2/G3/G4 PASS，但 `L2/L4/L5: ⏭️ 跳过（无 cache 路径）`，即冒烟测试、
  安全扫描、产物基线三项**未实际执行**却计为 PASS。
- 影响：验证报告给出 PASS 时，读者无法区分"通过"与"未运行"。
- 本次处理：手工补测 NX/PIE/RELRO/.codesign/解释器/sha256 并写入 `reports/test-report.md`。
- 建议：找不到 cache 路径时应标为 `SKIPPED`（区别于 PASS）并提示手工补测命令。

## F7. `make` 的 jobserver FIFO 告警（环境相关）

- 现象：`make: jobserver mkfifo: /storage/Users/currentUser/tmp/GMfifo59549: Operation not permitted`
  （conan 以 `-j20` 调用，make 无法建立 jobserver FIFO）。
- 影响：本次 make 仍成功（自动降级串行），但并行度失效。
- 备注：与 `/tmp` 只读（E002）同源，建议 CI/本地统一把 `TMPDIR` 指向可写目录。

## F8. `clean_verify` 把 manifest 的 `configure_options: []` 解析成字面串 `[]` 并拼进命令行

- 现象（首次 finish）：`G0: configure 失败 (exit 1)`，
  `g0-configure.log` 内容为
  `configure: WARNING: invalid host type: []` /
  `checking build system type... Invalid configuration '[]': machine '[]' not recognized` /
  `configure: error: /bin/sh build/config.sub [] failed`。
- 根因：`scripts/ohc/clean_verify.py` 用正则
  `configure_options:\s*["\']?(.*?)["\']?\n` 抓取该字段，YAML 空列表 `[]` 被抓成字面串 `"[]"`，
  随后拼成 `./configure --prefix=… []`。知识库 **E141** 已记录该问题。
- 本次处理：按 E141 建议把 `manifest.yaml` 的 `configure_options: []` 改为 `configure_options: ""`，
  G0 随即 `configure 成功 / make 成功 / 安装产物正常 (1 bin, 0 lib)`。

## F9. `gen_summary`（Step 8）抛 `'str' object has no attribute 'append'`

- 现象：`finish` Step 8/10 → `⚠️ gen_summary 失败: 'str' object has no attribute 'append'`
  （非致命，finish 继续）。
- 影响：`SUMMARY.md` 未重新生成。
- 备注：与归档内容无关，属工具内部类型错误；本次未深挖（非阻塞）。

## F10. `finalize-archive` 的 notes↔manifest 一致性检查把 notes 表格内容误当状态值

- 现象：`⚠️ 状态不一致: notes=can't create ./confstatoCFpmc/subs.sed: Permission denied` → … `vs manifest=published`，
  随后又报 `⚠️ notes.md 无对话记录`。
- 根因：检查器从 `notes.md` 中提取 "状态" 相关文本时命中了"问题与解决方案"表格里的报错片段
  （该行含反引号与 `→`），而非 `## 编译环境` 中的 `- 状态: published`。
- 影响：产生 2 条"一致性问题"噪音，但 `缺失项: 0`，不阻塞。
- 建议：一致性检查限定在 notes 的固定小节（如"## 编译环境"）内匹配 `状态:`。

## F11. 仓库 index 存在 `libXext/` 与 `libxext/` 大小写冲突 → 工作树恒定显示 2 个文件 modified

- 现象：全新 worktree（`git worktree add … origin/main`）建立后，
  `git status` 立即显示 ` M archives/l/libXext/README.md`、` M archives/l/libXext/manifest.yaml`
  （`archives/l/` 磁盘上只有一个目录 `libXext`）。
- 根因：git index 中**同时存在** `archives/l/libXext/` 与 `archives/l/libxext/` 两套路径，
  而 HMDFS 不区分大小写，二者只能落地一份 → 另一个变体被 git 视为被修改。
  主工作树同样如此（非本任务引入）。
- 本次处理：对该文件**未做任何提交级操作**；最终 PR 只 `git add archives/m/mkcue`。
  排查期间曾执行过一次 `git checkout -- archives/l/libXext/`（仅影响本 worktree 文件内容），
  已用 `git show HEAD:archives/l/libxext/<f>` 逐字写回，恢复为与本 worktree 建立时
  （亦即主工作树当前）完全一致的内容。
- 建议：清理仓库中大小写冲突的历史目录，或对该路径加 `core.ignorecase` 相关治理。

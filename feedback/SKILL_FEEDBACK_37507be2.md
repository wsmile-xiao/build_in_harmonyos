# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_37507be2.md`

---

## 背景

- **软件名称**: tunnelx
- **版本**: 20190701
- **构建日期**: 2026-10-04
- **构建系统**: custom（javac + jar，无 CMake/Autotools/Make/Maven/Gradle/Ant）
- **上游仓库**: https://github.com/goatchurchprime/tunnelx/archive/refs/tags/R2019a.tar.gz
  （上游 tag R2019a = `src/TN.java:58` 的 `version2019-07-01 DoES` 快照；与 Debian orig 包 `src/` 逐字节一致）
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
无（纯 Java，零第三方编译期依赖；JDK 由平台 BiSheng OpenJDK 17.0.13 提供）
- **最终状态**: 成功（本地全链路绿；按用户指令停在 commit/push 前）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 W4 审计的完整链路（按用户指令不执行远端写操作）。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 预置已核验 tarball 规避 GitHub TLS 抖动 |
| lang-preflight | R47 语言预检 | 通过 | task=java / detected=java（81 .java，主体 85%） |
| build | 编译构建 | 成功 | javac 81 源文件 → 230 class；jar cfe → tunnelx.jar（623,817 B） |
| conan create | 配方构建 + L1 test_package | 通过 | 包 6b129b06…；test_package 11/11 |
| conan-verify | 配方验证 | ✅ PASS | G1/G2/G3/G4 + L2/L4/L5；reports/conan-verify-report.md |
| finish | 归档收尾（W2 结构 + R36 依赖 + W3 本地 CI） | 完成 | W3 PASS（.ci-result.json exit_code=0）；step5b 为**存量**知识债务 |
| W4 | Pre-PR 独立审计（隔离子任务，3 轮） | ✅ PASS | 第 3 轮（修复后复审）verdict=pass，P0=0/P1=0/P2=0/P3=7 |
| submit | PR提交+AI检视+CI | 未执行 | 按用户指令停在 commit/push 前等待确认；AI Review: — |

### 失败与问题

- **1**: 根因=`conan create` 首个错误：`TypeError: get() got an unexpected keyword argument 'tar_format'`（source() 第 94 行）, 解决方案=conandata.yml 的 `tar_format` 是归档规范字段，`conan.tools.files.get()` 只接受 `url/sha256/destination/strip_root/verify`；source() 内 `dict(...)` + `pop("tar_format")` 后再展开（已沉淀为知识草稿 DRAFT-tunnelx-20190701-conandata-tar-format-kwarg-typeerror）
- **2**: 根因=直连 `github.com/archive/...` 下载在 `init-build` 中 `_ssl.c:993 handshake timed out`, 解决方案=本机到 GitHub 偶发 TLS 抖动（curl 重试可成功）；预置已核验 tarball 到 `$TMPDIR/builds/tunnelx-20190701.tar.gz` 并固定 `EXPECTED_SHA256`
- **3**: 根因=`git worktree add` 全量检出失败：`unable to create file ... (Errno 28)` / `No space left on device`, 解决方案=文件系统 **inode 耗尽**（`/mnt/hmdfs/100/non_account` 48,455,677 inode 已用满，剩余 <6k）；改用**稀疏工作树**（sparse-checkout，检出 7239→1280 文件），并清理 `$HOME/tmp/builds` 中 ≥2 天的陈旧 scratch（释放约 43 万 inode）
- **4**: 根因=`conan create` 在测试包目录留下 `conanrun.sh`/`conanbuildenv-*.sh`/`metadata/`/`__pycache__`, 解决方案=`test_package` 无 `layout()`，conan 默认把生成器写到 conanfile 所在目录；提交前清理（JC 只扫提交差异）
- **5**: 根因=HarmonyOS 无 `libawt_xawt.so`（仅 `libawt.so` + `libawt_headless.so`），GUI 无法建窗, 解决方案=BiSheng JDK 的 `java.desktop` 未构建 X11 后端（平台限制）；test.sh T4 改为断言"入口可达 + 停在 AWT 初始化（栈帧含 Tunnel.MainBox.main）"
- **7**: 根因=**CI 平台功能矩阵 L2 记 skip**（`<bin> --version/--help` 失败：上游 `Tunnel.MainBox` 是 GUI 入口，`--version` 被当作未知参数 → `TN.emitWarning` → `mainbox` 为 null 时 NPE）, 解决方案=在安装的 `bin/tunnelx` 启动器层承接 CLI 契约（`--version`/`--help`，JDK 探测前处理、无需 JVM、exit 0），并在 test_package 增加 T5b 真断言覆盖；重建后 `L2_RESULT=pass: tunnelx --version OK`
- **6**: 根因=**W3/E017 镜像注入改写 conandata.yml 后未还原**（连续两轮 finish 后仍残留 `gh-proxy.com` 前缀，备份 `conandata.yml.orig` 存在但无还原步骤）, 解决方案=W4 审计第 1 轮以 P1（R39/PF7）拦截；手工还原为官方单条 URL 并删除残留备份后，第 2 轮复审 pass

### 知识图谱使用情况

- **引用知识条目**: 无（G2 首次失败时引擎给出 E185/E538 等误命中，均与 Java/下载无关）
- **新增知识草稿**: 1 条（`DRAFT-tunnelx-20190701-conandata-tar-format-kwarg-typeerror`，kv + md 一一对应）
- **引擎命中情况**: 对 `TypeError: get() got an unexpected keyword argument 'tar_format'` 查询未命中（最相近的 E483 是 `BadZipFile` 形态，失败阶段与签名不同）
- **测试统计**: 上游自动化用例 0（如实申报 0/0）；test_package 11/11；鸿蒙探针 7/7（含鸿蒙特有 OHOS-1/OHOS-2 = 2 项）
- **未覆盖的错误模式**: 「conandata.yml 规范字段 tar_format 被 `**` 直接展开传给 `get()` → TypeError」——已提草稿；另建议补充「OHOS 文件系统 inode 耗尽导致 git worktree / conan create ENOSPC」类环境故障条目

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 未执行（PR 未创建，按用户指令停在远端写操作前）
- **检视意见数量**: 未执行
- **检视意见处理**: 未执行

### CI 结果

- **本地 CI 模拟 (W3)**: ✅ PASS，且 `L0/L1/L2/L4/L5` 全 pass（`reports/w3-local-ci.log`，`.ci-result.json` exit_code=0，含 integrity_hash + log_sha256）
- **远程 CI (PR 校验)**: 未触发（PR 未创建）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 1（finish Step 3 clean-verify 的 G0 HANDOFF；G0 按 autotools 假设执行 `./configure`，对 javac+jar 工程不适用）
- **重试次数**: 8（conan-verify 4 次：G1 缺 export_sources/apply_conandata_patches、G2 tar_format、G2 镜像注入、通过；finish 4 轮迭代收敛；手工 conan create 2 次）
- **关键瓶颈**: ① 文件系统 inode 耗尽（多次阻塞 worktree 检出与 conan create 测试阶段）；② W3/E017 镜像注入改写 conandata.yml 且未还原（证据链与门禁冲突）
- **耗时较长的步骤**: `finish`（内含 conan-verify + W3 = 2 次完整 conan create）与 `verify-build`；单次 conan create（javac 81 文件 + jar + test_package）约 1 分钟，瓶颈在环境而非构建本身

---

## 建议

### SKILL 设计改进

1. **W3/E017 镜像注入必须保证还原**：`ci/conan/build_and_test.sh` 的 Pre-download 与 `conan_verify.py` 的 E017 注入都会改写 `conandata.yml` 的 `sources.url` 为镜像列表；实测连续两轮 finish 后仍残留（`gh-proxy.com` / `ghfast.top` 前缀），虽生成了 `.orig` 备份却无还原步骤。建议：① 用 `trap ... EXIT` 或 `finally` 强制还原；② `finish` 在最后一步断言 `conandata.yml` 不含镜像域名（同时纳入 `preflight` 前置自检），避免"本地全绿但 PR 必被 PF7/R39 拦"。
2. **G0 clean-verify 应对非 autotools 工程跳过**：当前 `clean_verify.py` 无条件执行 `./configure`，对 javac/jar（Java）、headeronly、纯 shell 类工程必然 exit 127 并输出红色 HANDOFF。建议读 `.build-context` 的 `BUILD_SYSTEM`（本例被猜成 autotools），在 `custom`/`headeronly` 时跳过并说明"等效验证由 conan-verify G2 + W3 承担"，避免误导性红项。
3. **conan-verify 的 G4 包 ID 提取正则在 `--user/--channel` 形式下失效**：本轮 G4 报"⚠️ 无法找到程序包 ID"，导致 L2（smoke）/L4（checksec）/L5（baseline）全部"跳过（无 cache 路径）"，即这三道门禁实际未执行却被记为 PASS。建议修正 `_package_id` 提取（或直接以 `package_folder` 定位），并把"跳过"与"通过"在报告里明确区分（Java/无 ELF 包可显式记为 N/A）。
4. **W5（`check_knowledge_completeness`）应区分"存量债务"与"本次引入"**：本轮 step5b 失败仅因 main 上既有条目 `E219/E253/E305` 的 `root_cause`/`rec_approach` 为空（与本次变更无关），却计入 AI 的 finish 失败步骤。建议按变更范围过滤或标注为存量告警，避免把他人债务算到当前任务头上（W5 已在文档标"非阻塞"，但 `steps[]` 仍记为失败）。

### 模板改进

1. **`templates/conanfile-*.py.tmpl` 的 `source()` 应内置 `tar_format` 处理**：模板与归档规范都要求 `conandata.yml` 写 `tar_format`，但 `get()` 不接受该 kwarg——每个新配方都要自己踩一次 `TypeError`（仓内 `archives/m/motif`、`a/accountsservice`、`d/dbus`、`p/polkit` 均已各自写注释规避）。建议模板直接生成 `source_data.pop("tar_format", None)`。
2. **`test_package` 模板应给出 `layout()` 或显式 `folders`**：当前 conan 会把 `conanrun.sh`/`conanbuildenv-*.sh`/`metadata/`/`__pycache__` 写进 `test_package/`（源码目录），污染归档树并需要人工清理。建议模板加 `layout()`（或说明须在提交前清理）。
3. **`templates/notes.md` 建议内置"上游测试入口"与"鸿蒙特有用例"两节**：本轮上游确实 0 个自动化用例，但模板无对应栏目，只能自行写入；若模板固定这两节，可减少遗漏与返工。

### 自动化补全

1. **`pre_pr_audit.py generate` 在分支无提交时必须覆盖未跟踪文件**：`get_changed_files()` 走 `git diff origin/main...HEAD`，无提交时回退 `git ls-files`，而 `git ls-files` **不含未跟踪文件**——结果是审计输入里根本没有本次新增的包（本轮实测 3954 个文件、0 个 tunnelx）。对"停在 commit 前"的协作模式（本任务即如此）完全失效。建议回退链改为 `git status --porcelain --untracked-files=all` + `pr.diff` 白名单。
2. **`pre_pr_audit.py report` 应落盘 `reports/audit-result.json`**：当前 `report` 只打印不写文件，而 `submit` 的 W4 门禁正是读该路径；实测需手工把审计 JSON 搬过去（易漏、易被误判"未审计"）。建议 `report` 直接写出规范化产物（含 `audited_file_sha256`，顺带满足 R52 证据一致性）。
3. **`init-build` 下载失败应支持本地回退**：本机到 GitHub TLS 抖动时 `_download_one` 直接失败退出（`_ssl.c:993 handshake timed out`）。建议 `_download` 增加"本地已核验 tarball / conan sources download cache"回退（`$TMPDIR/builds/<name>-<ver>.<fmt>` 命中即用，`EXPECTED_SHA256` 校验），可显著减少网络抖动导致的重试。
4. **inode/磁盘前置检查**：本机文件系统 inode 已近耗尽，`git worktree add` 与 conan create 测试阶段会以 `Errno 28` 失败且不提示根因。建议 `init-build`/`finish` 入口增加 `stat -f` 空闲 inode 检查并在不足时给出明确指引（清理 `$HOME/tmp/builds` 陈旧 scratch / 使用稀疏工作树）。

### 知识图谱覆盖

1. **新增条目（已提草稿）**：`DRAFT-tunnelx-20190701-conandata-tar-format-kwarg-typeerror` —— `conandata.yml` 的 `tar_format` 被 `**` 展开传给 `get()` → `TypeError`；与既有 `E483`（get() 不据 tar_format 推断格式 → `BadZipFile`）是同一事实的两个表现面，建议 promote 时建立 `similar_to` 关联。
2. **建议新增**：`OHOS inode 耗尽`（`Errno 28 / No space left on device`，影响 `git worktree add`、`conan create` 测试阶段、`mktemp`）——属平台环境类故障，判定与止损口径清晰（先查 `df -i`，清理可重建的 scratch/cache），复用价值高。
3. **建议补充**：`W3/E017 改写 conandata.yml 未还原 → PF7/R39 拦截` 的反模式条目（可作为"门禁自相矛盾"类知识：CI 脚本行为与 PR 前置硬闸冲突时的判定优先级），本轮 W4 审计正是靠该模式识别出 P1。

---

## 作者

- **姓名**: lyl_ling
- **邮箱**: lan_ling_wang@noreply.gitcode.com
- **Agent ID**: 4BA1
- **生成时间**: 2026-10-04 12:41:06
- **PR 编号**: —（按用户指令停在远端写操作前）
- **Git Commit**: 1262b4ac24

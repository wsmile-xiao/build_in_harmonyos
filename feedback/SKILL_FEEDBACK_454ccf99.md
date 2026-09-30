# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_454ccf99.md`

---

## 背景

- **软件名称**: lokalize
- **版本**: 26.04.0
- **构建日期**: 2026-09-28
- **构建系统**: cmake
- **上游仓库**: https://download.kde.org/stable/release-service/26.04.0/src/lokalize-26.04.0.tar.xz
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
- qtbase/6.11.1
- qtbase-gui/6.11.1
- qtbase-sql-dbus/6.11.1
- ki18n/6.14.0
- kconfig/6.14.0
- kcoreaddons/6.14.0
- kconfigwidgets/6.14.0
- kitemviews/6.14.0
- kwidgetsaddons/6.14.0
- kio/6.14.0
- kxmlgui/6.14.0
- ktextwidgets/6.14.0
- knotifications/6.14.0
- kcrash/6.14.0
- kiconthemes/6.14.0
- kcolorscheme/6.14.0
- kdbusaddons/6.14.0
- sonnet/6.26.0
- hunspell/1.7.3
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: cmake |
| conan-verify | 配方验证 | 通过 | G0-G4 + L2/L4/L5 全过（含系统库隔离、产物基线） |
| finish | 归档收尾 | 完成 | W2 结构 + R36 依赖 + W3 本地 conan create 均过，状态 built |
| submit | PR提交+AI检视+CI | 完成 | PR #13577；CI #63901「CI 校验通过」；AI Review 仅到「检视进行中」 |

### 失败与问题

- **1**: 根因=编译报 `hunspell.hxx` 找不到, 解决方案=注册表 hunspell/1.7.3 的头装在 `include/hunspell/`，而上游按 pkg-config 风格变量名读取（`.pc` 里是 `includedir/hunspell`），CMake 侧变量名大小写与惯例不符
- **2**: 根因=应用启动即退出（rc=1，无输出）, 解决方案=OHOS 无 D-Bus：既无守护进程也无会话总线；lokalize 启动时经 QtDBus 连接会话总线失败后退出
- **3**: 根因=`gettextheadertest::testFormatDate` 失败：QTimeZone("Europe/Moscow") 偏移恒为 `+0000`, 解决方案=测试用 QTimeZone 格式化日期，需 TZDIR 指向 tz 数据库；OHOS 镜像既无 `/usr/share/zoneinfo` 也无 `/system/usr/share/zoneinfo`；且配方原先用 `os.path.isdir(candidate/"UTC")` 探测候选目录，而 tz 数据库把 `UTC`/`Europe/Moscow` 存为**普通文件**，isdir 探测把所有合法数据库都拒掉了 → TZDIR 从未生效
- **4**: 根因=`projectmodeltest` SIGSEGV（rc=139）, 解决方案=该用例用 `QTEST_GUILESS_MAIN`（仅 QCoreApplication），却在遍历工程目录时经 KIconThemes 触发 KColorSchemeManager 的延迟调色板激活（`QGuiApplication::setPalette`），此时无 QGuiApplication，libKF6ColorScheme 解引用未初始化调色板后崩溃。已用 LD_PRELOAD 帧指针追踪器定位栈（本机 ptrace 全禁，gdb 不可用）：`KColorSchemeManagerPrivate::activateSchemeInternal` → `QGuiApplication::setPalette`（libKF6ColorScheme 内帧）
- **5**: 根因=直接运行测试二进制报 `Error loading shared library ../../bin/libKF6SonnetCore.so`, 解决方案=本地构建产物带构建树相对 `DT_NEEDED`（`../../bin/...`），且 KF6 包把共享库装在 `bin/` 而非 `lib/`
- **6**: 根因=KF6 模块版本约束, 解决方案=上游 `find_package(KF6Sonnet 6.14.0 REQUIRED)` 接受 `[6.14.0,7.0)`，但制品仓没有 sonnet 6.14.0

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 1 条（`knowledge/drafts/DRAFT-13577-ohos-stale-absolute-dt-needed-cache-path.kv` + 同名 `.md`）
- **引擎命中情况**: 未命中既有正式条目——依赖包 `DT_NEEDED` 记录构建机绝对路径导致干净机器装载失败，知识库此前无覆盖
- **测试统计**: 上游 ctest 6/6（上游共 7 项，`projectmodeltest` 因依赖侧缺陷显式排除）+ test_package 消费者用例 3/3
- **未覆盖的错误模式**: ①已发布依赖包 `DT_NEEDED` 内嵌构建机 conan 缓存绝对路径 → 干净 worker 装载失败、上游测试全挂（本次已建草稿）；②`QTEST_GUILESS_MAIN` 用例经 KIconThemes 触发 `KColorSchemeManager` 调色板激活而 SIGSEGV（依赖侧缺陷，非本包可修）

### AI 检视结果

- **检视阶段到达**: Phase 1（变更摘要 + 「AI 代码检视正在进行中」）
- **变更摘要评估**: 摘要由 atomgit-bot 生成；未给出必须修改项
- **检视意见数量**: 0（截至 CI 转绿未收到行级检视意见）
- **检视意见处理**: 无需处理；若后续出现意见按 accept/reject 逐条闭环

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 通过 —— #63901（worker CI-018，SHA `9ffeaddc`）「CI 校验通过」，L0/L1 门禁全过
- **CI 失败原因**: 首轮 #63825 失败：上游 ctest 0/6，`Error loading shared library <绝对路径>/libKF6ConfigCore.so`——根因是已发布 KF6 包 `DT_NEEDED` 记录构建机绝对缓存路径；配方补测试期路径修复后 #63901 转绿

### 效率分析

- **HANDOFF 次数**: 1（PR 创建通道 401：`gitcode_pr.py create-pr` 缺 `~/.gitcode-token`，改走 atomgit_api 建 PR）
- **重试次数**: CI 修复 1 轮（#63825 红 → 修复 → #63901 绿）；`conan create` 因制品仓/源码源网络抖动多次退避重试
- **关键瓶颈**: ①网络：`conan.cnb.cool` 与源码源 DNS/连接不稳（仅 IPv6、连接拒绝），需本地下载缓存 + 退避重试才能推进；②环境差异：依赖包 `DT_NEEDED` 绝对路径使「本地绿、CI 红」，必须拿完整 CI 日志 + 依赖包 ELF 分析才能定位
- **耗时较长的步骤**: `conan create` 全量交叉编译（Qt6 + KF6 依赖链）+ 上游 ctest；每轮远程 CI 约 8-10 分钟
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 3 个事件（含 1 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-28T17:10:48 | lang_checked | detected=cpp 与任务 cpp 匹配 |
| 2026-09-28T20:20:20 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/lokalize-26.04.0 --target main --title 'feat(lokalize): 26.04.0 适配完成' |
| 2026-09-28T20:30:23 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

- **W3 缺一道「本地/CI 环境等价性」闸**：本地 conan 缓存目录恰好存在，会让依赖包 `DT_NEEDED`
  绝对路径问题*完全隐身*（本地 6/6 绿、CI 0/6 红）。建议 W3 增加 ELF 依赖表自检
  （对构建产物跑 `readelf -d <elf> | grep NEEDED | grep -c '/'`，非 0 即告警并提示修复），
  把这类失败在提交前暴露，而不是消耗一轮 CI（本轮 ~10 分钟 + 诊断轮次）。
- **submit 的 PR 创建通道需备用路径**：本机无 `~/.gitcode-token` 时 `gitcode_pr.py create-pr` 403/401，
  最终靠手工 `atomgit_api` 建 PR，导致 submit 内置的 AI Review/CI 监控全程脱轨（只能人工轮询评论）。
  建议：create-pr 失败时自动回落到 atomgit_api 通道，或显式提示「PR 已由外部通道创建，请用
  `submit --resume --no-wait` 接管监控」。
- **junk_check 的模式退化会误拦他人残留**：未提交工作区时 `junk_check.sh` 从 incremental 退化为
  full 整仓扫描，命中**他包已跟踪**的运行时状态文件（JC1/JC5 报错与被审包无关）。建议 full 模式
  限定在被审包路径内，或直接提示「请先提交本次变更再跑门禁」。

### 模板改进

- 建议为「依赖预编译 KF6/Qt6 的 GUI/KDE 类包」在 conanfile 模板中内置**测试环境 ELF 依赖自检与
  陈旧绝对路径修复**辅助（本次自研 `_repair_absolute_needed_paths()`，全链通用：扫描构建树 +
  依赖包 ELF 的绝对 `DT_NEEDED`，按 basename 在依赖包内重建软链并迭代到不动点）。
- PR body 模板的「上游测试」统计字段会自动填 0 占位，而 R51 要求实测数字；建议从
  `<ver>/reports/test-report.md` 与 ctest 日志自动提取「定义数/运行数/通过数/排除项及原因」。

### 自动化补全

- **R44 diagnose 增加 ELF 维度**：环境差异类 CI 失败（`Error loading shared library <绝对路径>`）
  可在 diagnose 阶段直接解析日志中的绝对路径，在依赖包内验证 basename 可达性，自动给出
  「可修（重建软链）/不可修（依赖包缺库）」结论，省掉人工读 6 万字符日志。
- **制品仓侧 SONAME 自检**：对已发布包检查 `readelf -d | grep SONAME`，缺失即告警
  （SONAME 缺失正是 `DT_NEEDED` 落全路径的根因），从源头减少下游适配踩坑。
- 依赖检查脚本（PF4 `probe_registry`）可顺带输出依赖包 ELF 的 `DT_NEEDED` 健康度，供配方预扫描消费。

### 知识图谱覆盖

- 建议新增正式条目：**依赖包 `DT_NEEDED` 内嵌构建机绝对路径 → 干净机器装载失败**。
  已提交草稿 `knowledge/drafts/DRAFT-13577-ohos-stale-absolute-dt-needed-cache-path.kv`（+ `.md`），
  含症状、根因（无 SONAME 时链接器写全路径）、判定命令、已试失败方案（`LD_LIBRARY_PATH`/`rpath`
  对含 `/` 的条目无效、改上游源码只能修本包产物）与消费者侧修复方案、适用边界。
- 建议评估新增条目：**`QTEST_GUILESS_MAIN` 用例经 KIconThemes 触发 `KColorSchemeManager`
  调色板激活而崩溃**（Qt/KF6 在无 `QGuiApplication` 的测试 main 下的依赖侧缺陷模式）。

---

## 作者

- **姓名**: weijiapan
- **邮箱**: weijiapan@noreply.gitcode.com
- **Agent ID**: B762
- **生成时间**: 2026-09-28 20:30:23
- **PR 编号**: #13577
- **Git Commit**: `9ffeaddc0c`（CI 修复提交；最终以 PR head 为准）

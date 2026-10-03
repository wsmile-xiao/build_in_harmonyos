# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_b305cba8.md`

---

## 背景

- **软件名称**: kamailio-memcached
- **版本**: 6.0.6
- **构建日期**: 2026-10-02
- **构建系统**: makefile
- **上游仓库**: https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
- libmemcached/1.0.18
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: makefile |
| conan-verify | 配方验证 | 通过 | G0-G4 + L2/L4/L5 全 PASS（rc=0）；最后一轮复跑 G2 遇并发/磁盘抖动（conan 内部 os.utime FileNotFoundError），随后 W3 conan create 通过 |
| finish | 归档收尾 | 完成（有警告） | W2 结构 ✅ / R36 依赖 ✅ / W3 本地 CI ✅（.ci-result.json exit_code=0）；警告：packaging tarball 未生成、gen_summary 框架 bug、G0 clean-verify 按 autotools 假设执行 configure（exit 127） |
| submit | PR提交+AI检视+CI | 未执行（按用户要求停在提交前） | AI Review: — |

### 失败与问题

- **1**: 根因=`conan create` 产物 `memcached.so` 中 `__gxx_personality_v0` / `_ZSt9terminatev` / `__cxa_begin_catch` 未解析（`llvm-nm -u` 可见）；运行时 `dlopen` 报 `symbol not found`, 解决方案=`libmemcached/1.0.18` 是**静态 C++ 实现**归档，其 `package_info` 声明 `system_libs=["m","c++"]`，但**包内自带 `.pc` 未声明** `-lm -lc++`；kamailio 模块 Makefile 正是用 `pkg-config --libs libmemcached` 取链接参数 → 共享库链接仍 rc=0，隐患静默
- **2**: 根因=`make[1]: --libs: No such file or directory`（模块 Makefile 解析期噪声）, 解决方案=`src/modules/memcached/Makefile` 用 `BUILDER = $(shell which pkg-config)` 探测 pkg-config；在 make 默认 `/bin/sh`（toybox）下该探测不稳定
- **3**: 根因=裸进程 `dlopen(memcached.so, RTLD_LAZY)` 失败：`Error relocating ...: pv_get_null: symbol not found`, 解决方案=OHOS（musl）无延迟绑定 —— `dlopen` 返回前即完成全部重定位；模块依赖 Kamailio core ABI（宿主提供）
- **4**: 根因=`conan create` test_package 报 `CMakeToolchain is declared in the generators attribute, but was instantiated in the generate() method too`, 解决方案=test_package 既在 `generators` 声明 `CMakeToolchain`，又在 `generate()` 实例化（需注入 `MODULE_SO` cache 变量）

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 6 条
- **引擎命中情况**: 草稿目录 2769 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: 本次 3 类新模式在适配前均无对应条目（已补草稿 E429/E430/E431）：
  (1) 依赖包自带 `.pc` 漏声明 `package_info` 的 `system_libs` → 静态 C++ 依赖链入共享对象时 C++ 运行时未解析，
      且**共享库链接 rc=0 静默**（W3/conan create 都不会报错，只有 dlopen 才暴露）；
  (2) OHOS(musl) **无延迟绑定** → 宿主插件只能由提供宿主 ABI 的进程装载，独立进程 dlopen 必失败，
      现有测试范式（dlopen 自检）对"插件型包"缺少宿主桩约定；
  (3) `make` 默认 `/bin/sh`（toybox）下 `$(shell which pkg-config)` 探测不稳定
      （`make[1]: --libs: No such file or directory`）→ 模块型 Makefile 的链接参数来源在
      pkg-config 与 LOCALBASE 裸路径间摇摆。

### AI 检视结果

- **检视阶段到达**: —（未进入 submit，故 AI Review 未触发）
- **变更摘要评估**: 不适用（未创建 PR）
- **检视意见数量**: 0（未创建 PR）
- **检视意见处理**: 不适用；本地已按仓库审计规则自查（code-style / review-memory 对应项：无平台宏补丁、
  测试非空壳、无 build 残留入 PR、单软件原子性）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 4
  （① conan-verify G1：缺 `export_sources`/`apply_conandata_patches` 文本检查；
   ② W3 失败：JC full 模式命中**仓库既有** 5 个他人包的 `.build-closed`/`.staging-verified`；
   ③ W3 失败：并发导致瞬时 ENOSPC（"No space left on device"）——重试即通过；
   ④ finish 完成后知识遗漏 unreferenced=3）
- **重试次数**: 3（W3/conan create 3 次；其中 1 次为磁盘抖动、1 次为 JC 模式问题、1 次为真失败修复）
- **关键瓶颈**: ① 共享机器资源竞争（磁盘瞬时写满 ENOSPC、内存仅剩 ~0.5G/32G）导致 conan create 偶发失败；
  ② `finish` 的 W3 junk_check 在**无本地 commit** 时退化为 full 模式，扫全仓既有脏文件必然失败，
  迫使以 `JUNK_PR_DIFF`（CI pr.diff 语境）复现 CI 判定；③ 2380+ 条存量知识草稿导致 W5 每次全量枚举。
- **耗时较长的步骤**: conan create（每轮约 1–2 min，含 13MB tarball 下载 + 7000 文件源码拷贝）；
  finish（内含一次 conan-verify + 一次 W3，约 3–4 min）。总计约 35 min（含探索与 4 次修复循环）。
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-02T12:42:23 | lang_checked | detected=cpp 与任务 cpp 匹配 |
| 2026-10-02T13:10:59 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **W3 junk_check 在无本地 commit 时必然误判**：`junk_check.sh` 默认 `incremental`
   （`git diff origin/main...HEAD`），但贡献者若按"停在 commit 前等待确认"的协作边界工作，
   工作树尚未 commit → diff 为空 → 退化为 `full` 模式扫全仓 → 命中**其他包**的
   `archives/*/.staging-verified`、`.build-closed` 等 5 个既有脏文件（本仓 origin/main 实测存在），
   本地 W3 直接红，与本次改动无关。建议：`full` 模式下限制扫描范围到本次涉及的
   `archives/<首字母>/<软件>/` 子树，或在无 commit 时改为 `git status --porcelain` + 未跟踪目录扫描。
   （本次以 `JUNK_PR_DIFF` 复现 CI 的 pr.diff 语境绕过，并已单列证据。）
2. **仓库既有脏文件应清理**：`archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、
   `archives/k/kics/2.1.20/.staging-verified`、`archives/l/libbfio/20260623/.staging-verified`、
   `archives/t/thc/3.8/.staging-verified` 均已被 origin/main 跟踪，任何 `full` 模式扫描都会失败。
   建议 CI 侧一次性清理并加入 JC1 防回归。
3. **`finish` 的 G0 clean-verify 硬编码 autotools 假设**：对 makefile 型源码执行 `./configure` → exit 127
   （kamailio 无 configure）。应以 manifest 的 `build_system` 选择验证命令（makefile → `make cfg`）。
4. **`conan-verify`/`finish` 的 G2 对并发/资源抖动无退避**：共享机器（内存 <1G 可用）下
   conan 内部 `os.utime(package_layout.base_folder)` 因目录被其他任务移走而 `FileNotFoundError`，
   直接判 FAIL。建议对"conan 内部 Traceback（非配方错误）"做一次退避重试。
5. **插件型包（dlopen 模块）缺少一等公民支持**：manifest/测试规范默认"库/可执行"两类；
   Kamailio/Asterisk 类宿主插件既不是 link 库也不是可执行文件（`package_info.libs = []`）。
   建议在 ADAPTATION_GUIDE 增加"宿主插件包"章节，明确 staging 验证（无 `bin/*` 时 `verified=0`）
   与 test_package 的宿主桩约定。

### 模板改进

1. `templates/` 缺 **make/自定义构建系统** 的 conanfile 模板（本次 `init-build` 报
   "conanfile.py 模板不可用（autotools）"、"conandata.yml 模板不可用"，全部手写）。
   建议补 `conanfile-make.py.tmpl`（含 `SHELL=<bash>`、`PKG_CONFIG_PATH` 指向 generators 的范式）。
2. version-level `manifest.yaml` 模板缺 `build.build_commands` 字段（makefile 型包需要记录
   `make cfg` + `make modules modules=...` 两条命令），建议补入。
3. `templates/notes.md` 的"验证结果"节缺少"上游无测试套件"专用表述位，容易产生
   "0/0/0/0" 与"未执行"的歧义。

### 自动化补全

1. **依赖 `.pc` 的 system_libs 一致性检查可自动化**：对 `requires` 中每个声明了
   `system_libs` 的包，若其包内 `.pc` 的 `Libs:` 未覆盖这些库，则在 conan-verify 阶段提示
   "用包内 .pc 可能漏链"。规则：`package_info.system_libs ⊄ pc.Libs` → warn。
   （本次该缺陷导致共享库链接 rc=0 但 dlopen 失败，属最难发现的静默类。）
2. **产物未定义符号闭环检查**：G4/L5 可增加"排除宿主 ABI 名单后，产物未定义符号必须 ⊆ {libc, libc++}
   等系统运行时"，可自动发现"漏链 C++ 运行时/漏链依赖"两类问题。
3. **ENOSPC 退避**：build/finish 阶段捕获 `No space left on device` 时自动短暂退避重试（本次 1 次重试即过）。
4. **JC full 模式自动降级**：无 commit/无 pr.diff 时，自动以"git status 未跟踪+修改文件"为检查集，
   避免把整仓历史脏文件算到本次任务头上。

### 知识图谱覆盖

1. 本次新增 3 条草稿（建议 promote）：`E429-draft-B596`（依赖 .pc 漏声明 system_libs 导致的
   C++ 运行时未解析，静默类）、`E430-draft-74DD`（OHOS/musl 无延迟绑定 → 宿主插件装载模型）、
   `E431-draft-7643`（make 默认 /bin/sh 下 pkg-config 探测不稳定）。
2. 存量条目字段缺失（W5 反复告警，仍无人处理）：`E219.kv`/`E253.kv` 的 `root_cause` 为空、
   `E305.kv` 的 `root_cause` 与 `rec_approach` 均为空 —— 建议主编补齐或归档。
3. 存量草稿 2769 条（本轮全量枚举），建议增加"草稿年龄 >N 天自动归档/合并"的治理任务，
   否则每次 W5 都要枚举数千条并产生噪声。

---

## 作者

- **姓名**: lyl_ling
- **邮箱**: lan_ling_wang@noreply.gitcode.com
- **Agent ID**: B3E4
- **生成时间**: 2026-10-02 13:10:59
- **PR 编号**: —
- **Git Commit**: 172d7d38e0

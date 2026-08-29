# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_d6c213de.md`

---

## 背景

- **软件名称**: websocketpp
- **版本**: 0.8.2
- **构建日期**: 2026-08-28
- **构建系统**: cmake
- **上游仓库**: https://github.com/zaphoyd/websocketpp/archive/refs/tags/0.8.2.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 3
- **编译依赖**:
- boost/1.90.0
- openssl/3.5.6
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: cmake |
| conan-verify | 配方验证 | 最终 PASS（8 门禁全绿） | 前两轮 G2 FAIL：①patches 段被残留 .ghfast-bak 静默回退→编的是未打补丁源码；②配方漏 requires openssl→消费者 `openssl/conf.h` not found。16:23 清缓存重跑，日志含 Apply patch ×3 + 38 断言通过 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 部分成功：门禁/自检/push 全过，PR 创建被框架缺陷挡住后手工补 | Gate0-4 与 6 项自检全 PASS；`git commit` 被误判失败（容错只匹配 nothing to commit）；PR 创建连撞两处：PF0 环境闸 str/Path bug 与 fork head 需 `Awstme:branch`。改用 create-pr --no-preflight 建 #7052，CI #33898 ✅ PASSED |

### 失败与问题

本次流程未遇到阻塞性问题

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 10 条
- **引擎命中情况**: 草稿目录 222 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: 3 类
  1. Asio 1.31（boost≥1.88）整体移除经典执行器 API：`io_service`/`io_service::work`/
     `expires_from_now()` getter/`io_context::post|reset` 成员/旧 resolver `query|iterator`/
     `socket_base::max_connections`。全库 grep `io_service|expires_from_now|executor_work_guard|
     max_listen_connections|resolver::query` **0 命中** → 已建草稿
     `DRAFT-asio-classic-executor-boost-1-88.kv`（含 error_signature/forbid_*/prescan_pattern）。
  2. 老库的上游测试用 Boost.Test 旧模块入口 `init_unit_test_suite(int,char**)`，boost 1.90 的
     `unit_test_main` 只要 `init_unit_test()` → 静态与 header-only 两种链法都失败（与 SCons/Py2 无关的独立阻塞）。
  3. header-only 库 `requires boost` 不够：`config/asio*.hpp` 经 `boost/asio/ssl.hpp` 需要 openssl 头，
     而本仓库 boost 配方不传递 openssl → `openssl/conf.h` not found。

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 未评估——按用户指示本轮只追 CI 绿，PR 用 `--no-wait`/直接 create-pr 建立后立刻 trigger-ci，未进入 submit 的 AI Review 5 阶段。
- **检视意见数量**: 未采集（atomgit-bot 检视意见未拉取；CI 机器人与 PR body 正常，mergeable=True）。
- **检视意见处理**: 待后续 follow-up：`submit websocketpp 0.8.2 --resume`（或直接 `gitcode_pr.py get-review-comments` + `handle-review-opinion`）闭环检视意见；PR 正文与 notes 已把技术决策写全，回复成本低。

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 6（G2 FAIL ×2 的报告块、finish step5b/step8 收尾块、submit `git_commit_failed`、submit `pr_creation_failed`、feedback 骨架填充）。其中 3 次是框架缺陷造成的非生产性交接。
- **重试次数**: conan-verify 4 轮（1 轮纯白跑：因 .ghfast-bak 回退，编的是未打补丁源码）；补丁设计迭代 3 轮（别名→探针全量枚举→兼容层收敛）。
- **关键瓶颈**: 不是编译，而是**"证据可信度"**——三个隐蔽状态坑：
  ①G2 用残留 `.bak` 覆盖 conandata（假失败）；②`refresh-patch` 不写 conandata patches 段（补丁存在但 0 应用）；
  ③缓存命中使 `conan-create.log` 丢掉 Apply patch 行（证据自洽性被破坏）。三者都会让"看起来通过/看起来失败"与真实构建脱钩。
- **耗时较长的步骤**: `conan create` 每轮 2–4 min。转折点是用秒级 `clang++ -fsyntax-only` + **实例化探针**（真调用被改成员）替代整轮 conan：5 类错误面在 ~3 分钟内全部枚举完，兼容层才是一次设计到位；建议把这类探针做成 header-only C++ 包的标配前置步骤。
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 3 个事件（含 2 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-08-28T16:42:40 | handoff:git_commit_failed | git commit 失败:  |
| 2026-08-28T16:46:48 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/websocketpp-0.8.2 --target main --title 'feat(websocketpp): 0.8.2 适配完成' |
| 2026-08-28T16:52:56 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **G2 的"崩溃恢复"语义要改**：`conan_verify.py` 用任意残留 `conandata.yml.ghfast-bak`
   无条件覆盖 `conandata.yml`，等于让"上次没跑完"污染"这次的内容真值"；且 finally 只回写不删自建 `.bak`，
   每轮都留一颗地雷。建议：镜像注入改成**只在内存/conan 侧 cache 生效不落盘**，
   或至少在恢复前比对 `.bak` 与当前文件的 mtime+hash，当前文件更新时以当前为准并告警。
2. **PF0 应区分"预检异常"与"预检不通过"**：现在 `str/Path` 这类自身 bug 会以 fail-closed 直接拦死建 PR，
   贡献者只能全局逃生（`--no-preflight`），既误伤又削弱闸门公信力。建议异常时打印 traceback 并给出
   "仅跳过该子检查"的最小逃生口。
3. **submit 建 PR 的 head 需按 fork 自动补 `<owner>:` 前缀**（协作者默认 fork 工作流，现在必然 404）。
4. **commit 容错补 `no changes added to commit`**（git 2.45 实际措辞），否则"AI 先自检提交过一次"的正常路径会被判失败。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **header-library 模板缺"消费者头依赖"提示**：`templates/conanfile-*.py.tmpl` 对 header-only 只示范
   `requires` 主依赖，没有提醒"上游若 include `boost/asio/ssl.hpp` 之类聚合头，还要显式 requires 其
   传递依赖（openssl）"——本仓库 boost 配方不传递 openssl，这个坑 100% 会踩。建议在模板注释里点名。
2. **`test_package/MANIFEST.yml` 建议加两个字段**：`upstream_unrunnable_evidence`（贴原始命令+输出行）
   和 `covered_by_consumer_test`（上游用例→消费者断言映射）。本次"上游 35 测试不可运行"的三条实证
   现在只能塞进 description 字符串，评审很难快速核验。
3. **积分赛 PR 模板缺"依赖项定位"字段**：本次是给 autobahn-cpp 补依赖，模板里没有"为什么是本任务的依赖、
   下游谁消费、接口约定（cmake_file_name/target）"这一栏，只能写在"三方库信息"里，建议显式加一条。
4. **版本级 manifest 模板建议强制 `patch_verification` 段**（dry-run/重放等价/ sha256 对齐三件套）：
   本次靠手工核对才发现 `refresh-patch` 不写 conandata，模板化能让下一个作者一眼看到该做什么。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **`refresh-patch --auto` 同步维护 `conandata.yml: patches`**（或检测到 patches/ 非空而 conandata 为空时 FAIL）：
   这是本次最贵的自动化缺口——补丁文件在、构建却应用 0 个，且报错完全看不出因果。
2. **`conan-verify` G2 前自动清理本包自建残留**（`*.ghfast-bak`/`conandata.yml.orig`），并在 G2 结束后校验
   "日志是否出现 Apply patch 行"与"conandata 是否声明了 patches"一致性，缺一条就明确报"本轮可能编了未打补丁源码"。
3. **缓存命中时给日志加标记**：G2 走 binary cache 时 `conan-create.log` 不含 patch/test 证据，
   建议 conan-verify 在 G2 PASS 后自动 `conan remove <ref> -c` 复跑一次"干净留证轮"，或明确在报告里标注
   "本日志为缓存复跑，补丁证据见 <另一文件>"。本次是手工补的。
4. **给 header-only/模板库加 `cxx-instantiate-probe` 子命令**：按配方头文件自动生成一个"真调用公开 API"的
   探针并 `clang++ -fsyntax-only` 跑，秒级枚举模板成员错误面，替代整轮 conan create。本次收益最大的一项。
5. **`finish` 的 G0 探针按构建系统分派**：上游无 `configure`（CMake-only/header-only）时不该以 127 报"失败"，
   建议识别为 N/A 并只走 `conan create` 证据链。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. 建议把本次草稿 **`DRAFT-asio-classic-executor-boost-1-88.kv`** 提升为正式 E 条目
   （签名已可直接匹配：`no type named 'io_service' in namespace`、
   `no member named 'work' in 'boost::asio::io_context'`、
   `no member named 'expires_from_now' in 'boost::asio::basic_waitable_timer`、
   `no member named 'max_connections' in 'boost::asio::socket_base`、
   `no member named 'query' in 'boost::asio::ip::basic_resolver`）。
   它同时带 `prescan_pattern`，入库后预扫能力自动增长（所有 2015–2020 年 asio 库选型阶段即可预警）。
2. 建议新增一条：**"上游 Boost.Test 旧入口 `init_unit_test_suite` 与 boost≥1.90 不兼容"**
   （trigger_tool=ld，phase=linking），这是"老库上游测试跑不动"的独立根因，
   与"SCons 不可用/boost 无 stage 树"是三条不同阻塞，混在一条里会误导后来人只查其一。
3. 建议新增一条工具行为坑：**"归档内残留 `conandata.yml.*.bak` 会被 conan-verify 用来覆盖 conandata.yml"**
   （trigger_tool=conan，phase=compilation，severity 3），命中特征就是"补丁明明在 patches/ 里，
   报错却是打补丁前的老错误"。这类"框架自我污染"的条目目前知识库里没有。
4. 反面教材登记：本次 G2 失败被引擎误命中为 **E225**（test_package `CMakeUserPresets.json`/`BUILD_DIR`），
   评分高但根因无关。建议 E225 的 `match_keywords` 增加排除性关键词
   （如 `io_service`/`Apply patch` 不参与匹配），或在 `similar_to` 里显式区分"编译期 asio API 缺失"这一族。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: Awstme
- **邮箱**: awstme@qq.com
- **Agent ID**: ED02
- **生成时间**: 2026-08-28 16:52:56
- **PR 编号**: —
- **Git Commit**: ca7c77a42

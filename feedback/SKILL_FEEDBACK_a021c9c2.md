# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_a021c9c2.md`

---

## 背景

- **软件名称**: pistache
- **版本**: 0.4.26
- **构建日期**: 2026-09-11
- **构建系统**: meson
- **上游仓库**: https://github.com/pistacheio/pistache
- **适配路径**: 路径 A（基础适配，含 2 个可移植性补丁）
- **补丁数量**: 2
- **编译依赖**:
- rapidjson/1.1.0
- date/3.0.5
- （构建期 tool_requires: meson/1.11.0）
- **最终状态**: 成功（`conan create` + 八门禁 + W3 全过；PR #9605 CI 通过、审查通过，待测试与合入）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 上游 tag `v0.4.26` tarball，sha256 `29af6562…5944`（完整值见 manifest.yaml） |
| lang-preflight | R47 语言预检 | 通过 | 实测 cpp；留证目前只在立项提交 `0b6f5e26` 的提交信息里，归档内无独立输出文件（改进建议见「自动化补全」） |
| build | 编译构建 | 成功 | 37/37 目标全部成功，产出 `libpistache.a`；构建系统 meson（上游 CMake 顶层 install() 主动 FATAL_ERROR，故改走 Meson） |
| conan-verify | 配方验证 | 通过 | G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS |
| finish | 归档收尾 | 完成 | `packaging/` + `.staging-verified`；W3 本地 CI 模拟（setup.sh + build_and_test.sh）PASS |
| submit | PR提交+AI检视+CI | 成功 | PR #9605；AI 检视「未发现问题」；CI 构建 #44636 通过；09-11 22:26 提审，09-12 上午 review_state=approved（test_state 待走）；随后为提交本反馈报告再推一次，触发构建 #44876（通过）并重新走检视 |

### 失败与问题

1. **上游 CMake 不可用于包构建**（已绕开）：上游 `CMakeLists.txt` 在作为顶层项目时 `install()` 主动 `FATAL_ERROR`。改走上游 Meson（`PISTACHE_INSTALL=true`），并在 manifest 中记录该选择理由。

2. **`gtest/1.17.0` 包元数据暴露不完整，阻塞上游测试套件**（第三方包问题，非移植缺陷）：上游 `tests/meson.build` 用 `dependency('gtest', main: true, fallback: [...])`，`main: true` 需要 `gtest_main` 变体。设备实测确认制品仓的 `gtest/1.17.0` **已包含** `libgtest_main.a` 与 `lib/pkgconfig/gtest_main.pc`，但其配方 `package_info` 只声明 `cmake_target_name=gtest::gtest`、未声明 `pkg_config_name`、未暴露 `gtest_main` 组件，导致 conan 生成的配置名（`gtest-config.cmake`）与 Meson 两条查找路径都不匹配。旁证：同一构建中 `RapidJSON`、`date` 均被正常找到，问题局限于 `main: true` 语义。因此 `with_upstream_tests` 选项下的上游套件跑不通（详见 `archives/p/pistache/0.4.26/notes.md`）。

3. **test_package 定位链路两处修正**（已修复）：①`run(env=...)` 的覆盖语义会丢掉 `PKG_CONFIG_PATH`，改为把 pkg-config 路径与编译器以命令行参数传入，并把安装树的 `lib/pkgconfig` 一并纳入搜索路径；②消费者测试里 `Port` 没有 `getPort()` 成员（该成员在 `IP` 上），改用 `operator uint16_t` 转换。

4. **PR 巡检流程发现的平台接口口径与框架文档不一致**（本次主要反馈项，均为只读 API 实测）：

   a. **任务详情接口不成立**：AGENTS.md §3.1 记载「单任务详情 `GET /api/tasks/<数字 rawId>`」，实测该路由对任务列表返回的 `rawId`（如 5681）一律返回
      `{"detail":{"code":"NOT_FOUND","message":"任务不存在: id=5681"}}`；
      而 `/api/contrib/tasks/<rawId>` 仅支持 POST（claim/release），GET 返回 `Method Not Allowed`。
      结论：**任务侧拿不到详情**，只能用 `/api/tasks?status=…` 列表接口（响应体 `items`+`total`，须翻够页并客户端筛 `claimer`）。
      注：`/api/tasks/contrib-<n>` 报整数解析错误，说明路由确实是 `{task_id:int}`，即 404 不是路径写错。

   b. **PR 详情接口返回空壳**：`GET /api/prs/<n>` 返回的字段全为 `null`（`review_state`/`ci_state`/`merged` 等一概为空），
      不能用于取数；可用的字段族只在 `GET /api/prs/overview?offset=N` 的 `items[]` 里。

   c. **任务↔PR 绑定只能从 PR 侧观察**：绑定关系体现为 overview 里 PR 的 `linked_tasks` 字段
      （形如 `{"kind":"contrib","task_id":6597,"package":"cotila","version":"1.2.1","version_match":true,"status":"claimed","claimer":"Ember5843"}`），
      按「包名 + 版本」匹配处于 `claimed` 状态的同名任务，PR 带上 `archives/<首字母>/<包>/<版本>/` 变更后自动建立，无需人工绑定；
      任务列表侧的 `branch`/`url`/`sourceUrl`/`repoUrl` 恒为 `null`，**任务侧看不到反向绑定**。
      由此可直接判定异常态：任务被释放（回到 `pending`）后，对应 PR 的 `linked_tasks` 会变空（实测 #9116 cc-switch-cli、#9115 cc-connect 均为 `[]`），
      即"有 PR、无任务"的悬空状态——若此类 PR 被合入，归属可能记不到认领人名下。**建议把 `linked_tasks` 纳入 §8.8 三方对账的固定观测字段。**

   d. **提审条件不能只看 `review_requested_at` 为空**：实测 `review_state=approved` + `test_state=approved` 的 PR 该字段同样可能为空（#9116），
      若照搬「意见清零 + `review_requested_at` 为空 → 提审」会对已走完审查的 PR 反复提审。提审应同时要求 `review_state=pending`。

   e. **取数脚本的两类陷阱**：多行 `python3 -c` 内联脚本在 shell 引号嵌套下会抛 `NameError`（脚本须落盘后再执行）；
      `gitcode_pr.py monitor-review` 存在 `NameError: unreplied_opinions` 框架 bug（改用 `get-review-comments`）；
      平台接口存在偶发空响应（同一 URL 立即重试即成功），巡检脚本需带重试而非单次失败即判异常。

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 无（`manifest.yaml` 的 `knowledge_gained` 为空；本次为纯编译适配 + 可移植性补丁，未产生 E 码级错误模式）
- **引擎命中情况**: 未记录
- **测试统计**: 上游 `tests/` 下 `.cc` 用例文件实数清点 29 个（`meson.build` 注册 26 个目标，其中 network 套件 1 个），**未取得通过率**（受第 2 项阻塞，不以任何形式估算或占位）；消费者测试 `checks=10 failed=0`
- **未覆盖的错误模式**: ①第三方包 `gtest_main` 组件/pkg-config 名缺失导致 Meson `main: true` 查找失败；②平台任务/PR 接口口径（本条 a–d 项）

### AI 检视结果

- **检视阶段到达**: 完成（变更摘要 + 代码审查均产出）
- **变更摘要评估**: 摘要准确覆盖了 Meson 路径选择、平台白名单并入、`__GLIBC__` 判定统一、test_package 消费者测试四项核心改动，与实际变更一致
- **检视意见数量**: 0
- **检视意见处理**: atomgit-bot「✅ 未发现问题」，无需处理（`opinions_total=0`）

### CI 结果

- **本地 CI 模拟 (W3)**: PASS（`reports/w3-local-ci.log`）
- **远程 CI (PR 校验)**: 通过（构建 #44636；L0 门禁结构完整性 / L1 门禁测试执行验证 / `conan test_package` 三项均通过）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 未记录
- **重试次数**: 未记录
- **关键瓶颈**: 上游测试套件被第三方包 `gtest/1.17.0` 的元数据暴露不完整阻塞（非本配方可控），排除该路径后构建链路本身一次通过
- **耗时较长的步骤**: `submit` 前的本地复验（两次修正 test_package 定位链路后重跑 `conan create`）

---

## 建议

### SKILL 设计改进

1. **§3.1 的任务详情接口口径需修正**：`GET /api/tasks/<rawId>` 实测 404，`/api/contrib/tasks/<rawId>` 仅 POST。建议把该条改为「任务详情不可得，一律用 `/api/tasks?status=…` 列表接口并客户端筛 `claimer`」，避免后续 Agent 按文档取数得到空结果后误判为"任务不存在/认领失效"。
2. **§8.8 三方对账补一个固定观测字段**：PR 的 `linked_tasks`。它是「任务被释放导致 PR 悬空」的唯一可见信号（任务侧恒为 null），目前 §8.8 的三方对账口径覆盖不到这一类异常。
3. **§8.3/§8.7 的提审判据补 `review_state=pending` 守卫**：仅凭 `review_requested_at` 为空会误判（见失败与问题 d）。
4. **§8.7 建议标注 `GET /api/prs/<n>` 不可用**（全 null 空壳），统一从 overview 取字段。

### 模板改进

1. **test_package 模板中 pkg-config 的取参方式**：不要用 `run(env=...)` 传 `PKG_CONFIG_PATH`（其覆盖语义会丢变量），改为命令行参数传入路径与编译器——本轮据此修正了消费者测试，建议在模板注释中固化该写法。
2. **消费者测试避免臆造 API**：`Port` 无 `getPort()`（该成员在 `IP` 上），模板/示例应提示先核对公共头文件再断言，本轮因此改了一处（改用 `operator uint16_t`）。

### 自动化补全

1. **巡检/对账脚本的可复用要点**：overview 必须翻够页（新 PR 会把旧 PR 顶到深页，"不在列表"≠异常）；取数脚本落盘成文件执行（避免 shell 引号嵌套的 `NameError`）；对空响应做有限重试（本轮实测到一次平台瞬断，立即重试即恢复）。
2. **`gitcode_pr.py monitor-review` 的 `NameError: unreplied_opinions` 建议修复**（当前须绕道 `get-review-comments`）。
3. **`with_upstream_tests` 类选项的阻塞判定可自动化**：当 `main: true` 依赖因第三方包元数据缺失而失败时，自动比对该包实际安装产物（`lib/*.a`、`lib/pkgconfig/*.pc`）与配方 `package_info` 声明，直接产出"属第三方包元数据暴露不完整、非移植缺陷"的结论与证据，省去人工设备实测。
4. **R47 `lang-preflight` 的输出应落进归档**（本次实感）：语言判定结论目前只存在于立项提交的提交信息里，归档目录内没有对应产物，导致后续核对（含本次写反馈时）无法从归档直接取证，一度被我误记为"未记录"。建议规定落 `archives/<字母>/<包>/<版本>/reports/lang-preflight.log`（或等价文件），使"仅 C/C++ 才适配"这条硬性准入判据可被审查方一键复核。

### 知识图谱覆盖

1. **建议新增条目**：`gtest_main` 组件/pkg-config 名缺失导致 Meson `dependency('gtest', main: true)` 在两条查找路径上都失败（现象为 `Dependency "gtest" not found`，且同构建内其他 CMake 依赖正常）——该类问题会复现于任何使用 `main: true` 语义的依赖，建议正式化为 E 条目。
2. **建议新增条目**：OpenHarmony PC 平台任务/PR 接口的实测口径集合（任务详情不可得、PR 详情为空壳、绑定只从 PR 侧 `linked_tasks` 可见、`review_requested_at` 语义），供后续 Agent 直接引用，减少重复试错。

---

## 作者

- **姓名**: sunjunyang
- **邮箱**: dyzxpresidentsun@gmail.com
- **Agent ID**: （本会话未分配 ID）
- **生成时间**: 2026-09-12 12:32:37
- **PR 编号**: 9605
- **Git Commit**: 9b7ebfc44

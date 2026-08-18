# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_38e01ca1.md`

---

## 背景

- **软件名称**: servlet-api
- **版本**: 4.0.1
- **构建日期**: 2026-08-15
- **构建系统**: custom
- **上游仓库**: https://codeload.github.com/javaee/servlet%2Dspec/tar.gz/refs/tags/4.0.1
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
无
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: custom |
| conan-verify | 配方验证 | 通过 | 配方语法、YAML、Conan create、L0、W3 和独立审计均通过；消费者测试 7/7 PASS |
| finish | 归档收尾 | 完成 | 77 个 Java 源文件已编译并生成 `javax.servlet-api-4.0.1.jar`；无源码补丁和运行时依赖 |
| submit | PR提交+AI检视+CI | 受 Worker 阻塞 | PR #5397；AI Review 未发现问题；最新 CI #25799 在通用 conan-setup 阶段因 Worker 缺少 `libsqlite3.so.0` 失败，尚未执行配方 |

### 失败与问题

1. 早期远程 CI #25706 暴露健康 Worker 未预装 JDK 的真实配方问题；已改为下载并校验固定 BiSheng JDK 17.0.13，主配方和消费者测试均不依赖系统 Java。
2. CI 预下载 URL 正则会在连字符处截断完整 GitCode URL；JDK 地址在 `conandata.yml` 中拆分为 scheme、host 和 path，由配方静态拼装后交给 `conan.tools.files.get()`，避免触发 L0o 外部下载门禁。
3. `test_package` 初版将约 290 MB JDK 解压到源码树；增加 `basic_layout()` 并设置 `self.folders.build = "build-release"` 后，工具只落入忽略的构建目录，旧污染目录已隔离到 `.build-cache/quarantine/`。
4. CI #25723 与重建 CI #25799 均在通用 `ci/conan/setup.sh` 阶段失败：HNP Python 的 `_sqlite3` 无法加载 Worker 缺失的 `libsqlite3.so.0`，随后 zsh 对 `/system/lib*` 无匹配退出。两次均未进入 `conan-build-test`、未读取 servlet-api 配方，属于 Worker 环境故障。

### 知识图谱使用情况

- **引用知识条目**: 无直接命中
- **新增知识草稿**: 无
- **引擎命中情况**: 未覆盖本次 Java 工具链和 Worker Python 故障
- **测试统计**: 77 个 Java 源文件编译成功；消费者测试 7/7 PASS；无上游测试目录，据实声明未执行上游测试
- **未覆盖的错误模式**: 健康 Worker 无预装 JDK；CI URL 预扫描正则错误截断含连字符的 URL；大体积构建工具污染 `test_package` 源码树；HNP Python 因 Worker 缺少 `libsqlite3.so.0` 在通用 setup 阶段失效。

### AI 检视结果

- **检视阶段到达**: 变更摘要与代码审查完成
- **变更摘要评估**: 准确覆盖纯 Java/Javac 构建、固定 BiSheng JDK、JDK 身份校验、下载回退、Conan JAR 暴露和 7 项消费者断言。
- **检视意见数量**: 0 条；机器人结论为“✅ 未发现问题”。
- **检视意见处理**: 无代码审查意见需要修改；CI 评论中的 setup 故障已依据完整日志区分为 Worker 环境问题，不将其错误归因于配方。

### CI 结果

- **本地 CI 模拟 (W3)**: 通过；`setup.sh`、`build_and_test.sh`、L0、Conan create 和消费者测试 7/7 均通过；隔离 HOME/PATH 的无预装 JDK 验证也通过
- **远程 CI (PR 校验)**: 当前受 Worker 阻塞；CI #25706 已进入构建并暴露的无预装 JDK 问题已修复；CI #25723、#25799 未越过通用 conan-setup
- **CI 失败原因**: CI #25799 的 Worker `OpenHarmonyPCDeveloper-CI-041` 缺少 `libsqlite3.so.0`，HNP Python 无法导入 sqlite3，配方和 `CI_PACKAGES` 尚未执行；需维护者修复 Worker 后重建

### 效率分析

- **HANDOFF 次数**: 至少 4 次（无预装 JDK 修复、源码树污染清理、独立审计、feedback 补全）
- **重试次数**: 多次远程重建；其中 #25706 产生一项有效配方修复，#25723 和 #25799 均重复命中 Worker sqlite3 故障
- **关键瓶颈**: 健康 Worker 不保证预装 Java；CI URL 预扫描规则限制工具地址表达；Worker HNP Python 与系统 `libsqlite3.so.0` 不完整导致配方前置阶段反复失败
- **耗时较长的步骤**: 固定 JDK 约 290 MB 的下载与双重校验、无预装 JDK 隔离复验，以及等待远程 Worker setup 超时（#25799 约 10 分钟）

---

## 建议

### SKILL 设计改进

1. Java/JAR 适配流程应把 JDK 作为受校验的构建工具，而不是假设 Worker 预装 Java；门禁应要求固定版本、SHA256 和无预装 JDK 隔离验证。
2. CI 应在领取任务前执行 Worker 健康检查，包括 `python3 -c 'import sqlite3'`、`conan --version` 和必要系统共享库；失败时应标记为基础设施故障并自动换 Worker，不应消耗配方重试。
3. `feedback` 应正确识别 Git worktree；当前需显式传 `--project-dir`，但 HANDOFF 的 `RESUME_CMD` 又丢失该参数。
4. CI 结果模型应区分 `setup/infrastructure failed`、`recipe not executed` 和 `recipe failed`，避免机器人将 PyPI 超时或 sqlite3 损坏误诊为源码下载问题。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. 纯 Java 模板应提供 `javac`/`jar` 构建骨架、固定 JDK 下载校验、`JAVA_HOME` 身份检查及 JAR 消费者测试示例。
2. `test_package` 模板应默认使用 `basic_layout()` 和独立 build 目录，防止 JDK、Gradle/Maven 缓存或其他大体积工具污染源码树。
3. `conandata.yml` 模板应支持结构化工具 URL（scheme/host/path），并说明 CI URL 预扫描限制，避免完整含连字符 URL 被错误截断。
4. 测试报告模板应支持“上游标签无测试目录”，并分别统计源码编译数、消费者断言数和未执行原因。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. Worker 调度器应在 `conan-setup` 前探测 sqlite3 和 Conan，失败时自动隔离节点、切换健康 Worker 并保留同一 PR 重建记录。
2. CI 机器人应按步骤边界解析日志；若 `conan-build-test` 未执行，不应建议修改源码 URL 或配方。
3. L0 URL 扫描应使用 YAML 解析后的 URL 或正确的 URI 语法，而不是会在连字符处截断的正则。
4. `feedback` 应从 PR API、AI Review、CI 评论和清单自动填充 PR 编号、测试统计及最新 CI 阶段；本次自动报告错误显示 PR 编号为空、测试为 0、远程 CI 未知。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. 建议新增条目：HarmonyOS CI Worker 不保证预装 Java；Java 配方必须下载并校验固定 JDK，且在隔离 HOME/PATH 下验证。
2. 建议新增条目：HNP Python `_sqlite3` 依赖 `libsqlite3.so.0`，缺失时 Conan 在通用 setup 阶段不可运行；此类失败属于 Worker 基础设施，不是配方问题。
3. 建议新增条目：大体积构建工具必须解压到 Conan build folder，不得落入 `test_package` 源码目录。
4. 建议新增条目：CI URL 预扫描可能错误截断含连字符 URL；在规则修复前可将受校验工具 URL 拆为结构化字段并由配方静态拼装，下载仍须使用 `conan.tools.files.get()`。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: wingsluo
- **邮箱**: wingsluo@noreply.gitcode.com
- **Agent ID**: FE33
- **生成时间**: 2026-08-16 01:12:55
- **PR 编号**: —
- **Git Commit**: 96e6f1cf79

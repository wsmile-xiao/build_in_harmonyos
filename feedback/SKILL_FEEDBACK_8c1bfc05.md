# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_8c1bfc05.md`

---

## 背景

- **软件名称**: notcurses
- **版本**: 3.0.17
- **构建日期**: 2026-09-17
- **构建系统**: cmake
- **上游仓库**: https://github.com/dankamongmen/notcurses/archive/refs/tags/v3.0.17.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 10
- **编译依赖**:
- ncurses/6.4
- libunistring/1.0
- libdeflate/1.25
- ncurses/6.4 (Conan)
- libunistring/1.0 (Conan)
- libdeflate/1.25 (Conan)
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 接续修复模式：git fetch 既有分支 feat/notcurses-3.0.17，未重新适配 |
| build | 编译构建 | 成功 | 构建系统: cmake；特性检测 pthread_cancel/ppoll/mremap 均 not found（预期） |
| conan-verify | 配方验证 | G1-G4 全部通过 | 干净构建（G2）经本地下载缓存预置解决 GitHub 直连超时 |
| finish | 归档收尾 | 完成 | W3 本地 CI 模拟通过；close_archive 补丁计数 glob("000*.patch") 漏 0010（框架 bug，警告级） |
| submit | PR提交+AI检视+CI | PR #4519, CI 通过 | AI Review: 旧 19 条意见全闭环（16 resolved + 3 summary 回复），新代码复审「未发现问题」；CI #49315 校验通过 |

### 失败与问题

本次流程未遇到阻塞性问题

本轮（接续修复）发现并处理的非流程问题：
1. **本地 W3 模拟污染 conandata.yml**：build_and_test.sh 的镜像 fallback 步骤会改写工作区 conandata.yml 且此快照版本无还原逻辑，导致 gh-proxy URL 被误提交（W4 审计 P1 抓获）；已从 .orig 恢复并提交修正
2. **get_cursor_location() 无限等待**（上游缺陷级）：pty 冒烟测试深挖发现 notcurses_init 在不答 CPR 的终端上永久挂死（旧补丁同样存在），已加 250ms 有界等待
3. **服务器 main 为孤儿 squash 提交**：本地 origin/main...HEAD 无 merge-base，pre_pr_audit 的三段式 diff 失效；以分支 fork 点重定位本地 main 引用绕过（审计后恢复）

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 3 条
- **引擎命中情况**: 草稿目录 64 条
- **测试统计**: 总计 2, 通过 2, 失败 0, 跳过 0
- **未覆盖的错误模式**: ①OHOS libc「符号存在但头文件不声明」（ppoll/mremap 有符号、无 _GNU_SOURCE 时不声明）——check_symbol_exists 与 check_function_exists 的语义差异值得沉淀；②notcurses 类 TUI 库的无头验证模式（openpty + dup2 stdin + TIOCSWINSZ + TERMINFO 注入）；③musl 系 libc pthread_cancel 缺失的协作式线程收尾模式（stop 标志 + 有界 poll + 信号唤醒 + join + free）

### AI 检视结果

- **检视阶段到达**: Phase 5 (完成)
- **变更摘要评估**: 旧摘要描述 detach 方案已过时；本轮全面重构后触发 /ai review 复审，新审查结论「未发现问题」
- **检视意见数量**: 旧 19 条（R8×11、P1 死锁/泄漏×4、R39×1、汇总×3）+ 新复审 0 条
- **检视意见处理**: 19 条全部 accept 修复并逐条回复（16 条标记已解决；3 条为审查汇总类评论，平台不支持 resolve，已回复说明）；对「先关管道再 join」建议经源码核实后给出拒绝理由（线程阻塞于条件变量非管道读取）并附替代方案

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 通过 (PR 校验)（build #49315：test_package/L0/L1 全过）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 7（PR body 占位符×1、AI 检视意见×1、CI 旧状态误判×1、SKILL_FEEDBACK×1、W4 审计 fail×1 轮、pre_pr_audit 无变更文件×1、submit 门禁状态缺失×1）
- **重试次数**: conan create 4 次（pty 测试迭代：CMake 签名/TERMINO/winsize/stdin dup2 各修一轮）；审计 2 轮（首轮 fail→修复→复审 pass）
- **关键瓶颈**: ①GitHub 直连超时（已用 core.sources:download_cache 预置 tarball 解决）；②W4 审计 fail 后的修复-复验循环（本轮最大耗时项，但发现了 2 个真实缺陷，值得）；③zsh 不做变量分词导致批量回复脚本静默失败（改为显式脚本文件）
- **耗时较长的步骤**: pty 功能测试调试（约 90 分钟，含 get_cursor_location 缺陷发现与修复）；W4 审计两轮（约 40 分钟）；git fetch 大仓分支（13 分钟）

---

## 建议

### SKILL 设计改进

1. **build_and_test.sh 镜像改写需还原**（P0 级）：本快照的镜像 fallback 步骤 `cp conandata.yml .orig` 后改写文件但无 trap 还原——本地 W3 模拟会污染工作区并把镜像 URL 带进提交（本轮 W4 审计抓获）。建议对齐 v12.17 的 .build-cache/predl_cache + trap EXIT 还原方案
2. **close_archive 补丁计数 glob 应为 `*.patch`**：现用 `glob("000*.patch")` 漏掉 0010 及以后编号，10 补丁报 9，产生假性"补丁数不一致"警告
3. **服务器 main 孤儿化后的审计基线**：pre_pr_audit 的 `origin/main...HEAD` 在历史 squash 后失效（no merge base）。建议 fallback 到两段式 tree diff（git diff origin/main HEAD --name-only），与平台 PR diff 语义一致
4. **submit --resume 对 CI 旧状态的误判**：resume 直接读最新 CI 评论（可能是历史失败），未区分"push 后是否有新构建"。建议 resume 先检查最新构建是否包含当前 HEAD commit，必要时自动 /rebuild（v12.12 已有此设计，本快照未含）

### 模板改进

1. test_package 模板可增加「功能性测试」段（pty/openpty 驱动模式）——TUI/终端类库的 R40 验证普遍需要，本次摸索出的 dup2(stdin)+TIOCSWINSZ+TERMINFO 注入套路可模板化
2. PR body 生成器对「上游测试用例统计」直接复用适配后统计（2/2），与 R51 期望的上游清点（46 doctest）不一致，需人工改写；建议从 test-report.md 的上游清点段单独解析
3. conanfile 模板可预置 NOTCURSES 式「特性检测 + 行为选项」分层注释示例（API 可用性→check_symbol_exists；运行时行为→CMake option），本次 R8 闭环走通的路线对后续 TUI/线程类库适配有直接复用价值

### 自动化补全

1. **conan 源码下载缓存预置**：GitHub 直连超时是常态，建议 W3/finish 前自动检测 conandata sha256 是否已在 core.sources:download_cache，缺失时提示预置（本次手动配置耗时 20 分钟）
2. **W4 审计 fail→修复→复审循环可半自动**：首轮审计意见若为明确 P1（如 URL 违规），修复后自动重新 generate 输入并触发复审
3. **检视意见批量回复**：handle-review-opinion 逐条调用 API 限速慢；可支持 --batch JSON 文件模式

### 知识图谱覆盖

建议新增 E-entry（已具备完整实证）：
1. **OHOS libc 符号/声明分离模式**：ppoll/mremap 符号在 libc 存在但默认头文件不声明（需 _GNU_SOURCE）→ check_symbol_exists（含头文件）与 check_function_exists（仅链接）语义差异；notcurses 案例中检测上下文必须与目标编译单元一致
2. **无 pthread_cancel 的协作式线程收尾**：无限循环线程（poll/cond_wait/nanosleep 阻塞）需 stop 标志 + 有界 poll 超时 + 信号唤醒（SIGWINCH 类已注册 handler 的信号）+ join + 资源释放；detach+泄漏方案会被检视驳回
3. **TUI 库无头功能测试模式**：openpty + TIOCSWINSZ + dup2 slave→stdin（输入层固定读 fd 0）+ TERM/TERMINFO 从 conan 包注入（静态传递依赖会被剪枝，需直接 require）
4. **notcurses init 无限等待族**：不答查询的终端上 get_cursor_location（CPR）无限 cond_wait → timedwait 有界化；DA1/DA2/DSRCPR 同族（已有跳过方案，CPR 是本轮新发现）

---

## 作者

- **姓名**: ohpcd-robot
- **邮箱**: ohpcd-robot@noreply.gitcode.com
- **Agent ID**: 5191
- **生成时间**: 2026-09-17 14:05:54
- **PR 编号**: 4519
- **Git Commit**: 4a9577932

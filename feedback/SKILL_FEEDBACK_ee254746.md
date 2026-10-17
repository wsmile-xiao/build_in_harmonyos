# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_ee254746.md`

---

## 背景

- **软件名称**: sdl3
- **版本**: 3.4.8
- **构建日期**: 2026-09-20
- **构建系统**: cmake
- **上游仓库**: https://github.com/libsdl-org/SDL
- **适配路径**: 路径 B（探索性编译 + conan 配方固化；前会话已建 PR #6209，本次在其分支上继续优化）
- **补丁数量**: 5
- **编译依赖**:
无
- **最终状态**: 成功（conan-verify 全绿，上游测试 24/25，PR #6209 已更新）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | GitHub 直连超时，本地用镜像下载（sha256 与官方一致），配方只写官方 URL |
| lang-preflight | 语言预检 | 通过（有波折） | 检测器把 android-project/ 里的 build.gradle 误判为 gradle 项目，临时移出后通过（detected=cpp，C 占 89%） |
| build | 编译构建 | 成功 | cmake + SDL_TESTS=ON，上游测试 24/25 通过 |
| conan-verify | 配方验证 | 全绿（G0-G4+L2/L4/L5） | testrwlock 因 musl rwlock 写者饥饿排除（有完整实验证据） |
| finish | 归档收尾 | 完成 | W3 本地 CI 模拟通过（第一次 full 模式误报：main 历史遗留 cloog/kics 状态文件，建分支后 incremental 模式通过） |
| submit | PR提交+AI检视+CI | 增量 push 到 PR #6209 | AI Review 2 条意见已回复（1 Info + 1 Critical 误判已用 3.4.8 头文件证据澄清）；/rebuild 已触发 |

### 失败与问题

| # | 问题 | 处置 |
|---|------|------|
| 1 | lang-preflight 误判 mixed（android-project/build.gradle 干扰） | 移出 android-project 重检通过；检测器缺陷：gradle 判定用全递归文件名集合，而 cmake/package.json 判定只看顶层——不一致 |
| 2 | test_package 首版用 SDL2 风格 API（SDL_GetVersion 填结构体）编译失败 | SDL3 3.2+ 改为 int 返回；改用 SDL_VERSION 整数比较后通过 |
| 3 | testrwlock CTest 超时死锁 | 根因：OHOS musl pthread_rwlock 无写者排队公平性；裸探针 + --nbthreads 1 双实验证实为 libc 差异非逻辑缺陷；ctest -E 排除并全文档记录 |
| 4 | conan-verify 镜像注入回滚污染 conandata.yml（gh-proxy 首选 URL 提交进 git） | 从提交恢复官方 URL；建议工具在注入时跳过"已被 git add 的文件"或退出前强制校验回滚 |
| 5 | junk_check full 模式扫到 main 历史遗留（cloog/kics 的 .build-closed 等 3 个被跟踪的运行时状态文件） | 建分支后走 incremental 模式通过；**main 遗留垃圾建议主编清理**（不属于本 PR 范围） |
| 6 | reports/ 被 .gitignore 全局排除，test-report.md 需 git add -f | SDL2 等先例已 force-add；建议 .gitignore 排除模式收窄到具体文件名 |

### 知识图谱使用情况

- **引用知识条目**: E267（CMAKE_SYSTEM_NAME MATCHES 平台检测模式，验证补丁 0001 用法）、E017/E092（镜像注入/平台模块，工具自动）
- **新增知识草稿**: 2 条（DRAFT-musl-rwlock-writer-starvation、随 sdl2-compat 的 DRAFT-cmakedefine-guard-unix-false）
- **引擎命中情况**: conan-verify G2 失败时命中 E267（首次 ctest 失败时给出的匹配相关性不高，实际根因需自行实验）
- **测试统计**: 上游 CTest 注册 25，通过 24，失败 0，跳过 1（testrwlock，文档化排除）；test_package 1/1
- **未覆盖的错误模式**: musl rwlock 写者饥饿（已补草稿）；SDL3 SDL_GetVersion API 形态在 3.2 前后不同（小众，暂不入库）

### AI 检视结果

- **检视阶段到达**: Phase 4（意见处理完毕）
- **变更摘要评估**: atomgit-bot 逐文件核查 conandata/0005 补丁 no issues；唯一 Critical 集中在 test.c 的 SDL_GetVersion 用法
- **检视意见数量**: 2 条（1 Info + 1 Critical）
- **检视意见处理**: Critical 为误判（bot 引用的是 SDL3 早期 3.0/3.1.x 的 SDL_version 返回形态；SDL 3.2 起官方改为 int，3.4.8 头文件 160 行实证 + CI #49336 编译运行通过佐证）——已回复澄清并标注 accept（代码本来就是正确形态）；Info 无需动作。教训：bot 的 API 知识可能滞后于库版本演进，回复时附头文件行号与 CI 证据最有效。

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（incremental junk_check + build_and_test.sh 全绿）
- **远程 CI (PR 校验)**: 9-17 同代码路径多次 ✅（#49336 等）；本次增量（SDL_TESTS=ON + 0005 + test 增强）后 /rebuild 已评论触发，调度处理中
- **CI 失败原因**: 无（本次）

### 效率分析

- **HANDOFF 次数**: 6（lang_mismatch 误报、W3 junk_check、W4 审计、自检 manifest/packaging、submit 状态文件缺失、conan-verify G2×2）
- **重试次数**: conan-verify 3 次（test API 修复、ctest 排除、镜像污染清理）
- **关键瓶颈**: ① CI 调度排队（/rebuild 评论后 50 分钟仍在调度）；② W4 审计子任务往返；③ conan-verify 每次 8-12 分钟全量重建（无 ccache 增量）
- **耗时较长的步骤**: conan-verify（3 轮约 35 分钟）、W4 审计（含交叉验证约 15 分钟）、CI 等待（不可控）

---

## 建议

### SKILL 设计改进

1. **lang-preflight 检测器缺陷**：`_manifest_scan` 中 gradle/maven 判定用全递归 `names` 集合（`android-project/app/build.gradle` 非顶层也命中），而 cmake/package.json 用 `tops`（仅顶层）。建议全部 manifest 判定统一为"仅顶层目录 + 声明式子目录白名单（如 BUILD_ROOT）"，或至少 gradle 判定降级为顶层匹配。本次 SDL3 因 android-project 辅助工程被误判 mixed，差点触发 env_unsupported 误终止。
2. **conan-verify 镜像注入的回滚可靠性**：ghfast.top 注入在 HANDOFF/异常退出时可能残留（本次污染已提交的 conandata.yml，靠 git 历史恢复）。建议：注入前把 conandata.yml 内容哈希记入状态文件，任何 ohc-run 入口检测到残留注入即自动回滚（现在只有崩溃恢复守卫覆盖部分场景）。
3. **W4 审计对"分支无共同祖先"场景的适配**：pre_pr_audit.py generate 依赖 `git diff origin/main...HEAD`，历史重写仓库（无 merge base）直接报"没有变更文件"。建议回退为 `git diff origin/main HEAD -- <pkg_dir>` 或按提交范围枚举。
4. **junk_check full 模式的 main 遗留问题**：cloog/kics 3 个被跟踪的运行时状态文件长期污染所有 full 模式扫描（本次在 main 上直接跑任何包的 finish 都会撞上）。建议主编一次性清理 main，并给 JC1 加"已跟踪状态文件"豁免提示。
5. **submit --resume 对"PR 已存在但状态文件缺失"场景**：本次 PR #6209 由前会话创建，本会话 push 后跑 submit --resume 报"无 PR 编号无法恢复"，而正常 submit 又有重复建 PR 风险（靠 create-pr 的 15s 复核兜底）。建议 submit 入口先用 list-prs --source-branch 探测已有 PR 并回填状态文件。

### 模板改进

1. test_package/CMakeLists.txt 模板生成的 `find_package(<name>)` + `<name>::<name>` 命名对"上游有官方 CMake config 的库"（SDL3/SDL2 等）不适用，建议 conan-init 时提示 AI 核对上游 config 名（cmake_file_name 属性），模板注释里给出提示。
2. test_package 骨架的 test.c 是 print-only 空壳（PF3 必拦），conan-init 生成后 AI 必须重写——建议骨架直接生成"调用被测包最基础 API"的 TODO 注释框架（列出需替换的调用点），减少一轮 conan-verify 失败。

### 自动化补全

1. "SDL3 头文件版本核对"类 API 形态验证（SDL_GetVersion 返回类型等）可以由 recipe-search 或知识库提示：生成 test_package 前自动 grep 上游 include/ 目录的关键签名，避免编译失败一轮。
2. CI 调度排队时（/rebuild 评论 30 分钟无 CI 回应）建议 gitcode_pr.py 提供 re-trigger 或状态探针命令，目前只能反复 ci-status 轮询。

### 知识图谱覆盖

1. **musl pthread_rwlock 写者饥饿**（本次新增 DRAFT-musl-rwlock-writer-starvation.kv）：建议转正，testrwlock 类饱和并发测试在 OHOS 上是普适陷阱。
2. **cmakedefine 守卫变量在 CMake 平台变量缺失时失效**（随 sdl2-compat PR 的 DRAFT-cmakedefine-guard-unix-false.kv）：建议转正，E267 的平台检测模式 + cmakedefine 守卫的组合是 OHOS cmake 适配的高频坑。
3. 引擎对"ctest 测试超时"类错误（本次 testrwlock Timeout）无现成条目，匹配建议质量一般——可考虑新增"test 超时/死锁"类别的通用排查条目（区分逻辑死锁/平台语义差异/超时预算不足三条路径）。

---

## 作者

- **姓名**: ohpcd-robot
- **邮箱**: ohpcd-robot@noreply.gitcode.com
- **Agent ID**: 0411
- **生成时间**: 2026-09-20 10:03:11（填充: 2026-09-20 12:25）
- **PR 编号**: #6209（sdl3 3.4.8，open）
- **Git Commit**: 12e341702

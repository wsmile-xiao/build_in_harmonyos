# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_cdd237da.md`

---

## 背景

- **软件名称**: pokerstove
- **版本**: 1.1
- **构建日期**: 2026-09-03
- **构建系统**: cmake
- **上游仓库**: https://github.com/andrewprock/pokerstove/archive/refs/tags/v1.1.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1
- **编译依赖**:
- boost/1.84.0
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: cmake |
| conan-verify | 配方验证 | 通过 | 8 道门禁全部通过（G1 配方完整性/G0 预构建风险/G2 conan create 干净构建含三层 test_package/G3 系统同名库/G4 产物完整性 L2/L4/L5），报告 archives/p/pokerstove/1.1/reports/conan-verify-report.md |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | PR #7885, CI 通过 | AI Review: Phase 1 (等待摘要) |

### 失败与问题

- **1**: 根因=boost/core/detail/sp_thread_sleep.hpp: `use of undeclared identifier 'pthread_setcancelstate'`（E127 命中）, 解决方案=OHOS musl libc 不提供 pthread_setcancelstate（同 Android）；conan boost/1.84.0 包把 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 宏挂在 boost_headers 组件 defines 上，只有链接 Boost 目标的程序能继承，pokerstove 的 peval/penum 库源码只 include boost 头不链接 Boost
- **2**: 根因=cmake 4.1.2 配置报错 `Compatibility with CMake < 3.5 has been removed`（根/子 CMakeLists 均要求 3.0）, 解决方案=cmake 4.x 移除 <3.5 兼容
- **3**: 根因=conan create 主包成功但 test_package 编译报 `boost/operators.hpp file not found`（新知识，草稿 DRAFT-conan2-cmakedeps-transitive-include-strip）, 解决方案=Conan 2 CMakeDeps 只对消费者直接 requires 的包生成含 include dirs 的完整配置；经 pokerstove 传递引入的 boost 在 test_package 端 `boost_Boost_headers_INCLUDE_DIRS_RELEASE` 为空（主包构建有 toolchain CMAKE_INCLUDE_PATH 兜底故不报错，形成"主包过/测试挂"隐蔽差异；requires visible=True 实测无效）
- **4**: 根因=首次 conan create 报 package() `TypeError: unsupported operand type(s) for /: 'str' and 'str'`, 解决方案=conan 2 的 self.source_folder/self.package_folder 是 str 不是 Path
- **5**: 根因=打包后发现 include/ 下混入 gtest/gmock 头文件+静态库, 解决方案=上游捆绑 googletest 的 INSTALL_GTEST 默认 ON，其 install 规则随 cmake.install() 装进包

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 4 条
- **引擎命中情况**: 草稿目录 84 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: Conan 2 CMakeDeps 对消费端传递依赖生成的配置 include 为空（boost_INCLUDE_DIRS_RELEASE 空 → boost 头 not found；主包构建因 toolchain CMAKE_INCLUDE_PATH 兜底不报错，形成"主包过/测试挂"隐蔽差异；requires visible=True 实测无效）——已提交草稿 DRAFT-conan2-cmakedeps-transitive-include-strip（kv+md），建议编入正式 E 条目

### AI 检视结果

- **检视阶段到达**: Phase 4 (CI 通过)
- **变更摘要评估**: 摘要准确覆盖 5 大改动面（平台守卫补丁/Conan 配方/消费者测试/传递依赖知识条目/归档元数据），关键细节（967/990 断言值、INSTALL_GTEST、cpp_info.libs 顺序）均如实提取
- **检视意见数量**: 0（AI 代码审查结论"✅ 未发现问题"）
- **检视意见处理**: 无需处理

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 通过 (PR 校验)
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 2（pr_creation_failed——fork 工作流预期路径（跨仓 head 404/preflight PF0 git 不可见）；ai_review_summary_timeout ×2——monitor-review 框架 bug 假超时）
- **重试次数**: conan create 6 轮迭代（package() str/str TypeError→googletest INSTALL_GTEST 污染→CMakeDeps 传递 include 为空→visible=True 无效→conan1 API cmake.test(output=)→ps-colex 断言语义修正）；W3 junk_check full 模式误伤他人遗留文件 1 次（分支无 commit 时增量 diff 为空回退全仓扫描，commit 后通过）；E017 镜像注入恢复 bug 致 conandata.yml url 变镜像列表 1 次（git checkout 恢复）
- **关键瓶颈**: ① scripts/gitcode_pr.py cmd_monitor_review 的 NameError（unreplied_opinions 未定义，应为 review_opinions）导致 submit --resume Phase 1 轮询 6 连败假超时 ×2，累计浪费约 1 小时（摘要与审查评论实际早已生成）；② 本机 OpenHarmony Python subprocess 不做 PATH 搜索（posix_spawnp 对裸命令名一律 FileNotFoundError，ls/uname 同挂），框架脚本裸名 ["git",...] 调用必失败，需 shutil.which wrapper（本次 preflight-runner.py monkeypatch 方案验证有效）
- **耗时较长的步骤**: ps-eval 单手全枚举 1.78B 次评估约 110s；conan create 全流程每轮 3-5 分钟（含 test_package 三层）；AI Review/CI 轮询等待合计约 70 分钟
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 7 个事件（含 3 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-03T12:56:11 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/pokerstove-1.1 --target main --title 'feat(pokerstove): 1.1 适配完成' |
| 2026-09-03T12:58:22 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-03T12:58:22 | skeleton_created | resume_pr_exists |
| 2026-09-03T13:28:25 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #7885 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 7885 \| 摘要出现后: python3 scripts/ohc-run.py submit pokerstove 1.1 --resume |
| 2026-09-03T13:31:13 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-03T13:31:13 | skeleton_exists | resume_pr_exists |
| 2026-09-03T14:01:16 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #7885 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 7885 \| 摘要出现后: python3 scripts/ohc-run.py submit pokerstove 1.1 --resume |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **修复 scripts/gitcode_pr.py cmd_monitor_review 的 NameError**：`unreplied_opinions` 未定义（应为 `review_opinions`），异常被上层当"获取检视状态失败"网络错误无限重试，造成 Phase 1 假超时（本任务累计 2 次 30 分钟超时、约 1 小时浪费）。建议框架 PR 修复并在 except 分支打印真实异常。
2. **junk_check incremental 判定的空 diff 回退误伤**：分支尚无 commit 时 `git diff origin/main...HEAD` 为空 → 回退 full 全仓模式 → 他人归档的遗留状态文件（embree/flatcv/libmorton/goaccess 等 13 个）被误判为本次 junk 阻塞 finish。pngnq 与 pokerstove 连续踩坑。建议：finish 前置检查"当前分支相对 base 无提交则提示先 commit"，或 full 模式下仅对 JC1/JC5 报 warning 不阻塞（JC 本意是拦本 PR 引入的文件）。
3. **E017 镜像注入/恢复应原子化**：注入时把 conandata.yml url 改写为列表，"恢复"后未还原单官方 URL（本任务出现 gh-proxy.com 残留，靠 git checkout 恢复；PR6091 教训同源）。建议注入前备份原文件全文、恢复时整体还原，或注入后校验 diff 为空。
4. clean-verify (G0) 只支持 autotools（硬编码 ./configure + make），对 cmake 项目必报 exit 127；cmake 项目的干净构建已由 conan-verify G2 覆盖，建议 finish 按 build_system 跳过或标注 not-applicable，避免误导性 FAIL 警告。

### 模板改进

1. conanfile-cmake.py.tmpl 的 package() 示例建议直接用 `from pathlib import Path` + `Path(self.source_folder) / ...` 写法（conan 2 的 folder 属性是 str，模板常见的 `/` 运算符写法直接 TypeError）。
2. test_package 模板建议增加提示："若被测库公共头 include 传递依赖（尤其 boost），test_package 需显式 requires 该传递依赖"（CMakeDeps 消费端只为直接依赖生成完整 include 配置）。
3. 捆绑 googletest 的上游项目模板提示：CMakeToolchain 注入 `INSTALL_GTEST=OFF`（上游官方选项），否则 gtest/gmock 头与静态库经 cmake.install() 污染包。

### 自动化补全

1. 框架脚本所有 subprocess 裸名调用（git/cmake/tar 等）建议统一 `shutil.which()` 解析绝对路径：本机 OpenHarmony Python 的 posix_spawnp 不做 PATH 搜索（ls/uname 均 FileNotFoundError），preflight.py 的 PF0 即因此必挂（本次用 monkeypatch wrapper 绕过，框架文件只读未改）。
2. pre_pr_audit.py generate 时可自动校验 conandata.yml url 是否为镜像列表形态（对照 git HEAD），把 E017 注入残留从"人工自审发现"提前为自动拦截。
3. submit --resume 检测到 PR 评论里已有"变更摘要"与"代码审查"结论时可直接跳过 Phase 1 轮询（本次两次假超时均为摘要已存在却因 API bug 不可见）。

### 知识图谱覆盖

1. 建议编入 DRAFT-conan2-cmakedeps-transitive-include-strip（本次已提交 kv+md）：Conan 2 CMakeDeps 消费端传递依赖 include 置空的根因/修复/反模式（visible=True 无效、CPATH 兜底禁止）。
2. 建议新增环境类知识条目：本机 OpenHarmony Python subprocess 不做 PATH 搜索（posix_spawnp 限制）——所有子进程调用需绝对路径或 shutil.which（preflight/conan-verify 多处受影响）。
3. 建议新增工作流知识条目：E017 ghfast/gh-proxy 注入恢复 bug 的识别与 git checkout 恢复法（PR6091 教训 + 本次复现）。

---

## 作者

- **姓名**: ningyu
- **邮箱**: 405888464@qq.com
- **Agent ID**: 7496
- **生成时间**: 2026-09-03 12:58:22
- **PR 编号**: 7885
- **Git Commit**: 0b91eef3d2

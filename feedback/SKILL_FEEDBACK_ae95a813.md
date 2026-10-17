# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_ae95a813.md`

---

## 背景

- **软件名称**: include-what-you-use
- **版本**: 0.26.src
- **构建日期**: 2026-09-27
- **构建系统**: cmake
- **上游仓库**: https://codeload.github.com/include-what-you-use/include-what-you-use/tar.gz/refs/tags/0.26
- **适配路径**: 路径 C（高难度挑战，四特征命中 3/4）
- **补丁数量**: 0
- **编译依赖**:
- clang/22.1.8
- llvm/22.1.0
- zlib/1.3.2
- zstd/1.5.7
- xz/5.8.3.1
- libedit/20240808
- z3/4.15.4
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: cmake |
| conan-verify | 配方验证 | 通过 | G0-G4+L2/L4/L5 全过；审计修复后 14:37 复验，Package id 5716606709546343183208a48e8256886f517a6c |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 通过 | AI Review: 变更摘要 + 代码审查"未发现问题"；远程 CI #62723 校验通过 |

### 失败与问题

- **1**: 根因=init-build 主源 URL（releases/download/0.26/0.26.tar.gz）HTTP 404；备用链（github.com/archive）连接被重置；curl 直连 github.com:443 TCP 超时, 解决方案=设备出口网络对 github.com 主域不可达（拦截层返回 404/断连）
- **2**: 根因=init-build 将构建系统误判为 autotools（模板选择走 autotools 分支）, 解决方案=启发式检测未识别 CMake（lang-preflight 正确判为 cmake）
- **3**: 根因=configure 失败：HandleLLVMOptions.cmake:249 "Unable to determine platform"（设备 `uname -s`=HarmonyOS，LLVM 22 平台分支无 HarmonyOS）, 解决方案=OHOS 内核标识不在 LLVM 已知平台表
- **4**: 根因=iwyu 运行报 `fatal error: 'vector' file not found`（C++ 标准库头找不到）, 解决方案=clang 包不含 C++ 标准库头；iwyu 内置 driver 默认搜索路径（/usr/include/c++…）在 OHOS 设备不存在
- **5**: 根因=C 库头（stdio.h 等）在 C++ 模式下解析异常：`cstddef:50: no member named 'nullptr_t'`（CPATH 方案）/ `stdio.h:249: unknown type name 'uint64_t'`（shim builtin 覆盖方案）, 解决方案=OHOS sysroot 为 musl 系 C 库（`__NEED_*` + `bits/alltypes.h` 机制）；`::nullptr_t` 仅编译器 builtin stddef.h 在 C++ 模式提供；用 CPATH 类环境变量注入头目录会被 clang 归为 user include（破坏 IWYU 归属判断，25 条测试失败）；用 builtin 头覆盖 C 库 stdint.h 破坏 musl `__NEED_*` 链
- **6**: 根因=clang-cl 模式测试（clmode/preprocess_msvc/use_pch_msvc）注入 `-isystem` 报 "unknown argument ignored in clang-cl"；`--driver-mode=cl`（LLVM 18+ 新式 cl 模式选择，IWYU_ARGS 实测为此写法）未被识别, 解决方案=clang-cl driver 拒绝 -isystem/--sysroot 等非 MSVC 风格参数；测试文件 IWYU_ARGS 实为 `--driver-mode=cl …`（早期 grep 视图为 `-clang-cl`，文件系统瞬时视图不一致导致误判）
- **7**: 根因=dashdash 测试（IWYU_ARGS=`-c --`）注入 -isystem 报 "no such file or directory: '-isystem'", 解决方案=run_iwyu_tests.py 把 IWYU_EXTRA_ARGS 追加在测试参数之后（`--` 之后→被当作输入文件）
- **8**: 根因=二进制运行被 OHOS XPM 拒绝（未签名）, 解决方案=OHOS 要求可执行文件带代码签名
- **9**: 根因=py 测试（fix_includes_test）要求 `IWYU_BINARY` 环境变量（fix_includes.py:148 `os.environ['IWYU_BINARY']` 无默认值）, 解决方案=上游 CI 在 Actions 环境注入该变量
- **10**: 根因=设备 /data/service/hnp/bin/grep 为损坏 ELF（"cannot execute binary file"），shell grep 静默失败导致多次误判"无匹配", 解决方案=设备预装工具链个别二进制不可用
- **11**: 根因=conan create source() 报 `BadZipFile: File is not a zip file`, 解决方案=codeload URL 的 basename 是 tag 名 `0.26`（无扩展名）；conan 2.29 `get()`→`unzip()` 按**文件名后缀**判定压缩格式（conan/tools/files/files.py），无后缀回退 zip

### 知识图谱使用情况

- **引用知识条目**: 无 E 条目引用（参照 llvm/22.1.0、clang/22.1.8 配方先例：Platform/HarmonyOS.cmake 平台模块、XPM 签名、设备工具链路径惯例、-isystem 注入模式）
- **新增知识草稿**: E429-draft-A141.kv/.md（conan 2.29 get() 对 codeload 无扩展名归档回退 zip 报 BadZipFile，conandata filename 字段修复）
- **引擎命中情况**: 草稿目录 2095 条
- **测试统计**: 总计 232, 通过 228, 失败 3, 跳过 1（上游全量 223/227：1 合法 SKIP + 3 标准库实现差异失败；鸿蒙特有消费者用例 5/5）
- **未覆盖的错误模式**: OHOS libc++/musl 标准库实现导致的 iwyu include 归属差异（本任务 3 条 e2e 失败：test_badinc/test_libbuiltins/test_std_size_t），建议新增条目（见"知识图谱覆盖"建议 #2）

### AI 检视结果

- **检视阶段到达**: Phase 5 完成（变更摘要 + 代码审查"未发现问题"，无待处理意见）
- **变更摘要评估**: 已评估：摘要与实际改动一致（平台模块/LLVM_DIR 直指/资源目录重定向/自包含运行时/签名/test_package/E429 草稿），无必须修改的点
- **检视意见数量**: 0（AI 检视评论"未发现问题"）
- **检视意见处理**: 无检视意见需处理；W4 本地独立审计 2 P2 + 3 P3 项已全部修复并 W3 复验（第二 commit b085bd7cc：方法顺序/shebang/C2 输出断言入 CI/知识草稿 .md 补全）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 通过（CI #62723 @ CI-022，Conan test_package/L0/L1 全过，2026-09-27 14:53 更新校验通过）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 2（G0 clean-verify 非阻塞 HANDOFF ×2：finish 首次与 14:37 复验，同类平台限制 exit 127，不阻塞）
- **重试次数**: 1（审计修复后 W3 全量复验 1 轮；远程 CI 1 轮即绿，无修复轮）
- **关键瓶颈**: ① 设备出口网络拦截 github.com 主域（release 资产链 404）→ codeload + conandata filename 字段（沉淀 E429 草稿）；② iwyu 标准库头注入策略试错（CPATH 类环境变量被 clang 归为 user include 破坏 IWYU 归属，25-32 条 e2e 失败后才定 -isystem 双层注入）；③ gitcode token 过期 401，PR 通道人工切换 atomgit OAuth
- **耗时较长的步骤**: conan create ×2（W3 复验）与真机 ctest 全量（227 条，e2e 224 条 Total Test time 20.98s）；远程 CI #62723 仅约 6 分钟（worker 依赖缓存命中）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 4 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-27T05:33:18 | lang_checked | detected=cpp 与任务 cpp 匹配 |
| 2026-09-27T08:42:58 | skeleton_created | result_partial |
| 2026-09-27T13:55:25 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-09-27T13:55:26 | skeleton_exists | resume_pr_exists |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **fork 场景 create-pr 404**：`submit` 内置 create-pr 传裸 source 分支名（submission.py），跨 fork PR 必 404——本任务被迫手动经 atomgit 通道建 PR + 手工 seed `.submit-state.json`，submit 内置监控闭环（AI Review/CI 自动续）断裂。建议：检测跨 fork 时自动用 `owner:branch` 形态，或支持 `OHC_PR_HEAD` 环境变量显式指定。
2. **result success 硬闸的 CI 核验通道单一**：依赖 gitcode API 拉 PR 评论，token 过期 401 的 worker 只能 `--no-ci-verify` 自证。建议核验通道支持 atomgit OAuth，或 `.ci-result.json` 哈希 + 本地日志兜底。
3. **G0 clean-verify 本机恒失败（exit 127）**：每次 finish 输出非阻塞 HANDOFF，噪音高。建议支持 `OHC_SKIP_CLEAN_VERIFY=1` 显式跳过并在报告标注。
4. **R46 生命周期草稿 milestone 无顺序保护**：finish 重跑后 milestone 从 `pr_created` 回退为 `w3_finish_started`（挂点无单调性约束）。建议 milestone 取"已完成最远阶段"语义（max），不回退。

### 模板改进

1. **test_package/conanfile.py 模板缺 shebang + 模块 docstring**（W4 审计 P2 指出），应内置到模板。
2. **conanfile.py 模板方法顺序**：生成产物 `source()` 在 `layout()` 前，与规范顺序（export_sources→requirements→layout→source→generate→build→package→package_info）不符（W4 审计 P2），模板应对齐规范序。
3. **积分赛 PR 模板建议增加"高难度判定四特征命中表"可选块**：高难度挑战标题的 PR 需要四特征（强绑定私有接口/私有构建工具链/汇编闭源特殊调度/巨大依赖链）证据，本 PR 自检后采纳该格式（与参考 PR !12038 一致）。
4. **test_package 模板可增加 -isystem 注入模式注释样例**：SDK libcxx-ohos + musl sysroot 双层 -isystem 是 clang 系工具（iwyu 类）在 OHOS 的通用前提，CPATH 类环境变量方案会破坏 IWYU 归属判断（实测 25-32 条 e2e 失败）。

### 自动化补全

1. **init-build 构建系统误判**：纯 cmake 项目被启发式判为 autotools（模板选择走错分支），lang-preflight 判对但主流程未复用其结果。建议构建系统检测优先 CMakeLists.txt 并复用 lang-preflight 判定。
2. **设备工具链完整性自检**：`check-env` 应预检 `/data/service/hnp/bin/` 个别二进制可执行性——本次 grep 为损坏 ELF（"cannot execute binary file"）致 shell 管道静默失败、多次误判"无匹配"（问题台账 #10）。
3. **token 过期自动切换**：gitcode token 401 后 PR 通道操作（建 PR/评论/CI 触发/状态查询）应自动回退 atomgit OAuth 通道，本次为人工发现并手工切换。
4. **conandata filename 字段自动修复**：conan create 在 source() 阶段命中 `BadZipFile: File is not a zip file` 且 URL basename 无扩展名时，引擎应直接给出"conandata 增加 filename 字段"处方（本次靠读 conan 源码 files.py 人工定位；已沉淀 E429 草稿，待 promote 后引擎可命中）。

### 知识图谱覆盖

1. **E429-draft-A141**（conan get() codeload 无扩展名归档 BadZipFile → conandata filename 字段）：本任务草稿，提请主编审核 promote。
2. **建议新增"OHOS libc++/musl 标准库实现导致的 iwyu include 归属差异"**：本任务 3 条 e2e 失败（test_badinc std::string 经 allocator/char_traits 间接使用、test_libbuiltins std::pow using-decl 可见性、test_std_size_t musl stdio.h 直接定义 size_t）均为标准库实现差异而非适配缺陷，同类 clang 前端工具（iwyu/modernize 类）必然复现。error_signature 建议：`should add these lines` 与期望不匹配 / `is defined in` 行缺失。
3. **建议新增"OHOS XPM 未签名二进制执行拒绝"**（问题台账 #8）：iwyu ELF + 捆绑 .so 的 objcopy 去 .codesign + 自签链路，若现有条目未覆盖此形态（本任务为可执行工具 + 捆绑动态库双签名）。
4. **建议新增"clang-cl driver 模式拒绝 -isystem/--sysroot"**（问题台账 #6）：`--driver-mode=cl`（LLVM 18+ 新式 cl 选择）下 wrapper 需按驱动模式分支注入；`-c --` 参数后追加的 EXTRA_ARGS 会被当输入文件（台账 #7，dashdash 用例）。

---

## 作者

- **姓名**: gcw_Pp8UzTBn
- **邮箱**: 2280277721@qq.com
- **Agent ID**: 07A1
- **生成时间**: 2026-09-27 08:42:58
- **PR 编号**: 13202
- **Git Commit**: b085bd7cc（CI 绿 commit；首 commit 516fed616 为适配主体）

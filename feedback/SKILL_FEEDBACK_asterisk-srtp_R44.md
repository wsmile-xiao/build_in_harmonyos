# SKILL 执行流程反馈报告

> 本报告由适配 Agent 自动生成，记录 asterisk-srtp 22.10.1 适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_asterisk-srtp_R44.md`
> 触发: 合并人 goblinrs 2026-08-24 PR 评论「请通过FEEDBACK反馈SKILL问题」——原直接修改
> `references/iron-rules.md`（基础设施，协作者只读）已撤出（commit cf83653261），规则建议改由本文件提交。

---

## 背景

- **软件名称**: asterisk-srtp
- **版本**: 22.10.1
- **构建日期**: 2026-08-21 ~ 2026-08-22
- **构建系统**: autotools（configure + menuselect 子 configure + make）
- **上游仓库**: https://github.com/asterisk/asterisk（仅 res/res_srtp 模块）
- **适配路径**: 路径 A（基础适配）+ 路径 B（知识库扩展贡献）
- **补丁数量**: 5
- **编译依赖**: srtp/2.8.0、openssl/3.5.6.1、libedit/20240808、libxml2/2.15.3、ncurses/6.6、e2fsprogs/1.47.4（libuuid）、jansson/2.15.1.1、sqlite3/3.49.1
- **最终状态**: 成功（CI #29569 PASSED，AI Review 通过）

---

## 情况

### 执行概要

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build / build | 源码准备与探索 | 完成 | in-source 构建规避 HMDFS 077 umask 问题 |
| conan create | 配方构建 | 多轮失败→成功 | 19 轮 CI 全部 `C compiler cannot create executables`，方案 C 后通过 |
| conan-verify | 配方验证 | 通过 | G0–G4 全 PASS；test_package 实测 ELF 加载断言通过 |
| submit | PR 提交+CI | 通过 | PR #6055；CI #29569（耗时 48min）首次真正 PASSED |

### 失败与问题（核心教训）

1. **共享 SYS_PREFIX 注入污染**（19 轮 CI 失败的根因）：`generate()` 向共享目录
   `/storage/Users/currentUser/usr/local` 注入依赖库。CI worker 与本地**共享同一台机器的文件系统**，
   CI 从制品仓下载的依赖包 revision 与本地不同（共享库版 vs 静态库版、.pc 布局不同），注入后污染
   共享目录 → clang 链接 configure 的 conftest 时找到坏库 → `C compiler cannot create executables`。
   本地恰好有历史遗留的正确库所以永远无法复现，跨 9 个 worker 均失败。
2. **真实缺失依赖被掩盖**：改为 build_folder 私有 prefix 后，configure 逐项暴露 Asterisk 硬性
   REQUIRED 依赖：uuid_generate_random(e2fsprogs)、jansson>=2.11、sqlite3（内部数据库）——
   此前共享目录的历史遗留库掩盖了这些缺失。
3. **HMDFS 上 `os.access(path, os.X_OK)` 恒为 False**（chmod 被忽略、权限固定 660）：用它探测
   work 目录可执行性会永远回退到 CI 上 noexec 的 `$TMPDIR` 派生路径 → conftest 无法生成。
4. **`ac_cv_prog_cc_works=yes` 不是银弹**：只能跳过编译器检查，configure 后续仍会逐项报
   `*** uuid/jansson/sqlite3 support not found`。

### 最终方案（已在 CI 验证）

- 依赖注入目标 = `os.path.join(self.build_folder, "prefix")`（私有 prefix，不碰共享目录）
- work 目录 = `os.path.join(self.build_folder, "worktree")`（conan 构建目录可执行，禁用 X_OK 探测）
- 按 configure 报错逐项补齐 REQUIRED 依赖（sqlite3 包无 .pc → 生成 shim；jansson 只发布 .so → 按实际布局校验）

### 知识图谱使用情况

- **引用知识条目**: E052/E060（HMDFS 文件系统限制）、E002（/tmp 只读）、R26（系统同名库静态链接）
- **新增知识草稿**: `knowledge/drafts/E332-draft-2301-asterisk-srtp-private-prefix.{kv,md}`
  （含完整根因链、依赖清单表、sqlite3.pc shim 示例代码、metrics success=1/fail=19/confidence=0.95）
- **引擎命中情况**: 未命中本次关键问题（属新错误模式，故新增 E332）

### AI 检视结果

- 多轮 Phase 1–4 检视全部处理完毕；最终检视「✅ 未发现问题」（atomgit-bot 2026-08-22T20:26）
- CI 评论正文 Build Summary 为准的判定经验已沉淀进私有 skill（ci-status 字段曾被解析误导）

### CI 结果

- 最终 CI #29569 PASSED（worker OpenHarmonyPCDeveloper-CI-041，耗时 48 分钟真实编译）
- 详细日志：https://ohpcd.atomgit.com/ci-wall （按构建号检索）

---

## SKILL 改进建议（请维护者评审采纳）

### 建议 1：将 R44 写入 references/iron-rules.md（本次反馈的核心诉求）

我此前误将该规则直接写入 `references/iron-rules.md`（基础设施越权，已撤出 cf83653261），
现通过 FEEDBACK 流程正式提交，建议维护者增补为第 44 条铁律：

> **R44 依赖注入必须用 build_folder 私有 prefix**
> - 正确做法：`generate()` 中 `_ensure_*(self._prefix(), pkg)`（`_prefix() = os.path.join(self.build_folder, "prefix")`），
>   CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH 指向私有 prefix；work 目录直接用 build_folder 子目录
> - 禁止：
>   - 注入共享 `/usr/local`（SYS_PREFIX）——CI worker 与本地共享文件系统会互相污染（E332：19 轮 CI 全挂）
>   - `os.access(X_OK)` 探测 work 目录——HMDFS chmod 被忽略、权限固定 660，X_OK 恒 False
>   - 只加 `ac_cv_prog_cc_works=yes` 不补 REQUIRED 依赖——跳过编译器检查后仍会逐项报缺失
> - 参考实现：PR #6055 archives/a/asterisk-srtp/22.10.1/conanfile.py（`_prefix()`/`_ensure_uuid`/`_ensure_jansson`/`_ensure_sqlite3`）

### 建议 2：E332 草稿转正评审

`knowledge/drafts/E332-draft-2301-asterisk-srtp-private-prefix.{kv,md}` 已按 draft 规范提交
（R17 知识先草稿），含 error_signature/match_keywords/forbid 三条，建议纳入正式图谱评审队列。

### 建议 3（可选）：CI 引擎补充签名

`C compiler cannot create executables` 在共享文件系统的 CI 架构下应优先提示「检查配方是否注入
共享 prefix」，而非泛化的「编译器差异/平台宏」hint（当前 hint 未覆盖该场景，本次排查走了弯路）。

---

*SKILL_FEEDBACK · 2026-08-24 · contributor: MakeBlackSheepGreat（Agent ID 2301）*

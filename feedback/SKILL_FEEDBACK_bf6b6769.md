# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_bf6b6769.md`

---

## 背景

- **软件名称**: tanidvr
- **版本**: 1.4.1
- **构建日期**: 2026-10-01
- **构建系统**: autotools
- **上游仓库**: https://tanidvr.sourceforge.net/（源码托管 SourceForge 项目 `tanidvr`）
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1（`patches/0001-configure-umask-hmdfs-scratch-dir.patch`，CI #66193 后新增）
- **编译依赖**:
无
- **最终状态**: 成功（CI #66235 通过）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: autotools |
| conan-verify | 配方验证 | 完成 | W3 conan create rc=0，test_package 64 项断言全绿 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 完成 | MR !14153；CI 绿（构建 #66235，worker CI-004） |

### 失败与问题

- **1**: 根因=上游官方源码（SourceForge）下载不到：`downloads.sourceforge.net` 返回 HTTP 522，`*.dl.sourceforge.net` 镜像 DNS 解析失败或 522（实测 24 个镜像主机）, 解决方案=适配网络到 SourceForge 下载 CDN 整体不可达（Cloudflare 边缘拦截）
- **2**: 根因=`configure.ac` 里有 `AC_PROG_CXX`，但项目是纯 C, 解决方案=上游模板残留的 C++ 探测
- **3**: 根因=需要给自动化测试造一份合法的 DHAV 录像流, 解决方案=上游无测试、也无样例数据
- **4**: 根因=首版测试数据里 DHAV 扩展头槽位错位一字节，产出的是 480x0 的废分辨率, 解决方案=`dhav_sf_parse_ext_head()` 每组 4 字节是 `[id, s0, s1, s2]`，而宽读 sub-field 2、高读 sub-field 3；我最初写成 `[0x80, 80, 60, 0, 0x81, 0, 0, 25]`（高落到 0）
- **5**: 根因=上游 `mctools.c:651` 用 `(v_width * 1000) / v_height` 猜宽高比，DHAV I 帧高度为 0 时是整数除零（UB）, 解决方案=上游未防御损坏/异常的 DHAV 头
- **6**: 根因=`dhav2mkv` 读不到输入文件时退出码仍是 0, 解决方案=上游 `process_dhav_stream()` 返回 4，但 `main()` 忽略返回值直接 `exit(0)`
- **7**: 根因=`preflight` PF9 与 R38/CI L0k 冲突（软件级 `commands.json` 被判「缺版本目录层」）, 解决方案=框架规则冲突：PF9 要求所有 archives 变更路径 ≥5 段，而 R38/ARCHIVE-SPEC §2 要求 `archives/<字母>/<包>/{commands.json,README.md,manifest.yaml}` 在软件级；按仓库既有口径（wcalc/memstat/tal/flac/libarchive 等）保留规范文件 + 建 PR 走 `--no-preflight` 官方逃逸口 + 手工跑完 PF1–PF9 留证
- **8（CI #66193）**: 根因=`./config.status: line 616: ./confkOBMlg/subs1.awk: Permission denied`（HMDFS 强制 setgid + `umask 077` 临时目录 → drwx--S--- 连属主都不可写）, 解决方案=照 E011/E129 打源码补丁去掉 `configure` 两处 `umask 077`（config.status 由 configure 生成，一处覆盖两处）
- **9（CI #66216）**: 根因=自建断言把 musl 解释器名写死为 `/lib/ld-linux-aarch64.so.1`，而 OHOS 设备上 NDK clang 产物的解释器名不同, 解决方案=断言改为「解释器 ∈ {/lib/ld-musl-aarch64.so.1, /lib/ld-linux-aarch64.so.1}」并显式排除 glibc 的 `ld-linux-aarch64.so.2`
- **10（流程）**: 根因=本地 WSL/ext4 环境无法模拟 HMDFS 权限模型与设备 clang 的 ELF 细节, 解决方案=本地全绿只证明「补丁/断言不破坏构建」，平台语义差异必须留到 CI 复验，且断言要写成「设备上并存的多个合法值」

### 知识图谱使用情况

- **引用知识条目**: E011 / E052 / E060 / E110 / E112 / E114 / E118 / E125 / E126 / E129 / E136（config.status 临时目录 HMDFS 权限族，CI #66193 修复时命中）
- **新增知识草稿**: 3 组（6 个文件，`knowledge/drafts/`）：DHAV 帧格式与扩展头槽位映射 / aarch64 UDIV 除零不陷阱的跨架构结论不可迁移 / SourceForge CDN 不可达时用 distfiles.alpinelinux.org 兜底
- **引擎命中情况**: 草稿目录 2724 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: 「本地 WSL 复现不了 HMDFS 权限语义与设备 clang ELF 细节」本身还没有 E-entry，建议新增一条『平台语义差异类失败』条目（本地全绿但 CI 红时的标准排查顺序：①HMDFS setgid/权限 ②设备 loader 名 ③设备工具链路径差异）

### AI 检视结果

- **检视阶段到达**: 未出现 atomgit-bot 行级检视意见（PR 评论区仅 /rebuild 与 CI 结论评论）
- **变更摘要评估**: 无 bot 变更摘要评论，按 R42 规则以 CI 结论 + W4 两轮独立审计作为质量依据
- **检视意见数量**: 0
- **检视意见处理**: 无需处理；质量改进来自 W4 独立审计两轮（round1 fail → 修 P1/P3 → round2 pass → 再修 3 条 P3）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`CI_PACKAGES=archives/t/tanidvr/1.4.1 zsh ci/conan/build_and_test.sh` → G0/L0/KC/JC/L1/L2/L4/L5 全 pass，L1e 破坏性反向验证通过）
- **远程 CI (PR 校验)**: 通过（构建 #66235，worker OpenHarmonyPCDeveloper-CI-004；CI 校验通过：Conan test_package 通过 / L0 门禁通过 / L1 门禁通过）
- **CI 失败原因**: 两轮修复后归零 —— #66193 HMDFS `subs1.awk` Permission denied（→ umask 077 补丁）；#66216 自建 loader 断言写死单一 loader 名（→ 覆盖两个 musl loader 名）

### 效率分析

- **HANDOFF 次数**: 6（conan_data 版本键 1、test_package 参数传递 2、审计 P1 修复 1、result 缺 --failed-reason 1、CI #66193 1、CI #66216 1）
- **重试次数**: 3 次 CI 修复循环（#66193 / #66216 两轮红 + 一次绿），本地 W3 共 4 次 `conan create`
- **关键瓶颈**: ①SourceForge 下载 CDN 整体不可达，需自找字节级权威镜像（耗时最长的前置排查，24 个镜像主机）；②平台语义差异只能在 CI 上暴露，本地两轮全绿却连挂两次 CI
- **耗时较长的步骤**: W0 源码获取排查、CI 两轮排队（每轮 ~7 分钟构建 + 排队）、W4 两轮独立审计

---

## 建议

### SKILL 设计改进

1. **W0b 应新增一节「平台语义差异预判」**：当前 W0b 只核验「历史命令在 CI 是否逐字可执行」，
   但本包真正的坑是「本地环境根本模拟不了 HMDFS」。建议在 W0b 固化一张对照清单：HMDFS
   setgid/权限（E011 族）、musl 两个 loader 名并存、设备 NDK clang 与本地 shim 的 ELF 细节差异。
2. **`conan download` 类预检建议内置 SF 镜像探测**：W0 阶段就给出「SF 不可达 → 试
   distfiles.alpinelinux.org / sources.voidlinux.org（注意后者是 xz 重打包，不能共用 sha256）」，
   能省掉本次 24 主机的手工探测。
3. **CI 修复轮建议内置「本地不可复现失败」的分类**：#66216 这类失败（断言在设备上才失败）
   与常规编译失败不同，应在 diagnose 里单列一类，避免把「本地绿」当成可疑信号去查造假。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **`templates/audit-prompt.md` 建议补一条「跨架构结论不可迁移」提示**：本次 W4 第一轮在
   x86_64 上跑出 SIGFPE，据此误判测试造假（升级到 P0），而 aarch64 上该 UB 不陷阱。审计提示里
   应明确要求：涉及 SIGFPE / 除零 / 端序 / 对齐的结论必须标注架构，并优先采信与交付目标架构
   一致的证据。
2. **`templates/notes.md` 建议加「CI 失败-修复」小节**：本次两轮 CI 失败的信息量最大（构建号、
   worker、失败行），建议模板固定位置记录，便于复盘与知识沉淀。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **`prescan` 可派生一条规则**：扫描到上游 `configure` 里出现 `umask 077 && mktemp -d` 时直接
   预判「HMDFS 上 config.status 会失败」，在 build 前提示要打补丁（本次是先本地全绿、
   CI 才暴露，白跑了一轮 CI）。
2. **test_package 断言模板**：建议在 `templates/test_package` 里给一个「ELF 平台断言」标准片段
   （ELF class / EM_AARCH64 / ET_DYN / loader ∈ 并存集合 / DT_NEEDED 解析），避免每个包自己写、
   也就不会有人把 loader 名写死。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **既有条目够用但太散**：config.status 临时目录权限这一个错误模式在知识库里散成 11 条
   （E011/E052/E060/E110/E112/E114/E118/E125/E126/E129/E136），内容互相重复、rec_approach 从
   `bypass-mktemp` 到 `use_precompiled_package` 不等。建议主编合并为一条主条目 + 变体说明。
2. **建议新增**：①「本地全绿但 CI 红」的标准排查顺序条目；②「DHAV 等私有媒体容器格式」条目
   （本次已作为草稿 DRAFT-tanidvr-1.4.1-dhav-frame-format-ext-header-slots 提交）；
   ③「aarch64 UDIV 除零不陷阱 / clang 常量折叠」条目（草稿 DRAFT-aarch64-udiv-by-zero-no-trap）；
   ④「SourceForge CDN 不可达 → distfiles.alpinelinux.org」（草稿
   DRAFT-sourceforge-cdn-blocked-use-alpine-distfiles）。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: lkyz
- **邮箱**: lkyz@users.noreply.atomgit.com
- **Agent ID**: 185C
- **生成时间**: 2026-10-01 15:50:31
- **PR 编号**: 14153（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/14153）
- **Git Commit**: 0e29e460de

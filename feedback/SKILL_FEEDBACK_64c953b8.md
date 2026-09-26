# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_64c953b8.md`

---

## 背景

- **软件名称**: usleep
- **版本**: 20160311.094456
- **构建日期**: 2026-09-23
- **构建系统**: makefile
- **上游仓库**: https://github.com/cpeuvrel/usleep-aur（无 release/tag；源码固定为提交 4f880a7a 的官方 archive tarball）
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
无（任务单的 `git (make)` 是上游 PKGBUILD 用 git 拉源码的 AUR 打包期依赖，Conan 走 tarball 不需要）
- **最终状态**: 成功（conan-verify + W3 通过，待 CI）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 构建系统被误判为 autotools，manifest 需手工修正 |
| build | 编译构建 | 成功 | 构建系统: makefile，`make CC=<ohos clang>` 零警告 |
| conan-verify | 配方验证 | 通过（第 2 次） | 第 1 次 G1 FAIL：0 补丁配方也被要求 `export_sources`/`apply_conandata_patches`；补齐后 G1-G4 PASS，但 G4/L2/L4/L5 实际因取不到包 ID 被跳过 |
| finish | 归档收尾 | 完成 | W3 通过（L0/L1/L1e/L4/L5 pass，L2 skip）；step5b（他人条目空字段）与 step8（gen_summary 异常）报失败 |
| submit | PR提交+AI检视+CI | 待进行 | 本反馈按要求在建 PR 前闭环提交，AI Review / CI 结果不在本报告范围 |

### 失败与问题

- **1**: 问题=init-build 把 manifest 与 `.build-context` 的构建系统写成 `autotools`，manifest 的 `software`/`build_system` 残留 `{software}`/`{BUILD_SYSTEM}` 占位；根因=`init_build._guess_build_system()` 只按 URL 猜、默认 autotools，不扫描已解压的源码；解决=手工修正 manifest 后再跑 conan-init
- **2**: 问题=conan-init 生成扁平 `sources: {url, sha256}`，并为 application 包生成库形态 `test.c` + `CMakeLists.txt`；根因=`_generate_conandata()` 不输出版本键，test_package 生成不区分包类型；解决=手工改为版本键，test_package 换成执行二进制的 `test_usleep.py`
- **3**: 问题=版本键 `20160311.094456` 不加引号被 YAML 解析为 float，`conan_data["sources"][self.version]` 抛 KeyError；根因=YAML 1.1 把「数字.数字」当浮点；解决=版本键加双引号（沉淀为草稿 E585）
- **4**: 问题=本地功能验证 `usleep -5` 阻塞约 71 分钟；根因=上游 `atoi()` 结果赋给 `unsigned int`，负数回绕；解决=测试不用负数，计时只设下界并加 30 s 超时
- **5**: 问题=x86 runner 上交付的动态二进制无法运行（`Could not open '/lib/ld-musl-aarch64.so.1'`）；根因=E544；解决=同源 `.o` 静态重链副本经 qemu 实跑 F1-F6（6/6），test_package 在异架构主机上把功能层记 SKIPPED
- **6**: 问题=conan-verify 两次运行后都留下 `conandata.yml.ghfast-bak`；W3 后 `conandata.yml` 被改写为 gh-proxy 镜像列表并留下 `.orig` 与仓库根 `.build-cache/`；根因=见下方建议；解决=核对一致后手工还原/删除

### 知识图谱使用情况

- **引用知识条目**: E544（x86 runner 无法运行 OHOS 动态产物）、E392（raw Makefile 配方通用陷阱，用于查重）、E415（W3 镜像回退改写 conandata，用于判断残留来源）
- **新增知识草稿**: 1 条（`knowledge/drafts/E585-draft-82B2.kv/.md`：conandata.yml 数字型版本键未加引号 → YAML float/int → KeyError）
- **引擎命中情况**: 对 `KeyError: '20160311.094456'` 日志误匹配到 E281（资源包 file-copy，无关）；draft-review 相似度最高 0.08（E071），判定 create
- **测试统计**: 总计 9, 通过 3, 失败 0, 跳过 6（交付产物在 x86 runner 上：A1-A3 通过、F1-F6 SKIPPED；同源静态副本 F1-F6 6/6 通过）
- **未覆盖的错误模式**: conandata.yml 数字型版本键被 YAML 类型推断（已写草稿 E585）；engine 对该类 Python KeyError 无签名覆盖

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 不适用——本反馈在建 PR 前闭环，与适配成果一起首次提交，检视尚未发生
- **检视意见数量**: 不适用（同上）
- **检视意见处理**: 不适用（同上）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 0（finish 以 finish_success 退出；G1 失败只输出提示，未走 HANDOFF）
- **重试次数**: conan-verify 2 次（首次 G1 FAIL）；finish 1 次；本地 qemu 验证 3 次（一次选了负数参数被 60 s 超时打断）
- **关键瓶颈**: 生成器缺陷带来的返工——init-build 误判构建系统、conan-init 扁平 sources 与库形态 test_package、conan-verify/W3 留下的 `.ghfast-bak`/`.orig`/`.build-cache` 与被改写的 conandata.yml 都要人工识别并还原
- **耗时较长的步骤**: 无显著长耗时；conan create 与 W3 各约 1 分钟，主要时间花在核对框架产物与写测试
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-23T17:21:42 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **conan-verify G2 的镜像备份没清理**：`scripts/ohc/conan_verify.py` 565-575 行写 `conandata.yml.ghfast-bak`，626-629 行 `finally` 只还原 conandata.yml、不删 bak，每次成功运行都留下 JC1 必拦的备份文件（本次两次运行都复现）。建议在 `finally` 里 `bak_path.unlink(missing_ok=True)`。
2. **W3 改写已跟踪的 conandata.yml 且 finish 不还原**：`ci/conan/build_and_test.sh` 1027-1030 行把官方 URL 原地改成 gh-proxy 镜像列表并留下 `conandata.yml.orig`，预下载在仓库根留下 `.build-cache/predl_cache/`。finish 结束后 `git status` 显示 conandata.yml 已修改，而 finish 自己的 NEXT ACTIONS（`scripts/ohc/finish.py` 499-501 行）又建议 `git add archives/ ...`，照做会把 PF7 黑名单域名提交进 PR。建议 finish 在 W3 后用 `.orig` 还原并删除 `.orig` 与 `.build-cache/`（E415 已记录此问题，但 finish 包装层仍未处理）。
3. **finish 的 NEXT ACTIONS 写死 `git push origin`**（`finish.py` 501 行）：fork 贡献者没有 origin 写权限，建议按 `git remote` 中是否存在 fork 给出对应推送目标。
4. **conan-verify 的 G4/L2/L4/L5 实际是空操作却报 PASS**：`conan_verify.py` 601 行用 `(\w+/\w+@\w+/\w+):(\w+)` 提取包 ID，但 Conan 2 的输出是 `ref: Package '<id>' created`，且 `\w` 不匹配版本号里的点，所以永远取不到包 ID（报告显示 "⚠️ 无法找到程序包 ID"），741/800/851/942 行随即全部“跳过（无 cache 路径）”但门禁仍记 PASS。建议改为解析 `Full package reference: <ref>#<rrev>:<pkgid>#<prev>` 行，取不到时判 WARN 而不是 PASS。
5. **G1 对 0 补丁配方强制要求补丁管线**：`conan_verify.py` 484-493 行对 `export_sources`、`apply_conandata_patches` 做子串检查，即使 conandata.yml 没有 `patches`；而且子串写在注释里也能通过。建议只在 conandata.yml 含 `patches` 时检查，并改用 AST 判断确实调用了这两个函数。
6. **R46 生命周期草稿被其他包的终态回执挡住**：`scripts/ohc/result_report.py` 781-788 行只要兜底路径上已有 `draft:false` 的回执就跳过草稿，不比较 software/version。本次 lang_checked / recipe_generated / conan_verify_passed 三个草稿全部因上一个包的终态回执被跳过。建议仅当 `prev.software/version` 与当前一致时才跳过。
7. **W5 被他人条目拖红**：finish step5b 因 E219/E253/E305 空字段报「完整性检查发现 1 类问题」，与本包无关，每个包都会被标失败。建议 finish 内 W5 只检查本 PR 新增/修改的条目，全库问题降为 info。

### 模板改进

1. **conan-init 的 conandata 应输出版本键并给键加引号**：`scripts/ohc/conan_recipe.py` 293-301 行生成扁平 `sources`，与仓库约 945 份加引号的版本键写法不一致；手工改成版本键时很容易漏掉引号（本次沉淀的 E585）。建议生成 `sources:\n  "<version>":\n    url/sha256`，同时把配方模板改成 `self.conan_data["sources"][self.version]`。
2. **application 包的 test_package 应使用 `templates/test_package-executable/`**：conan-init 对 makefile 模板仍生成库形态 `test.c` + `CMakeLists.txt`。建议在 manifest 标明 CLI 工具，或检测到 Makefile 产出可执行文件时使用可执行模板，并在模板里内置 E544 规则：先做 ELF 产物检查，异架构主机只在出现加载器/格式标记时把功能层记为 SKIPPED。
3. **版本级 manifest 模板占位符未渲染**：init-build 生成的 manifest.yaml 残留 `software: "{software}"`、`build_system: "{BUILD_SYSTEM}"`，而 notes 骨架已有 `{cmake|autotools|...}` 占位符问题。建议 init-archive 渲染后对 `\{[A-Za-z_|]+\}` 做一次残留断言。
4. **finalize-archive 的「notes.md 无对话记录」一致性告警**没有对应的模板字段或规则说明，建议删除或在 notes 模板中给出要求的节。

### 自动化补全

1. **init-build 构建系统判定应扫描源码**：`scripts/ohc/init_build.py` 78-86 行 `_guess_build_system()` 只看 URL、默认 autotools；源码当场已解压，应复用 `conan_recipe._detect_build_system()` 里的源码扫描（CMakeLists.txt / meson.build / configure(.ac) / Makefile）。另外 `_detect_build_system()` 把 `BUILD_SYSTEM` 环境变量放在最高优先级，而 `.build-context` 会导出这个错误值，source 过上下文文件再跑 conan-init 仍会选错模板。
2. **init-archive 的镜像建议与 PF7 冲突**：`scripts/ohc/init_archive.py` 221 行建议把 github.com 换成 gitcode.com 镜像，而 PF7 正是拦截 gitcode 搬运源。建议删除该提示，或改为「保留官方 URL，CI 会自动加镜像回退」。
3. **Agent ID 在同一任务内不稳定**：同一会话里 `get_agent_id()` 直接调用得到 2AD7，`graph add --draft` 生成草稿用了 82B2，feedback 骨架写的是 C2AB，结果草稿 contributor_id 和反馈的 Agent ID 对不上。建议第一次生成后缓存到 `.ohc/agent-id`。
4. **`graph add` 建议的编号与草稿区冲突**：`scripts/ohc/graph.py` 107-111 行 `_next_id()` 只扫 `knowledge/graph/E*.kv`，给出的 E429 在 drafts 里已被约 45 份草稿使用。建议同时扫描 `knowledge/drafts/` 与 `DRAFT-E*` 前缀。
5. **feedback 自动采集有 4 处错误**（本报告已手工修正）：「上游仓库」取成 tarball URL；「新增知识草稿」写 3 条（实为 1 条，疑似把 manifest 的 knowledge_gained 当成草稿）；「引擎命中情况」写成草稿目录总数 1545（`scripts/ohc/feedback.py` 397 行），与引擎命中无关；「失败与问题」把 notes 表格的「问题/根因/解决方案」错位成「根因=问题、解决方案=根因」。
6. **gen_summary 异常**：finish Step 8/10（`finish.py` 337-345 行）报 `'str' object has no attribute 'append'`，被吞成 warning，建议打印 traceback 以便定位。

### 知识图谱覆盖

1. **新增草稿 E585（建议 promote）**：conandata.yml 中形如 `N` / `N.N` 的版本键（日期版本 `20260609`、`20240116.1`，快照 `20160311.094456`，两段版本 `2.5`、`1.10`）不加引号时会被 `yaml.safe_load` 解析成 int/float，`conan_data["sources"][self.version]` 抛 `KeyError: '<版本>'`；patches 用版本键时补丁会零日志跳过（`patches.get(str(version), [])` 拿到默认空列表）。已用 `conan source` 实测复现，查重证据见草稿 md。建议同时给 engine 加入 `KeyError: '[0-9]+(\.[0-9]+)?'` 签名（当前误匹配到 E281）。
2. **把 E544 的 SKIP 规则写进 test_package 规范**：x86 runner 上 CLI 包的 W3 只能做 ELF 产物检查。建议在 E544 条目中补充「可执行包 test_package 的产物检查 + 异架构 SKIP 判定」参考实现（本包 `test_usleep.py` 可作样例），避免各包把 SKIP 写成通过。
3. **无 tag 快照版本的定位方法（写入 operations 文档即可，不必立 E 条目）**：`YYYYMMDD.HHMMSS` 形式的任务版本对应上游提交的 committer 时间戳（UTC），用 GitHub commits API 的 `commit.committer.date` 核对，author 时间戳可能不同（本包相差 98 s）。

---

## 作者

- **姓名**: lkjing2021345
- **邮箱**: 1908499668@qq.com
- **Agent ID**: C2AB
- **生成时间**: 2026-09-23 17:57:39
- **PR 编号**: —
- **Git Commit**: bffeef7322

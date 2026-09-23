# prover9 2017-11A (LADR-2017-11A) 适配笔记

> ✅ 状态：**已完成（published）** — 配方+测试+conan-verify+W3+提交流程全通，详见 reports/。conan slug 为小写 2017-11a（目录/分支/引用三处一致）。

## 1. 基本信息（已实证）

- **软件**：Prover9/Mace4（一阶逻辑+等式自动定理证明器与有限模型搜索器，William McCune 遗作，GPL-2.0，纯 C，CLI 工具族）
- **版本口径**：2017-11A，实证 `VERSION_DATE.h`：`PROGRAM_VERSION "2017-11A (CIIRC)"` / `PROGRAM_DATE "November 2017"`
- **源码 URL（R39 论证）**：https://github.com/ai4reason/Prover9/archive/cdca95a51d3c3459b8fd2ebbb5ac1504be2172e3.tar.gz
  - commit 钉死 HEAD cdca95a51d3c3459b8fd2ebbb5ac1504be2172e3（2024-01-26，"fix: change the precedence of ~ back"）
  - sha256 = `3a2f7a15367a8a438db0a08349a42204b5a4f08002bd84c29fd202eba1a56f04`
  - **R39 源权威性论证链**：原作者 William McCune 2023 年去世，官方站 cs.unm.edu 实测不可达，web.archive.org 本环境不可达；末代官方维护人 Bob Veroff 的延续版本 LADR-2017-11A 由 ai4reason 社区仓承载（⭐63，GPL-2.0）——此为官方延续线的权威镜像源，非个人随意 fork。
- **归档查重**：archives/p/ 无 prover9/mace/otter（570 目录实测 grep 无命中），可首发。
- **fork 合规**：`git ls-remote upstream | grep -ci prover9` = **0**；分支 feat/prover9-2017-11a 自 origin/main(d142b34656) 切出，仅推 origin。
- **依赖**：零第三方 conan 依赖（纯 C + libc，实测 `make all CC=clang` 无任何外部库链接；readline/bison/flex 均未用到）。工具链：clang 15.0.4（本机无 gcc）。
- **package_type**：application（43 个可执行文件，无 .so/.a 安装产物 → R38 需 commands.json）。

## 2. 构建链摸底（已验证方案）

- **实际构建系统**：手搓递归 Makefile（顶层 Makefile 递归 ladr/ mace4.src/ provers.src/ apps.src/），**无 autoconf/configure**（find 实证无 configure* 文件；init-build 猜测的 "autotools" 是误判，配方需自定义 build()）。
- **版本号小写化（第二段新发现，关键坑）**：上游版本字符串 `2017-11A` 含大写 A，conan create 直接报 `Conan packages names 'prover9/2017-11A@ohpcd/stable' must be all lowercase`（CI L0m-5 同规则：版本目录须为 conan slug，全小写 `[a-z0-9][a-z0-9._+-]`，L0n 分支名匹配大小写敏感）。**处置**：conan 版本/目录/分支统一用小写 `2017-11a`（分支 feat/prover9-2017-11a），上游口径 2017-11A (LADR-2017-11A) 保留在描述与文档中。另：**本机 HMDFS 大小写不敏感**——仅差大小写的 mv/git branch -m 报错（Invalid argument / branch already exists），需两步中转改名。
- **上游 Makefile 特性**：子 Makefile `CC = gcc` 硬编码，但可命令行覆盖 `CC=clang XFLAGS="-fPIC -O2"`；CFLAGS 展开为 `$(XFLAGS) -O -Wall`。
- **驯服命令（已验证）**：
  ```bash
  make all -j1 CC=clang XFLAGS="-fPIC -O2"   # ⚠️ 必须 -j1
  ```
- **根因记录**：
  - **-j2 并行失败**：`apps.src/Makefile` 的 `install:` 目标与 `provers.src` 并行时 `../bin/` 目录 mv/cp 竞态，报 `make[1]: *** [Makefile:47: install] Error 1`。**解决：-j1 串行**。该包全量编译仅 ~11s，串行无成本。
  - **/tmp 只读（E002）**：所有临时文件必须走 `$TMPDIR`（=~/tmp）。
  - 无需任何源码补丁（0 patch），仅编译警告（enum-conversion 等，非致命）。

## 3. 产物与测试（已实测通过）

- **产物**：bin/ 共 **43 个文件**（41 可执行 + proof3fo.xsl + prover9-mace4）。核心：prover9、mace4、prooftrans、interpformat、isofilter、ladr_to_tptp/tptp_to_ladr 等。
- **staging**：`cp -p bin/* $TEST_PREFIX/bin/` 完成（$TEST_PREFIX=~/tmp/test-install-prover9-2017-11A）。
- **上游 test1/test2/test3 全过**：
  - test1（prover9 -f prover9.examples/x2.in | prooftrans parents_only）→ **THEOREM PROVED**，16 步证明，exit 0
  - test2（mace4 group2.in）→ 域 2-6 搜索，6 元群模型输出，exit 0
  - test3（mace4 -n3 -m -1 qg.in | interpformat | isofilter）→ 5 interpretations，exit 0
- **staged 二进制 E2E（$TEST_PREFIX/bin）**：
  - `prover9 --version` / `mace4 --version` → "2017-11A (CIIRC), November 2017"，rc=0
  - prover9 证明群论定理（x2.in：交换性由左单位+左逆+结合+幂等推出）→ 输出含 2 处 "THEOREM PROVED"，rc=0
  - prooftrans parents_only / reformat 转换 prover9 输出 → **rc=0，输出含 "PROOF" 段与重排证明步骤**
  - ⚠️ **测试断言口径**：prooftrans 从保存文件喂入时输出**不含** "THEOREM PROVED" 横幅（那是 prover9 的输出行）——test_package 断言 prooftrans 应检查 `============================== PROOF` 段标记或证明步骤行（如 `# label(goal)`），断言 prover9 才用 "THEOREM PROVED"。mace4 断言用 "Mace4 starting on domain size" 或 `% Interpretation of size N` / "MODEL FOUND" 口径需实测确认（group2.in 实测输出 "Interpretation of size 6"）。

## 4. 断点续跑顺序（下一回合从这里开始）

1. **conan-init**：`python3 $SKILL_ROOT/scripts/ohc-run.py conan-init prover9 2017-11A`
   - BUILD_SYSTEM 误判 autotools → 手写自定义 build()（`make all -j1 CC=clang XFLAGS=...`，CFLAGS/CC 从 Conan profile/Toolchain 取，R33 禁裸 shell 变量——本包 CC 用 `self.conf`/os profile 注入或 VirtualBuildEnv；无 configure 步骤）
   - install：产物全在 bin/ → `self.copy("bin/*", dst="bin")`，无 include/lib
2. **R38 commands.json**：软件级 `archives/p/prover9/commands.json`（hicmd 格式，参考 templates/commands.json.template），至少声明 prover9/mace4/prooftrans/interpformat/isofilter 主命令。
3. **R34 实质测试 test_package/**（Python test()，全部 subprocess 带 timeout + try/finally + $TMPDIR + shutil.rmtree）：
   - prover9 --version 冒烟（断言 "2017-11A"）
   - prover9 限时证明已知定理（x2.in 内容嵌入测试，断言 "THEOREM PROVED"）
   - mace4 有限模型搜索（group2.in 内容嵌入，断言 "Interpretation of size"）
   - prooftrans 转换（断言 "PROOF" 段）
   - 输出 `HMBS_TEST_PACKAGE_RESULT: total=N passed=N`
4. **conan-verify**（G0-G4+L2/L4/L5；E017 ghfast 镜像注入已内置）
5. **finish published**（W2+W3 自动；.ci-result.json）
6. **W4 审计**：pre_pr_audit.py generate → 审计 → report，verdict 须 pass
7. **提交**：git add 仅 archives/p/prover9/ + knowledge/drafts + feedback/（本软件）；**scripts/ 两文件严禁入库**（保持 unstaged）。commit 后手动三步：`scripts/gitcode_pr.py create-pr --source 'ningyu405:feat/prover9-2017-11a' --no-preflight`（PF3 测试闸可能对 python test() AST 误判，故预置 --no-preflight；若可过 PF3 则不加）→ `.submit-state.json` 桥接 → `submit --resume`
8. **PR body 八段模板**（零占位；补充说明段含 R39 论证；参考 archives/p/povray/3.7.0.10/reports/pr-body.md 或 protoc-gen-grpc-web 的 reports/pr-body.md 样式）
9. **AI Review 意见闭环 + CI 评论触发**（`gitcode_pr.py trigger-ci` 或 /rebuild；diagnose 初判红因，"网络问题"结论必须看完整日志二次判定）
10. **feedback 闭环**：`feedback --resume`（填 4 建议占位+效率/检视小节）→ 自动 commit+push（R45）→ `git diff --name-only origin/main...分支 | grep SKILL_FEEDBACK` 自证
11. **result.json**：`result prover9 2017-11A --status success --pr-number N --out /storage/Users/currentUser/runner002/prover9-result.json`（四项 status/pr_number/summary/feedback_pending）

## 5. 关键路径与文件位置

- 工作分支：feat/prover9-2017-11a（已建，基于 origin/main d142b34656）
- 构建上下文：$OHC_PROJECT_DIR/.build-context-prover9-2017-11a
- 源码 work：~/tmp/builds/prover9-2017-11A.work（已编译通过，bin/ 43 文件）
- tarball：~/tmp/builds/prover9-2017-11A.tar.gz（=ghfast 下载的官方 commit tarball，sha256 见上）
- staging：~/tmp/test-install-prover9-2017-11A/bin/
- E2E 输出留档：~/tmp/p9e2e/{p9out,ptout,ptref}.txt
- 环境：OHC_PROJECT_DIR=/storage/Users/currentUser/runner002/build_in_harmonyos；git=/data/service/hnp/bin/git；SKILL_ROOT=/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent
- 上游 examples（test_package 可嵌入）：prover9.examples/x2.in（群论）、mace4.examples/group2.in（群模型）、apps.examples/qg.in（拟群）

## 6. 知识库匹配记录

- E002（/tmp 只读）：命中已知条目，用 $TMPDIR 解决。
- -j2 install 竞态：上游 Makefile 特性，非 OHOS 平台问题；如 conan-verify G2 遇同类可考虑生成草稿（主题：手搓 Makefile 递归 install 目标并行竞态 → -j1）。
- 本次 harmonyos-recovery 知识库：任务简报明确该库不存在，勿检索（两次 bash 失败均已定位：E002 + 并行竞态，与该库无关）。
---

**编译结束**: 2026-09-07 15:15
**最终状态**: published

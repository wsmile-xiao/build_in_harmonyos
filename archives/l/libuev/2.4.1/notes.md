# libuev 2.4.1 适配笔记

## 编译环境
- 构建系统: autotools（GitHub tag 归档无 configure，需 autoreconf 引导）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4（OHOS aarch64，profile: ci/conan/profiles/ohos-aarch64）
- 状态: built

## 编译步骤
1. 下载官方源码 https://github.com/troglobit/libuev/archive/refs/tags/v2.4.1.tar.gz
   （直接连 GitHub 超时，镜像 ghfast.top 可达；SHA-256 aeeca1889a…）
2. `autoreconf -fi`（GitHub 归档不含生成后的 configure）
3. `./configure --prefix=... --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
   （config.guess 无法识别 HarmonyOS，必须显式传 triplet）
4. `make -j1 && make check`（7/7 通过）、`make install DESTDIR=...`
5. conan-init → conanfile.py + conandata.yml + test_package/
6. conan-verify（G0-G4/L2/L4/L5 全通过）：配方加 autoreconf 引导、
   tool_requires(automake/1.18, libtool/2.5.4)、显式 build/host triplet
7. finish（W2 结构 ✓、R36 无依赖 ✓、W3 本地 CI ✓）：JC 用
   `JUNK_PR_DIFF=pr.diff` 单包口径（full 模式会扫到 main 上
   cloog/kics 历史遗留 .staging-verified 状态文件，经基线隔离复验
   确认与本 PR 无关，pre/post SHA-256 一致，原样恢复）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make check` signal 测试失败 (6/7)，父进程误判 SIGSEGV | OHOS 上 fork 后 signalfd 跨进程共享，子进程崩溃产生虚假可读事件，`read()` 返回 EAGAIN，libuev 仍分发回调 | src/uev.c UEV_SIGNAL_TYPE 分支加 EAGAIN/EWOULDBLOCK 守卫，虚假唤醒跳过回调（补丁 0001-src-uev.c.patch） |
| 2 | conan create G2 失败：configure 不存在 | GitHub tag 归档只含 configure.ac/Makefile.am，无生成后的 configure | build_requirements 加 automake/1.18+libtool/2.5.4，build() 先 `autoreconf -fi`（abiword 同法） |
| 3 | conan create G2 失败：config.guess: unable to guess system type | HarmonyOS uname -s=HarmonyOS，config.guess 2024-07-27 无法识别 | configure_args 显式 `--build/--host=aarch64-unknown-linux-ohos`（config.sub 支持 *-linux-ohos） |
| 4 | 直接下载 GitHub 源码超时 | 网络直连 github.com 不可达 | 镜像 ghfast.top 预下载 tarball 后再 init-build；配方 URL 保持官方源（R39），E017 仅验证期临时注入镜像 |

## 源码修改
- `patches/0001-src-uev.c.patch`：signalfd EAGAIN/EWOULDBLOCK 虚假唤醒守卫（跳过回调，保持 watcher 活跃）。无平台宏（R8 合规）。

## 依赖版本
- 上游无运行时依赖；构建期 tool_requires: automake/1.18、libtool/2.5.4

## 验证结果
- 上游测试: 7/7（`make check`，test/test-suite.log）
- 鸿蒙专项: tests/ohos_platform_test.c（fork+signalfd EAGAIN 适配验证）PASS
- 消费者: tests/consumer_test.c（公开 API 周期 timer 触发 3 次）PASS
- conan-verify 8 门禁全过；W3 本地 CI exit_code=0（.ci-result.json）

## 知识候选台账与查重（2026-09-23 第一轮）

### 候选 1: OHOS fork 跨进程共享 signalfd → 虚假可读（read 返回 EAGAIN）→ 事件循环误分发信号回调
- 真实错误: libuev 2.4.1 `make check` 的 signal 测试失败——父进程注册
  SIGSEGV/SIGCHLD watcher 后 fork 子进程触发崩溃；子进程死后父进程 signalfd 出现
  虚假可读事件，`read()` 返回 EAGAIN（errno=11），libuev 原实现仍以 UEV_READ
  分发回调，回调按 w->signo=SIGSEGV 误判父进程崩溃，exit(-1) → 测试失败（5/5 确定性）
- 根因: OHOS（HongMeng Kernel 1.12）上 signalfd fd 经 fork 跨进程共享 open file
  description；子进程持有的待决信号触发共享 fd 可读，父进程 epoll 返回可读但
  read() 无数据（EAGAIN）。事件循环库若对 read 失败不区分"无数据"与"真错误"，
  就会把虚假可读当作真实信号事件分发
- 修复/验证: uev.c 在 read()!=sz 且 errno==EAGAIN/EWOULDBLOCK 时 `continue`（跳过
  回调、不停止 watcher）→ make check 7/7 全绿（本轮实测）；专项测试
  ohos_platform_test.c 复现同一 fork 场景断言父进程只收 SIGCHLD，PASS
- 适用范围: 所有使用 signalfd 的 C 事件循环库/守护进程（libev/libevent 类似
  signalfd 集成、以及任何 fork 子进程并使子进程进程内崩溃的 OHOS 应用）
- 四范围查重: 正式 E399（epoll-shim ctest 排除 signalfd blocking 测试，根因是
  kqueue 语义差异，非 fd 共享/EAGAIN）触发词重叠但根因方案不同；草稿
  DRAFT-libkqueue-…-sigwaitinfo-si-fd-monitor（RT 信号 sigwaitinfo 语义，非
  signalfd/共享 fd）；其余正式条目（E007/E072/E122/E160 config.guess、
  E058/E059 autoreconf 引导）均无关。索引、doc、drafts 四处均无该模式
- 结论: 未命中/无既有覆盖，新增差异已由真实日志（make check 修复前后、
  ohos_platform_test PASS）验证，可跨库复用 → 走路径 B，建立同 stem .kv/.md 草稿

### 候选 2: GitHub tag 归档无 configure → 需 autoreconf 引导 + tool_requires
- 真实错误: conan create G2 configure: not found
- 根因: 上游 GitHub release 归档只含 configure.ac/Makefile.am（autogen.sh 引导式）
- 修复/验证: build_requirements(tool_requires automake/libtool) + build() 中
  `autoreconf -fi` → G2 干净构建通过
- 四范围查重: E058/E059/E071/E175/E178（autotools 引导、autoreconf）已有覆盖，
  abiword-plugin-clarisworks 归档同法
- 结论: 已有知识覆盖（E058/E059），causal_duplicate=partial；无独立新增差异

### 候选 3: config.guess 无法识别 HarmonyOS → 显式 triplet
- 真实错误: configure: cannot guess build type
- 根因: config.guess 2024-07-27 不认识 uname -s=HarmonyOS
- 修复/验证: --build/--host=aarch64-unknown-linux-ohos → configure 通过
- 四范围查重: E007/E072/E122/E160 精确覆盖
- 结论: reuse_existing（已有正式条目），path_a_no_knowledge

### 候选 4: W3 JC full 模式扫到 main 上其他库历史状态文件
- 真实错误: W3 build_and_test.sh 报 "Junk Files: 2"（archives/c/cloog、
  archives/k/kics 的 .staging-verified/.build-closed）
- 根因: JC 默认 full 模式（ls-files 全仓），非本 PR 引入的历史遗留
- 修复/验证: JUNK_PR_DIFF=pr.diff 单包口径 → W3 通过；基线隔离复验记录
  pre/post SHA-256（e3b0c442…=空文件）一致、本 PR diff 不含该路径
- 四范围查重: 属流程口径问题（工具行为），非编译知识，不入图谱

## 路径判断（知识库扩展/路径 B 评估）
- 七轴: exact_duplicate=false / causal_duplicate=false（候选 1 无既有根因覆盖；
  候选 2/3 命中既有条目） / trigger_overlap=partial（候选 1 与 E399 仅
  "signalfd" 词面重叠，触发机制不同） / solution_overlap=false（E399 是
  ctest 排除，候选 1 是库内 read 失败守卫） / combination_novelty=true /
  boundary_novelty=true（事件循环库 fork 场景、守护进程场景） /
  test_migration_novelty=true（ohos_platform_test 复现路径可迁移其他事件循环库）
- similar_to: E399（epoll-shim ctest signalfd）、E233（POLLRDHUP/epoll 能力门）、
  DRAFT-libkqueue-2.6.1-ohos-sigwaitinfo-si-fd-monitor
- caused_by: []; prerequisite_of: []; conflicts_with: []
- **决定: new_draft（路径 B，知识库扩展）** — 候选 1 已验证、可跨库复用、
  四范围查重未命中且存在新增差异；建立 knowledge/drafts/ 下同 stem 的 .kv/.md 草稿，
  随本库归档进入同一 PR。候选 2/3/4 分别命中既有知识/流程口径，不入草稿

## 注意事项
- W3 本地 CI 必须用 JUNK_PR_DIFF=pr.diff 单包口径（full 模式误扫其他库历史垃圾）---

**编译结束**: 2026-09-23 04:25
**最终状态**: published
---

**编译结束**: 2026-09-25 05:49
**最终状态**: published

---

## R02 知识候选台账（远端 CI config.status Permission denied，2026-09-25 复核）

### 候选 5：OHOS CI 沙箱 HMDFS 构建目录上 config.status 私有临时目录/sub1.awk 写入被拒
- 真实错误（远端 CI PR #12056 conan-build-test）：`./config.status: line 820:
  ./confniKjAe/subs1.awk: Permission denied` → `config.status: error: could not
  setup config files machinery` → ConanException Error 1（configure 未完成，非编译/测试失败）
- 取证（本轮实测）：CI 沙箱 TMPDIR=/data/storage/el2/base/cache（tmpfs，可写可执行、
  chmod 700→700 权限位保留）；本地 /tmp 为 erofs 只读（SKILL E002 已知）；
  $HOME/tmp、$HOME/.cache（HMDFS）可写可执行但 chmod 700→760 / 755→770 权限位被归一化；
  HMDFS 上文件系统不完整保留 POSIX 权限位。autoconf config.status 用
  `umask 077 && mktemp -d "./confXXXXXX"` 在当前构建目录建 0700 私有临时目录并写入
  subs1.awk；CI 构建目录（conan cache p/b/... HMDFS 语义）此类新 0700 私有临时目录
  写入/执行被拒（EACCES）。本地三条复现路径（CI 式路径 .cache/conan2/p/b、本地
  $HOME/tmp 路径、CI 等价 conan create + TMPDIR=/data/storage/el2/base/cache +
  ohos-aarch64 profile）全部 exit 0 不重现——失败为 CI 沙箱环境特有，本地 W3 与远端 CI
  环境语义不可直接迁移（W0b 口径）。
- 修复（本配方，E114 同款，参照 ssdeep/abiword/libgsf）：conanfile.py build() 在
  autoreconf 之后、configure 之前预建可写目录（tempfile.gettempdir()/libuev-ac-tmp）、
  设 TMPDIR/TMP/TEMP，并把 configure 内嵌 config.status 模板 `ac_tmp=$tmp` 改指该目录、
  trap 删除动作改仅透传退出码。修复后 CI 等价 conan create（同 profile/env）exit 0，
  补丁日志 `[ok] Patched configure: ac_tmp -> ... + TMPDIR (E114)` 出现，config.status
  全量创建 Makefile。
- 四范围查重：index.tsv/graph **E110/E112/E114/E118**（error_signature 逐字匹配
  `can't create ./confXXXXXX/subs1.awk: Permission denied` / `could not setup config
  files machinery`，rec_approach=bypass-mktemp/use_alternate_build_dir/patch-script）、
  E011（umask 077）、E052（modify_tmpdir）、E060（use-tmpfs）、E125（relocate-build-dir）、
  E129（sed-replace）、E136（TMPDIR/patch-script）；drafts/（DRAFT-6048-babeltrace、
  DRAFT-hogweed-3.9.1、DRAFT-buildtorrent-0.9.1 autoconf-umask-tmpdir 等）；recipes
  先例 ssdeep/2.8、abiword-plugin-*/3.0.8、libgsf —— **完整已有覆盖**
- 七轴查重：exact_duplicate=是（E110/E112/E114/E118 错误签名逐字一致，方案同）；
  causal_duplicate=是（HMDFS 对 mktemp 0700 私有临时目录权限语义，同因）；
  trigger_overlap=高（mktemp/subs1.awk 触发链一致）；solution_overlap=高（预建
  目录+TMPDIR+ac_tmp 改指，E114/abiword/libgsf/ssdeep 同款）；combination_novelty=无；
  boundary_novelty=无（OHOS CI conan 构建目录 HMDFS 已被 E110/E112/E114/E118/E125 覆盖）；
  test_migration_novelty=不适用
- 关系字段：similar_to=E110/E112/E114/E118/E125/E129/E136；caused_by=[]；
  prerequisite_of=[]；conflicts_with=[]
- **决定: reuse_existing（不建新草稿）** — CI 失败候选是既有 E110/E112/E114/E118
  组合的再一次落地，配方修复直接复用 E114 同款实现；基线/环境噪声不入知识库。
  R01 候选 1（signalfd EAGAIN，DRAFT-libuev-2.4.1-ohos-fork-signalfd-eagain-spurious
  .kv/.md）维持 new_draft 结论不变（已随 R01 进入 PR，本轮无变化）。

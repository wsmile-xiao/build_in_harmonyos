# htscodecs 1.6.5 — 适配笔记

## 任务与身份
- task_id: htscodecs-1.6.5-r01-pc1-30-20260921T155530Z
- executor: pc1-30  |  lib: htscodecs  |  version: 1.6.5  |  分支: feat/htscodecs-1.6.5
- 类型: 知识库扩展（候选观察 + 查重 + 草稿）
- 官方源: https://github.com/jkbonfield/htscodecs (tag v1.6.5)
- worktree: /storage/Users/currentUser/junshi_liu/worktrees/htscodecs-1.6.5

## 源码核验
- 下载 URL: https://codeload.github.com/jkbonfield/htscodecs/tar.gz/refs/tags/v1.6.5
- SHA-256: 39857c48462ebab2b2d231d67ccdb08f327406ce10dc1a60834651e38185592f
- 语言预检: task=cpp, detected=c（兼容族，通过）
- 构建系统: autotools（configure.ac/Makefile.am）

## 平台适配点
1. **临时目录权限（HMDFS）**：config.guess 在 `$TMPDIR`（HMDFS 属主 20001006，当前用户 20020101 不可写）创建 dummy.c 失败。修复：使用 `/data/storage/el1/base/ohc-htscodecs`（真实 0700 语义，mkdir+chmod 700+stat 验证通过），并导出 TMPDIR/TMP/TEMP。
2. **config.guess/config.sub 平台识别**：E007。`patch-autotools-ohos.pl` 修补两文件（评分 5/5）后，config.sub 的 kernel-OS 校验列表仍缺 `linux-ohos*-`，手工补加该组合后 configure 通过（否则 "Kernel 'linux' not known to work with OS 'ohos'"）。
3. **bzip2 依赖注入（R49）**：configure 硬性要求 libbz2（`--disable-bz2` 会降低数据流兼容性并使 arith 测试失败）。bzip2/1.0.8 已发布（ohpcd registry 有 recipe+binary），conan 装入私有 prefix 后以 CPPFLAGS/LDFLAGS 注入；conanfile.py 用 AutotoolsDeps + LD_LIBRARY_PATH env 注入（同 aaphoto 模式）。

## 构建结果
- configure: exit 0
- make -j4: exit 0（libhtscodecs.so.2.1.10 + .a，tests 下 7 个测试程序）
- make install DESTDIR 暂存: exit 0（include/htscodecs/*.h 9 个公共头 + lib）
- 非 CLI 库：产物仅 lib + headers，无 bin/ 可执行文件交付 → 不创建 commands.json（R38）

## 上游测试全量枚举台账（官方 tag v1.6.5，按 Makefile.am TESTS/noinst_PROGRAMS 逐项枚举）

### 双口径统计
- source_declared_total: 7（TESTS 注册项：6 个 .test 脚本 + varint 独立可执行）
- configured_executable_total: 7（当前 OHOS 配置全部实例化）
- executed_passed_total: 7
- failed: 0 | uninstantiated: 0（fuzz EXTRA_PROGRAMS 8 项为框架 fuzz 目标，不属用户测试入口，未计入）
- 全量通过率: 7/7 (100%)

### 源码声明 → 注册 → 执行映射
| 源码声明 (Makefile.am TESTS) | 构建目标 | 实际执行 | 结果 |
|---|---|---|---|
| tests/entropy.test | entropy (noinst_PROGRAMS) | make check 执行 | PASS |
| tests/rans4x8.test | rans4x8 (rANS_static_test.c) | make check 执行 | PASS |
| tests/rans4x16.test | rans4x16pr (rANS_static4x16pr_test.c) | make check 执行 | PASS |
| tests/arith.test | arith_dynamic (arith_dynamic_test.c) | make check 执行 | PASS |
| tests/tok3.test | tokenise_name3 (tokenise_name3_test.c) | make check 执行 | PASS |
| tests/fqzcomp.test | fqzcomp_qual (fqzcomp_qual_test.c) | make check 执行 | PASS |
| tests/varint (varint_test.c) | varint | make check 直接执行 | PASS |

### 覆盖内容说明
- 语料：dat/q4、q8、q40+dir、qvar、qsimd、u32 + 预压缩数据目录 dat/arith、dat/fqzcomp、dat/r4x8、dat/r4x16；names/ 11 个 .names + names/tok3/ 110 个预压缩文件
- htscodecs-corpus（外部语料）不在官方 tarball 中，测试脚本以 `2>/dev/null` 优雅跳过（不影响全量通过率口径，bundled 语料已覆盖）
- fuzz 目标（EXTRA_PROGRAMS 8 项：rans4x8_fuzz、rans4x16pr_fuzz、arith_dynamic_fuzz、tokenise_name3_fuzz/_fuzzrt、fqzcomp_qual_fuzz/_fuzzrt、entropy_fuzz）需要 libFuzzer + -fsanitize=fuzzer，为框架 fuzz 工具，非独立用户用例，未计入分母
- javascript/ 目录 14 个 .js 为 JS 参考实现（框架源码），非 C 用户测试入口，未计入

## 鸿蒙专项测试
- tests 侧新增真实可执行 OHOS 专项用例（见 reports/ 与 test_package 区分）：
  - test_package/test.c：消费者视角，调用 htscodecs_version() + rANS 往返压缩/解压（64 KiB 质量值数据），断言字节一致（非空壳，R34/PF3 合规）

## 消费者验证
- 消费者用例：见 test_package/test.c（仅用安装公共头 htscodecs/rANS_static.h，真实调用公开 API，编译/链接/运行验证）

## 待办（后续轮次）
- ~~conan-verify / finish / W2/W3 / W4 审计 / submit~~ → 本轮已完成（conan-verify G1-G4 PASS、finish exit 0、W3 prdiff 模式 JC pass）
- 知识候选台账 + 四范围查重 + 路径决定 → 见下

---

## 知识候选台账（knowledge_candidate_ledger）

任务类型：知识库扩展（knowledge_candidate_observation: required）。本适配遇到的
全部非噪声候选及其四范围查重（graph/index.tsv、knowledge/doc/、knowledge/graph/、
knowledge/drafts/）与七轴结论如下。

### C1 — codeload URL 无扩展名导致 conan get() BadZipFile
- 真实错误：`conan create` source() 报 `BadZipFile: File is not a zip file`
- 根因：URL 末段 `refs/tags/v1.6.5` 无 `.tar.gz` 后缀，conan get() 按 basename 推断格式失败
- 修复：conandata.yml 显式 `filename: htscodecs-1.6.5.tar.gz`（官方 URL 不变）
- 验证：conan-verify G2 PASS（日志 archives/h/htscodecs/1.6.5/reports/conan-create.log）
- 查重：**exact_duplicate**（E276、E483 完全覆盖：codeload + BadZipFile + filename= 方案一致）；E392 亦相关
- 七轴：exact_duplicate=yes, causal_duplicate=yes, trigger_overlap=yes,
  solution_overlap=yes, combination_novelty=no, boundary_novelty=no,
  test_migration_novelty=no
- 决定：**reuse_existing（复用 E276/E483）**

### C2 — config.sub kernel-OS 校验列表缺 linux-ohos*-（patch-autotools-ohos.pl 盲区）
- 真实错误：`Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'`
- 根因：patch-autotools-ohos.pl 只改 OHOS triplet 与 OS 列表，不改
  `case $kernel-$os-$obj` 校验列表行（`linux-mlibc*- )` 前缺 `| linux-ohos*-`）；
  且 `basic_os=linux-ohos` 已含 "linux-ohos" 子串，若按裸字符串判重会被误判为已补丁
- 修复：以 `linux-ohos\*-\s*\)` 模式判重，向校验行追加 `| linux-ohos*-)`
- 验证：conan-verify G2 PASS（干净 conan create 中 config.sub 校验通过）
- 查重：**exact_duplicate**（E268 完全覆盖同一根因与修复，含 `grep 全文 linux-ohos`
  误判细节；E122 亦覆盖 kernel-os 校验列表补丁；E007 覆盖 config.guess 检测）
- 七轴：exact_duplicate=yes, causal_duplicate=yes, trigger_overlap=yes,
  solution_overlap=yes, combination_novelty=no, boundary_novelty=no,
  test_migration_novelty=no
- 决定：**reuse_existing（复用 E268/E122/E007）**

### C3 — config.status 临时目录 mktemp drwx--S--- 不可写（HMDFS）
- 真实错误：`./config.status: line 816: ./confbYzDlm/subs1.awk: Permission denied` /
  `config.status: error: could not setup config files machinery`
- 根因：HMDFS setgid + `umask 077 && mktemp -d` 生成 drwx--S--- 目录，属主亦不可写
- 修复：移除生成的 configure 中 `umask 077 && mktemp -d` 的 umask（E114 方案）
- 验证：conan-verify G2 PASS（conan create 干净树中 config.status 正常生成）
- 查重：**exact_duplicate**（E114 完全覆盖 HMDFS mktemp drwx--S---；E175
  confXXXXXX mktemp config.status 亦覆盖）
- 七轴：exact_duplicate=yes, causal_duplicate=yes, trigger_overlap=yes,
  solution_overlap=yes, combination_novelty=no, boundary_novelty=no,
  test_migration_novelty=no
- 决定：**reuse_existing（复用 E114/E175）**

### C4 — clean `conan create` 中 OHOS autotools 适配补丁自包含进 conanfile.py（R02 扩展：aclocal tool_requires 自举）
- 真实错误（R01 基线）：conan create 干净树中 SKILL_ROOT/patch-autotools-ohos.pl 不可用，
  config.guess/config.sub/configure umask 三处平台补丁必须内联进 recipe build()；
  autoreconf 生成的 configure 由 `if not exists("configure"): autoreconf -i -f` 引导；
  E268 判重须用精确模式 `linux-ohos\*-\s*\)`
- **R02 核心扩展（本次返工修复）**：远端 CI 干净环境预装 autoconf 但**不预装
  automake/aclocal**，`autoreconf -i -f` 报 `Can't exec "aclocal"`（exit 2）；
  且 configure.ac 用 LT_INIT，缺 libtool.m4 时 automake 报 `LIBTOOL is undefined`。
  修复：build_requirements() 声明 `tool_requires("automake/1.18") +
  tool_requires("libtool/2.5.4.1")`（制品仓已发布），使干净 conan create 自包含。
  **实测陷阱**：不能顺手 tool_requires autoconf——其 conan 包依赖 conan perl，
  XS 模块（Cwd.so）污染 buildenv，使系统 autoreconf 报 `Perl_my_cxt_init: symbol
  not found`（同 DRAFT-6049 perl 双架构族；htscodecs 实测 exit 255）。
- 验证（R02，CI 等价干净缓存 PATH 无 aclocal 四连）：① 原配方 Can't exec
  aclocal（exit 2）；② +autoconf Cwd.so symbol not found（exit 255）；
  ③ +automake LIBTOOL undefined；④ +automake+libtool conan create EXIT=0、
  make check 7/7 PASS、test_package 1/1 PASS、conan-verify G1-G4 PASS
- 查重：**组合条目未命中/部分覆盖**。DRAFT-libuninameslist-conan-autotools-
  bootstrap-toolrequires 覆盖"tag 归档无 configure → tool_requires(automake/libtool)
  + autoreconf 自举"的通用模式（solution_overlap=partial）；DRAFT-6049 覆盖 perl
  双架构 handshake 但方案是 PERL=perl 显式统一解释器（htscodecs 用"不引入
  autoconf"回避，边界不同）；本条目新增差异：①三补丁内联 + autoreconf 自举 +
  tool_requires 自包含的配方内组合；②"禁止 tool_requires autoconf（perl XS 污染
  系统 autoreconf）"的反例边界；③CI 已有 autoconf 时只补 automake/libtool 的最小
  依赖原则。可跨库复用（任意 autotools+OHOS conan 配方）
- 七轴：exact_duplicate=no, causal_duplicate=no, trigger_overlap=partial（同
  autotools/OHOS/conan 域）, solution_overlap=partial（libuninameslist 自举 +
  各单条补丁均存在，配方内"三补丁+自举+禁 autoconf"组合无既例）,
  combination_novelty=**yes**, boundary_novelty=**yes**（禁 autoconf tool_requires
  反例边界 + CI 仅缺 automake 的最小自举）, test_migration_novelty=no
- 关系：similar_to=E268/E114/E007/E490/DRAFT-libuninameslist-conan-autotools-
  bootstrap-toolrequires/DRAFT-6049-libnxml-0.18.5-autotools-perl-dual-arch;
  caused_by=conan create 干净树 + CI 不预装 automake; prerequisite_of=无;
  conflicts_with=无
- 决定：**new_draft（路径 B）** — 已验证、可跨库复用（任意 autotools+OHOS conan
  配方）、四范围查重未命中组合条目；R02 同步 tool_requires 自举部分后差异仍成立

### 路径初判
根据任务规则：存在**已验证、可跨库复用且查重为未命中/部分覆盖并存在新增差异**
的候选 C4 → 必须走 **路径 B（知识库扩展）**，本库建立同 stem 的 .md/.kv 配对草稿
（知识库草稿与三方库归档文件进入同一 PR）。C1/C2/C3 复用既有条目（E276/E483、
E268/E122/E007、E114/E175），不建草稿。
最终决定：`new_draft`（C4）→ 知识库扩展 PR，标题前缀【知识库扩展】。
---

**编译结束**: 2026-09-22 14:46
**最终状态**: built

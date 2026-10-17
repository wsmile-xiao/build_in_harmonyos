# jpegqs 1.20210408 适配笔记

- 适配路径: A
- 使用知识库: 是（命中既有 `-march=native` 家族草稿，按其处置口径覆盖上游 Makefile 宿主优化标志；未新建条目）
- 知识库扩展: 无
- 关联 Issue: 不适用（路径 B 判定 = hit，沿用既有 `-march=native` 家族草稿与已晋升正式条目 E412，不新建知识库条目、不建【知识库扩展】Issue，本 PR 标题亦不带该前缀）

## 包与上游

- 上游：<https://github.com/ilyakurdyukov/jpeg-quantsmooth>（Ilya Kurdyukov, 2020-2021）。
  仓库名核对（任务书 §2① 要求两个候选都核，不猜）：
  - `https://api.github.com/repos/ilyakurdyukov/**jpeg-qs-codec**/tags` → **HTTP 404**（`Not Found`，
    该仓名不存在，台账里的这个写法是错的）；
  - `https://api.github.com/repos/ilyakurdyukov/**jpeg-quantsmooth**/tags` → **HTTP 200**，
    且 tag 列表含 `1.20210408`（commit `c86c6418ea6c827513d206694847033f9ca50151`），
    另有 `1.20200517/1.20210110/1.20230818/1.20240129/1.20260122` ⇒ **上游确实打 tag**
    （本笔记上一棒写的"上游不打 release tag"经实测为误，已更正）。
- `sources.url` 定案：**换成上游官方 https 通道**
  `https://github.com/ilyakurdyukov/jpeg-quantsmooth/archive/refs/tags/1.20210408.tar.gz`。
  依据 = 任务书 §2①.2 的硬条件"**sha256 与 Debian `.orig` 逐字相同才换**"，本机两侧实测同一
  散列、同一字节数、`cmp` 逐字节相同（命令与输出见 `~/tmp/uc2/z32-jpegqs/GATES.md` §1）：

  | 通道 | HTTP | 字节 | sha256 |
  |---|---|---|---|
  | 上游官方 tag 归档 | 200 | 65410 | `5937ca26…3116` |
  | Debian pool `.orig` | 200 | 65410 | `5937ca26…3116` |

  `cmp` 退出码 0、`tar tzf` 归一化清单两侧各 31 条且 `diff` 为空、顶层目录两侧同为
  `jpeg-quantsmooth-1.20210408/` ⇒ Debian 池里那份 `.orig` 就是上游官方 tarball 的原样分发
  （无 dfsg、无 repack）。因此本次换 URL 是**换通道不换字节**：`sha256` 字段保持
  `5937ca26db33888cab8638c1a8dc7a367a953bd0857ceb1290d5abc6febf3116` 不变，未使用镜像代理域、
  未用 `file://`、未加 `--no-preflight`。
  - 连带效应（已按 §2①.4 处理）：`conandata.yml` 变更 ⇒ recipe revision 变 ⇒ 本轮
    **重跑** create / conan-verify / finish(W3) / graph / PF1-PF9，判决行与行号见 GATES.md §2。
  - PF7 复核：`scripts/ohc/preflight.py:361` `_PF7_DEBIAN_HOSTS` 在 `:379` 对
    `deb.debian.org` 一律判「Debian 下游重打包源」，且扫描器（`:407-410`）对
    `conandata.yml` **与** `manifest.yaml` 中含 `url:` 的行都取值判类 ⇒ 上一棒留的
    "只能靠 PR 说明 + `--no-preflight`" 的悬置项已不必要，本包现在是 PF7 干净形态。
- 实测：官方 tag 归档 HTTP 200、65410 字节，`sha256sum` =
  `5937ca26db33888cab8638c1a8dc7a367a953bd0857ceb1290d5abc6febf3116`，与 Debian 索引
  `Checksums-Sha256` 及上游归档逐字节一致。
- 语言 / 构建系统：C / 裸 Makefile（无 configure、无 `install` 目标、无 `PREFIX`、无
  `-Werror`、无 `TESTS`）。解包 **27 个文件，其中 6 个 `.c` + 5 个 `.h`**（上一版把 11 写成
  `.c` 数，11 实为 `.c + .h` 之和），另有 4 个 `.sh`。
  复算：`find <pristine> -type f | wc -l` = 27、`-name '*.c' | wc -l` = 6、
  `-name '*.h' | wc -l` = 5、`-name '*.sh' | wc -l` = 4。

## 构建决策

1. `SIMD=none`（→ `-DNO_SIMD`）：上游 Makefile 第 15 行 `SIMD := native` 会带
   `-march=native`，把构建机 ISA 烧进产物，CI 产物不可复现。GNU make 命令行变量优先级高于
   makefile 内的 `:=` 赋值，故 `make SIMD=none` 一行覆盖即可；`quantsmooth.h` 中
   SSE2/AVX/AVX512/NEON 分支全部位于 `#ifndef NO_SIMD` 之内（实测 `quantsmooth.h:83`，
   同条件另见 `:377`），标量路径完整可用。与既有机制同族（见文末路径 B 判定），差异是上游
   **自带** `SIMD` 开关，因此不必像 tommyds/genann 那样绕过 Makefile 或改写 CFLAGS。
   - **未测面披露（本包按上游自带开关取 `SIMD=none`，因此 NEON 路径未编译、未测试）**：
     `-DNO_SIMD` 使 aarch64 向量面完全不参与编译——`quantsmooth.h:132-134` 在
     `#if defined(__ARM_NEON__) || defined(__aarch64__)` 下 `#define USE_NEON`（`:133`）并
     `#include <arm_neon.h>`（`:134`），`idct.h:91` 与 `idct.h:458` 的 NEON fdct/idct 核都在
     `#if 1 && defined(USE_NEON)` 之下 ⇒ **12 条断言只覆盖标量路径**，本包仅交付并验证标量
     路径，**不主张 SIMD/NEON 面已验证**。这是**取档决定**（用上游自带开关换产物可复现），
     **不是平台限制**。
     复算判据：`grep -n USE_NEON <pristine>/quantsmooth.h` → `:133`/`:137` 定义、
     `:152`/`:251`/`:388`/`:585`/`:726`/`:1013`/`:1211`/`:1369` 使用；
     `grep -n USE_NEON <pristine>/idct.h` → `:91`/`:458`；
     本轮编译行实测 `reports/w3-local-ci.log:187`（`make … SIMD=none MTOPTS= … -j1 app lib`）
     与 `:188`/`:201`（两条 `clang … -DNO_SIMD …`）。
2. `MTOPTS=`（去掉 `-fopenmp`）：`quantsmooth.h:28` 的 `#include <omp.h>`（第 27 行是
   `#ifdef _OPENMP`）与各 OpenMP 循环都在 `#ifdef _OPENMP` 之下，并给出
   `#define omp_get_thread_num() 0` 退化实现，因此去掉
   `-fopenmp` 后源码仍正确编译，产物不再需要 OpenMP 运行时（B 机 clang 15 实测可链
   `-fopenmp`，但 CI worker 的 libomp 存在性不可假设）。代价：`-t/--threads` 退化为单线程，
   输出结果不变。
3. `JPEGLIB="-I... -L... -ljpeg"`：Makefile 无 install/prefix，依赖 flag 只能经 `JPEGLIB`
   注入；其 `-I%` 会被 `$(filter -I%,$(JPEGLIB))` 追加到 `CFLAGS_APP`，一个变量同时覆盖编译
   与链接。路径取自 Conan 依赖 `libjpeg/10` 的 `cpp_info`，编译器取自
   `tools.build:compiler_executables`（R33，不用裸 shell 变量）。
   - ⚠ 本仓 conan 为 2.29.1：`self.conf.get("tools.build:compiler_executables:c")` 会抛
     `ConanException: [conf] ... does not exist in configuration list`（`conan config list`
     只注册整张 dict conf，子键 `:c` 不是合法 conf 名）。必须
     `conf.get("tools.build:compiler_executables", check_type=dict, default={})` 再取 `.get("c")`。
4. 目标 `app lib` 一次 make 同时产出 CLI `jpegqs` 与静态库 `libjpegqs.a`；`-j1`（R9）。
5. `package()` 手工 copy 产物：`make install` 不存在、OHOS 亦无 coreutils `install(1)`；
   仍走 `conan create` 组包，未手工打包（R16）。`jpegqs.1` man 页一并装到 `bin/`。
6. 未新增任何补丁，未在配方里注入 `__OHOS__` 平台宏（R8/PF5）；`patches/` 目录不建。
7. `package_type = "application"`：对外主要制品是 CLI 工具，故按 R38 在**软件级**目录声明
   `commands.json`；同时交付静态库供消费者链接（`cpp_info.libs = ["jpegqs"]`，
   `system_libs = ["m"]`）。

## 依赖（W0）

- 精确依赖：`libjpeg/10`（唯一编译期与链接期需求；无 tool_requires）。
- 为什么必需（实测源码）：`libjpegqs.c:28` 直接 `#include "jpeglib.h"`（缺头即
  `fatal error: 'jpeglib.h' file not found`，已实测），CLI `quantsmooth.c` 走 libjpeg
  transcode API（`jpeg_read_coefficients` / `jpeg_write_coefficients`）。**不是**只在
  demo 里用到 ⇒ 核心库与工具都依赖它，无法按"能省则省"去掉。
- 制品仓 libjpeg 家族可用版本（主窗已核）：`libjpeg/10`、
  `libjpeg-turbo/{2.1.5.1, 3.0.4, 3.1.4.1, 3.2.0}`、`libjpeg9/9f`；取 `libjpeg/10` 与同族
  CLI 包 `archives/j/jpeginfo/1.7.1` 一致（同为 IJG 接口）。
- 判据（权威读数；日志在构建机 `~/tmp/uc2/z32-jpegqs/`，属证据目录、不入仓）：
  `bash ci/scripts/preflight_check.sh jpegqs/1.20210408` 的输出
  `g1-preflight.log:8` = `[OK] 已发布: libjpeg/10`、`:14` =
  `[OK] 所有依赖均已发布到制品仓，可以安全开始适配 jpegqs/1.20210408`
  （同日志 `:11` = `[OK] 版本号未被占用: jpegqs/1.20210408`，R37）。
  W0 明令禁止用通配 `conan list` 判二进制，本包全程未用（证据目录里 `conan list` 只出现在
  正文自述中，无判 binary 的命令）。
- 本轮真实构建路径（事实披露，不是缺陷）：`g2-create.log:46`
  `libjpeg/10: Main binary package '42f30234e57c7cfe0d4745225b6ca7e5e4d83cfc' missing` →
  `:60` `libjpeg/10: No compatible configuration found` → `:86`
  `libjpeg/10: Sources downloaded from 'ohpcd'`（配方确在远端制品仓）→ `:92`
  `libjpeg/10: Building from source` ⇒ 发布态成立，但该配置的**制品未命中**，本轮由本地
  从源码重编；CI worker 的缓存同样不带这个配置，**很可能同样现场重编 libjpeg**（代价是
  耗时量级，不是正确性）。旧稿把 `libjpeg/10: Already installed!` 当判据属**弱读数**：
  缓存命中不等于发布态，且那行出自换 URL 之前的旧轮日志（旧 recipe revision
  `run1.log:11` 的 `#c97681eb…`；本轮为 `g2-create.log:13` 的 `#111508c99d…`），已弃用。

## 测试账（R51 / rule4）

- 上游测试清点（取证）：
  - `tar tzf jpegqs_1.20210408.orig.tar.gz | grep -ciE 'test|spec|check'` → 0
  - `grep -n '^[a-z_-]*:' Makefile` → 只有 `clean/all/app/lib` 等目标与文件规则，
    无 `check`、无 `TESTS` ⇒ 上游无可注册测试套件，`upstream_tests: []`。
    （故 `test_package/MANIFEST.yml` 的 `upstream_check_command` 亦置空：上游 Makefile
    实测 `grep -cE '^check:|^TESTS|^test:'` = 0，若填 `make check` 会与 `upstream_tests: []`
    自相矛盾、并让 CI 的 L0e 得到 `No rule to make target`。）
- 适配后：`test_package/test.sh` 12 条 `PASS n` 断言，全部真实执行产物（CLI 转码两次 +
  输入由 libjpeg 参考编码器现做 + 消费者程序链接并运行打包好的 `libjpegqs.a` + 打包件
  存在性）。三条同源：`MANIFEST.yml assertion_count = 12` = `test.sh` 内 `ok()` 调用 12 次
  （`grep -c '^ok '` = 12，且 `set -eu` ⇒ 断言不过就走不到 PASS）
  = 日志实测 `ALL_TESTS_PASSED=12`。同源指针已换成**本轮**两件：
  `~/tmp/uc2/z32-jpegqs/g2-create.log:450-462`（`PASS 1..12`）与 `:463`
  （`ALL_TESTS_PASSED=12`）；`reports/w3-local-ci.log` 的 `^PASS ` 计数 = 12
  （`:261`–`:273`）与 `:274`（`ALL_TESTS_PASSED=12`）。旧稿指向的 `run1.log:120` /
  `:107-119` 属换 URL 前的旧 recipe revision（数字 12 本身在本轮两份日志里都复算成立），
  已替换。
- 上游 0 用例 → 适配后 12 条消费者侧断言，未虚报上游测试数。

## 路径 B 四范围查重（实测命令与命中数）

| 范围 | 命令 | 命中数 |
|---|---|---|
| knowledge/graph/*.kv | `grep -rilE 'quantsmooth\|march=native\|jpegqs' knowledge/graph/*.kv` | 0（**字面检索式**为 0，不等于图谱无相关条目，见下 E412） |
| knowledge/graph/index.tsv | `grep -inE 'quantsmooth\|march=native\|jpegqs' knowledge/graph/index.tsv` | 0 |
| knowledge/drafts/*.kv | `grep -rilE 'quantsmooth\|march=native\|jpegqs' knowledge/drafts/*.kv` | 4 |
| archives/**/notes.md | `grep -rlE 'SIMD=none\|march=native\|quantsmooth' archives/ --include=notes.md` | 32 |
| knowledge/graph 按概念读正文 | `grep -n -E 'title\|root_cause\|affected_scope' knowledge/graph/E412.kv` | 命中 1 条已晋升正式条目（`:13`/`:15`/`:16`，见下） |

草稿命中清单：`DRAFT-genann-1.1.1-make-cflags-march-native-override.kv`、
`E543-draft-TOMMYDS.kv`、`E1000-draft-A1B2.kv`、
`DRAFT-8958-clthreads-makefile-stage-install-shadow.kv`。

**按概念（而非包名/字面 flag）检索后，图谱里已晋升的正式条目也是命中面**：
`knowledge/graph/E412.kv:15-16` 的主张是"把可选加速后端显式关掉，以保证自包含静态产物不随
构建 worker 变化；仅当上游自带完整实现、后端只影响性能而非功能时，关掉才成立"，其
`affected_scope`（`:16`）**明列 crypto / compression / SIMD backends** ⇒ 与本包 `SIMD=none`
+ `MTOPTS=` 的处置同因同向（本包正落在它划定的"合法关闭"条件内：上游自带完整标量实现）。
**这让 hit 判定更稳，结论不变**（不新建条目、不建【知识库扩展】Issue）。
按本项目口径该条目以文件名/编号引用（`.kv` 的 `id` 与顶部注释存在编号复用，故引
`knowledge/graph/E412.kv` 这一路径，其 `id: E412`、`title: Make optional acceleration
backends explicit in self-contained static packages`）。

一处可交叉引用的失效面否证：`knowledge/drafts/DRAFT-E616-upstream-auto-tarball-vs-release-src-asset-submodules.kv`
（GitHub 自动 tarball 与 release 资产不同源、子模块在自动归档里为空）⇒ 对本包不成立：
pristine 树**无 `.gitmodules`**、自动 tag 归档 27 个文件齐全（含全部 5 个头文件），
构建与 12 条断言都在该 tarball 上成立 ⇒ 该机制的失效面被否证，不构成本包的额外披露。

**判定：hit（同机制家族），不新建知识库条目。** 四条件对照：

| 条件 | 本包 | 既有条目（E543-draft-TOMMYDS / DRAFT-genann-1.1.1 / 正式条目 E412） | 对照 |
|---|---|---|---|
| 同机制 | 上游 Makefile 把 `-march=native` 写进构建变量 | 同一现象 | ✅ |
| 同根因 | 构建宿主 ISA 被烧进产物、交叉/CI 下不可复现 | 同一根因 | ✅ |
| 同处置面 | `make SIMD=none`（上游自带开关）+ `MTOPTS=` | `make CFLAGS=` 覆盖 / 绕过 Makefile 直接编译 / E412 的"显式关掉可选加速后端" | ✅ 同：显式关掉可选加速项以保证产物不随 worker 变化；本包差异（上游自带 `SIMD` 开关、故不必覆写 CFLAGS 或绕 Makefile）属**包特有的既有便利**，不构成新的平台行为差异，故不足以升 create |
| 同作用域 | 裸 Makefile C 包 / Conan 交叉 OHOS armv8 | 同上 | ✅ |

⇒ 属既有机制的**同一处置族**，无新增平台行为差异，故 **路径 A、不建扩展、不建
【知识库扩展】Issue**；台账 B潜力：低 与实测一致。若主窗按 `OHOS行为探针清单` 的
「家族命中是否升 B」口径另有判断，可据此表改判（判据、命中文件与行号均在上）。
## 门禁序列（本轮重跑，URL 变更后 recipe revision 已变）

- 序列：`ci/scripts/preflight_check.sh jpegqs/1.20210408`（W0）→ `conan create` →
  `ohc-run.py conan-verify`（G0-G4）→ `ohc-run.py finish jpegqs 1.20210408 built`（W2+R36+**W3**）→
  `ohc-run.py graph validate` → `scripts/ohc/preflight.py . origin/main HEAD`（PF1-PF9）。
- 逐项判决行原文、日志行号、字节数/mtime、判决标记数与 md5 ⇒
  `~/tmp/uc2/z32-jpegqs/GATES.md`（§1 源 URL 定案取证、§2 门禁序列、§3 PF 与提交）。
- **证据件位置口径**（免得读者在 PR 里找不到文件）：`reports/`（`w3-local-ci.log`、
  `conan-create.log`）、`.ci-result.json`、`.build-closed`、`.conan-verified`、
  `conandata.yml.orig` 等都被 `archives/.gitignore` 忽略、**不入仓**，只存在于构建机
  worktree 磁盘与证据目录 `~/tmp/uc2/z32-jpegqs/`。本 PR 的可核面是 `archives/j/jpegqs/`
  下的 12 个跟踪件（10 个原有 + 本轮新增的 `test_package/consumer.c`、`makejpeg.c`）
  ⇒ 上面引用的日志行号属"构建机上可复算"，不是"PR 内可点开"。
  另须报备一处本轮发现：被忽略的 `reports/conan-create.log` 是**更早一次** create 的副本
  （`:10` 导出的修订号为 `#777a51cc0cb106d830889e36fa5628d4`），与本轮判决件
  `g2-create.log:13` 的 `#111508c99d2ef5c6ee22b6498c1ba25c` 不是同一次 ⇒ 判同源一律以
  `~/tmp/uc2/z32-jpegqs/g2-create.log` 与绿件 `reports/w3-local-ci.log` 为准；本轮不改
  HEAD、不重跑 create，故只披露不刷新该副本。
- 测试账同源（本轮 create 日志复读）：`MANIFEST.yml assertion_count=12` =
  `test.sh` 的 `PASS n` 条数 = 日志 `ALL_TESTS_PASSED=12`。

### W3 首红的真因（归因更正，别照抄旧处置）

上一版台账把 W3 首红写成"`conan create` 落在 `test_package/` 的运行产物触发 JC1/JC5，
清掉就修好了"——该归因经独立审计复算为**误**，正确因果是：

- `finish` 跑在 `git commit` **之前** ⇒ `git diff --name-only origin/main...HEAD` 为空 ⇒
  `ci/scripts/junk_check.sh:54-56` 落入 **full 模式**（判定面 = 整仓 `git ls-files` 的
  85522 个跟踪文件），而不是只查本 PR 的变更面。
- 该模式下 JC1/JC5 各报的 3 件其实是**别人已合并进 main 的存量标记件**：
  `archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、
  `archives/k/kics/2.1.20/.staging-verified`（判据见 `junk_check.sh:92` 的
  `/\.(staging-|build-closed|conan-verified|…)`）。本包自己的 `test_package` 产物是
  **未跟踪件**，从来不在 JC1/JC5 的判定面内（full 模式取 `git ls-files`，只见跟踪件）。
- 真正让 W3 转绿的动作是"**先 commit 再复跑 finish**"：模式随之变为
  `检查模式: prdiff (10 个文件)`（本轮绿件 `reports/w3-local-ci.log:73`）。清除自建产物
  与本次红**无因果关系**，它只是"不把编译产物/图片二进制带进仓库"的卫生动作。
- 「未误删他人文件」的可复算证据：`git status --porcelain | grep -c '^ D'` = **0**；
  `git ls-files | wc -l` 在审计轮的审前 = 审后 = **85522**（本整改轮新增 2 个夹具源码件后为
  85524，删除件数仍 0，见下「产物卫生」）；`git log --diff-filter=D --name-only
  48d9cee684..HEAD` = 空；`archives/c/cloog/0.21.1/.staging-verified` 与
  `archives/k/kics/2.1.20/.staging-verified` 至今仍在 `git ls-files` 里且在盘上；
  备份面 `find ~/tmp/uc2/z32-jpegqs/junk-backup -type f` 恰 7 件，全部在本包
  `test_package` 语义内（consumer / consumer.c / makejpeg / makejpeg.c / src.jpg /
  out.jpg / out2.jpg）。

### 已知未完项（本轮只披露、未改任何判据）

以下红项/未完项原文都在构建机 `~/tmp/uc2/z32-jpegqs/GATES.md`（证据目录、不入仓），
本节把它们补进 PR 面。本轮整改**未**触碰 `scripts/`、`ci/`、`templates/` 或任何判据
（`git diff --name-only 48d9cee684..HEAD -- scripts ci templates SKILL.md` 为空）。

- `FINISH2_RC=1`（`GATES.md:209`）＋ 外层失败步骤 `STEP_FAILED: Step6`
  （`GATES.md:218`、`:305`）：外层 rc 与 W3 判决不同源 ⇒ 并列披露。绿件本体：
  `reports/w3-local-ci.log` 判决标记 57 条、`.ci-result.json` 为
  `exit_code: 0` / `integrity_hash: d76e20c36b49b5e5` /
  `log_sha256: 31de47ab4d72b9fbf97a8b4cecd62a5f085e2f8263b6ea7b7aefe5127f4453f6`。
- `step5b`：`manifest.yaml: knowledge_count=3 unreferenced=3` ＋
  `存在知识遗漏: pending=0 failed=0 unreferenced=3`（`GATES.md:275-276`）——属存量判据口径。
- `step8`：`gen_summary 失败: 'str' object has no attribute 'append'`（`GATES.md:279`），
  框架侧报错，未改判据。
- `Step10` 三项未就绪：`reports/test-report.md`、`packaging/`、`.staging-verified`。
  仓内占比（`git ls-files archives` 复算）：7751 个版本目录里分别只有
  450 / 372 / 2 ⇒ 属**存量/可选**产物，不是本包漏件；仍按"已知未完项"列在 PR 面。
- `PF1-PF9` 第三跑 `rc=1`，只剩 `PF9`（`GATES.md:261-263`）：PF9 报"变更路径缺版本目录层"
  与 R38 要求的软件级三件套 `archives/j/jpegqs/{README.md,commands.json,manifest.yaml}`
  互斥 ⇒ 三件套都在提交里（**未删除凑绿**），只披露。
- `L2` 冒烟（`--version` / `--help`）为 `skip`：`reports/w3-local-ci.log:294`
  `L2_RESULT=skip: jpegqs version/help failed` —— CI 裸跑不载 runenv 时的框架预期口径，
  既非失败，也不构成本包的可执行证据。
- 外观项（本轮**不动 HEAD**，否则 recipe revision 变化会作废本轮 create/verify/W3 的真跑
  证据链）：`conanfile.py:103` 把 man 页 `jpegqs.1` 装进 `bin/`、`:106` `bindirs` 含 `bin`
  ⇒ 消费者 PATH 里会出现一个非可执行文件。已在 PR 说明里留话，留待后续轮次与配方类改动
  一起处理。

### 产物卫生（整改轮第 0 步）

- `test_package/` 下由 `conan create` 落的运行产物 `makejpeg`（149952 B 可执行）、
  `src.jpg`、`out.jpg`、`out2.jpg` **不在 `archives/.gitignore` 的覆盖范围内**
  （`git check-ignore -v` 对这些路径无输出 = NOT-IGNORED，而 `conandata.yml.orig` 会被
  `archives/.gitignore:4` 的 `*.orig` 命中）。而入库动作是按包目录
  `git add archives/j/jpegqs/` ⇒ 整目录 add 会把它们带进仓，故本轮先把这 4 件
  `mv` 到构建机 `~/tmp/uc2/z32-jpegqs-fix1/tp-products/`（`mv`，不删）。
  判据：`git status --porcelain -- archives/j/jpegqs` 的 `??` 行在 mv 后只剩 2 个夹具源码，
  `git add` 后该路径 `??` 计数 = 0。
- `test_package/consumer.c` 与 `makejpeg.c` **留在原地并入库**：`test.sh:18` 执行
  `./makejpeg`、`test.sh:50` 执行 `./consumer`，两个夹具是断言面的一部分。
  须同时说明其可再生性：二者由 `test_package/conanfile.py:103-105` 在 `build()` 里从内嵌
  常量 `MAKEJPEG_C` / `CONSUMER_C` 逐字写出，入库是为评审可读与断言可追溯，**不是**
  因为不入库就会缺件（编译出的二进制 `makejpeg`/`consumer` 与 jpg 则一律不入库）。
---

**编译结束**: 2026-09-25 03:57
**最终状态**: built

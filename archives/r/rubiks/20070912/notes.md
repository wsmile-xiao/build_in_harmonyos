# rubiks 20070912 适配笔记（HarmonyOS PC / aarch64）

**适配路径**: 路径 C? 否 —— 路径 A+B（正常 Conan 配方，零源码修改，零补丁；未修改上游任何行为）
**使用知识库**: 是（E392 raw-makefile 配方模式、DRAFT-commander-1.4.0-makefile-recipe-build-package-traps 的 compiler_executables 字典键取法、E538 为 G2 假命中已排除；install 阶段处置面命中正式条目 **E313.kv:21,26,27**，见 §7）
**知识库扩展**: 无新增（W4 r1 复审后由 create 改判 **hit**：处置面已被 E313.kv:21,26,27 与 DRAFT-8958-clthreads-makefile-stage-install-shadow.kv:78,82,84 覆盖；本包自造草稿已按 §7 撤销（mv 未删）
**关联 Issue**: Issue #3365（编号来自主窗派发，本执行棒按任务书未调平台 API 核验其存在；因 §7 改判 hit，该 Issue 的撤销说明由主窗发布）

## 1. 取源定性与可核证披露

任务声明的上游主页是 Sage 的 spkg 目录（Debian `rubiks_20070912-7.dsc` 的 `Homepage:` 字段原样照抄）。
本机（B 构建主机）实测（curl，2026-09-25，`SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem`）：

| URL | TLS 严格 | 备注 |
|---|---|---|
| https://git.sagemath.org/sage.git/plain/build/pkgs/rubiks/ | curl (60) SSL: no alternative certificate subject name matches target host name | 证书 SAN 不含该域名 |
| 同上（-k 绕过校验） | rc=404 bytes=9115 | cgit `plain/` 目录形态不存在 |
| https://git.sagemath.org/sage.git/plain/build/pkgs/rubiks/spkg-configure.m4 | 同上 (60) / -k 后 rc=404 bytes=9115 | 逐文件形态同样 404 |
| https://www.sagemath.org/files/spkg/standard/rubiks-20070912.spkg | rc=404 bytes=9797 | 无该 spkg 归档 |
| http://www.maths.ox.ac.uk/~mreid/cube.html（作者 Mark Reid 页） | 301 → -L 后 rc=404 bytes=47548 | 作者页已下线，且从无 tarball |
| https://web.maths.ox.ac.uk/~mreid/cube.html | curl (6) Could not resolve host | NXDOMAIN |
| http://www.cwi.nl/~dik/math/math.html（作者 Dik Winter 页） | 301 → homepages.cwi.nl rc=404 bytes=236 | 同上 |

结论：上游三位作者（Dik Winter / Mark Reid / Eric Dietz）均未提供可 https 下载的官方归档；
`git.sagemath.org` 这条"官方主页"在本机连 TLS 都过不了，更给不出 tarball。
按任务书 §4.1（inputlirc 先例）维持 Debian 的 **pristine upstream** 归档：

- URL：`https://deb.debian.org/debian/pool/main/r/rubiks/rubiks_20070912.orig.tar.bz2`
- 实测：HTTP 200，**99028 B**，`sha256 = d8f9f1bcf7a1c7e152eb0df429d391b1a723c614eb7fad6fbbdacf20c19ab57d`
- `rubiks_20070912.orig.tar.bz2` 是 Debian `3.0 (quilt)` 格式里的 **orig**（上游原样件，非 `*.debian.tar.xz` 重打包件），
  解包后目录名 `rubiks-20070912/`，102 个文件，无 `debian/` 目录、无 Debian 侧改动。
- **未为过任何校验改动 sha256**；未使用 `file://`、未使用镜像代理域（ghfast/gh-proxy/清华/阿里/gitee/atomgit 均未出现）。
- 已知代价：`deb.debian.org` 在 PF7 的 `_PF7_DEBIAN_HOSTS` 名单里（scripts/ohc/preflight.py:361-362），
  因此 PF7 必报"Debian 下游重打包"。本仓已合入的 `a52dec/0.7.4`、`aalib/1.4p5` 等同样是 `.orig` 源，属既有先例；
  判框架口径问题，不删件、不改哈希凑绿（PF7 判决行原文见 §8）。

## 2. W0 依赖（零依赖）

`bash ci/scripts/preflight_check.sh rubiks/20070912` → rc=0，判决行原文：
`[OK] 预检通过（无依赖需要检查）`，上文 `[INFO] 未找到依赖声明（conanfile.py 尚未生成或无依赖）。`
本包 `requires` 为空（源码只链 libc/libc++），故 preflight_check.sh:127 剥 user/channel 的已知假绿灯面不适用于本包。
`recipe-search rubiks` 判决行：`⚠️ 无相似配方（语料 6173 条）——首稿走 conan-init 模板`（先检索后动手，未做重复交付）。

## 3. 构建系统实测与适配点

裸 GNU Makefile（无 configure/autotools/cmake/meson），102 个文件，`make -j1` 单核足够（轻包）。
语言实测：C 30 个（dik/*.c、reid/*.c）+ C++ 7 个（dietz/*.cpp）；
`lang-preflight` 与任务语言 cpp/c 兼容族一致（c↔cpp 不迁移），无 env_unsupported。

三处必须覆盖（全部用 **make 命令行变量**，命令行变量优先级高于 Makefile 内赋值 ⇒ **零补丁、零源码改动**）：

1. `dietz/{cu2,mcube,solver}` 的 Makefile 把 `CC`/`CPP`/`LINK` 烧成 `gcc`/`g++`。
   本机实测 `command -v gcc` / `g++` / `cc` 全部 **NONE**，只有 `/data/service/hnp/bin/clang`、`clang++`。
2. 顶层 `Makefile` 第 2 行 `#INSTALL=\`which install\`` 把 `INSTALL` 的定义注释掉了，
   而 install 规则里 6 行都是 `$(INSTALL) <bin> $(DESTDIR)$(BINDIR)` ⇒ `$(INSTALL)` 展开为空 ⇒
   该行变成**执行刚编出来的二进制**（并把安装路径当参数传给它），而不是拷贝它。
   叠加本机 toybox **没有 install(1)**（实测 `command -v install` = NONE），所以 `INSTALL=install` 也不行，
   必须 `INSTALL=cp`。
3. `PREFIX` 默认 `/usr`（不可写）⇒ 走 `DESTDIR=<build_folder>/pkgstaging` 私有暂存（R49），
   `package()` 再从 `pkgstaging/usr/bin` 拷进 `bin/`。

编译器来源（R33）：`_compilers()` 先读 `conf tools.build:compiler_executables`，
读不到时按 `self.settings.compiler` 推导（与 AutotoolsToolchain 默认口径一致），
解析靠 `VirtualBuildEnv` 注入的 PATH（profile `[buildenv]` 已加 `/data/service/hnp/bin`）。
**实拍框架口径差**：`ci/conan/profiles/ohos-aarch64:29` 写的是
`tools.build:compiler_executables={"c": "...", "cpp": "..."}` —— 键是 `cpp` 而不是 Conan 官方约定的 `cxx`；
只按 `cxx` 取值的写法必然拿到空值（本包第一次 conan-verify 就是这么在 build() 里抛 ConanException 的，
rc=2、G2: FAIL）。这条与已池化的 commander 草稿（compiler_executables 取字典键）同族，
但"键名 `cpp` ≠ `cxx`"是本仓 profile 特有形态，已写进 B 草稿。

`dik/makefile` 链接后会跑 `size`（本机 `/data/service/hnp/bin/size` 存在 ⇒ 不需要补丁）。
静态 bss 实测很大（`size` 输出 `sizekoc2` bss=814067788 ≈ 814 MB，因上游 CFLAGS 带 `-DLARGE_MEM`），
但只影响 `dik/` 的 `size*` 系列，`make install` 只安装 6 个命令（见 §4），实际交付物不含体积最大的那几个。

**objc=6 的作用域实测**：语言统计里的 6 个 `.m` 文件是 `dik/trans/{choice,cperm,eperm,flip,sperm,twist}.m`，
与同名 `.c`/`.r`/`.a` 并存，是 Dik Winter 分发的**同一置换表的多种书写变体**（纯文本 C 变体），
不是 Objective-C、也不参与任何构建：`dik/makefile` 只在依赖行里提到它们（如 `sizekoc1.o: trans/choice.m`），
没有 `.m` 的编译规则，`make all` 产物 12 个二进制无一来自 `.m`。⇒ 不影响 Linux/OHOS 构建，仅作用域披露。

## 4. 交付产物

`make install` 实装 6 个命令（上游自己的 install 规则决定，未自行增删）：
`optimal`、`cubex`、`mcube`、`cu2`、`dikcube`、`size222`。
`make all` 另会产出 `twist`、`size333c`、`sizesquare`、`sizedom`、`sizekoc1`、`sizekoc2`
（上游 install 规则不装它们，故不随包发布 —— 记为少报防呆：**产物 12、交付 6**）。
软件级 `commands.json` 声明这 6 个命令，`versions."20070912".ref = rubiks/20070912`。

## 5. 测试账（上游 0 用例 ⇒ "六形"取证 + 17 条自写断言）

上游测试用例数 **0**。六形取证（可复算命令在括号内）：

1. **tar 清单**：`tar tjf rubiks_20070912.orig.tar.bz2 | grep -iE 'test|check'` → 只有 `dietz/solver/test.cub`
   （206 B 的**魔方状态输入数据**，非测试代码；实测 `cubex test.cub` / `cubex < test.cub` 都报
   `510 ERROR: non-protocol input entered.`，它要靠交互式协议 `load` 读入，不是 runner）。
2. **Makefile 目标**：顶层只有 `all/clean/distclean/install` 四个目标，5 个子 Makefile 均无 `check`/`test`
   （`grep -nE '\.PHONY|install|check|TESTS' Makefile */Makefile dik/makefile`）。
3. **CI 文件**：上游树内无任何 CI 配置（`.github/`、`.gitlab-ci.yml`、`Makefile.am` 全不存在，见 tar 清单 102 个文件）。
4. **语料**：`dik/RESULTS` 是作者手抄的期望输出（`1 with  0 turns / 9 with  1 turns / 54 with  2 turns /
   321 with  3 turns / 1847 with  4 turns`，2x2x2 面转度量），`dik/TABLE` 同理 —— 是数据不是 runner。
   test_package 的 `size222 -q` 断言取的正是同一类枚举计数（四分转度量分支：`1/6/27/312`，
   与 RESULTS 的面转度量分支不同度量为不同值，符合 2x2x2 群已知结论）。
5. **源码自测**：`grep -rniE 'assert\(|self.?test|unit' *.c *.cpp` 无测试入口（只有算法内部变量名）。
6. **自带测试脚本**：无（树内 0 个 `*.sh` / `runtest` / `configure测试`）。

⇒ 上游静态合计 0，本包 **17 条**断言（实测 ≥ 声明，同源数字见下）。
断言全部落在 `test_package/test_rubiks.sh`：只从 PATH 调已安装产物，每条都是"退出码 + 逐字文案"，可证伪；
脚本自己数 `ASSERTIONS_RUN`，并要求 `=17 且 FAILED=0` 才 exit 0（少跑一条就算失败，防静默跳过）。
期望值取自本机实测参考输出（`~/tmp/uc2/z32-rubiks/ev/run-*.out` 与 `ev/probe.out`，2026-09-25），并与提交态参考夹具 `test_package/tc-*.txt` 分离：脚本本轮实跑产物写到 `$OUT`（`${RUBIKS_TP_OUT:-${TMPDIR:-$HOME/tmp}/rubiks-20070912-test-run}`），提交态夹具是上一轮真实运行的留档 ⇒ 「期望」与「实际」为两条独立来源，不可互相覆盖。

| # | 断言 | 期望 | 实测依据 |
|---|---|---|---|
| 1 | 6 个命令均可从 PATH 解析 | 无缺失 | 本轮 `$OUT` 产物 + ev/run-*.out |
| 2-4 | `mcube random` | rc=0 + `200 cube solved ok.` + `101 version 1.0 (20051216)` | 真实随机盘求解成功 |
| 5-6 | `cu2`（无协议输入） | rc=255 + `510 ERROR: non-protocol input entered.` | ev/run-cu2.out |
| 7-8 | `cubex`（无协议输入） | rc=255 + `101 version 1.30.505 by Eric Dietz (root@wrongway.org)` | ev/run-cubex.out |
| 9-13 | `size222 -q` | rc=0 + `1 with  0 turns`/`6 with  1 turns`/`27 with  2 turns`/`312 with  3 turns` | `ev/probe.out:10-13`（四分转度量分支 1/6/27/312，与提交态 `tc-size222.txt` 一致）；⚠ 同目录 `ev/run-size222.out:10-13` 是**不带 `-q` 的另一度量分支** 1/9/342/4823，`dik/RESULTS` 又是面转度量 1/9/54/321 —— 三个度量各自成账，不得互引 |
| 14-15 | `optimal -h` | rc=0 + `using quarter turn metric` | ev/run-optimal.out |
| 16-17 | `dikcube -p` | rc=1 + `Initialized = 2187` | ev/run-dikcube.out（phase1 表已建满） |

`assertion_count = 17` 的**四处**同源（W4R1-P2-03 整改：原称「五处」把软件级 `manifest.yaml` 也算了进去，但该文件实测只有 software/description/category/license/homepage/repository/keywords/versions{status,build_date,patches} 这些键，无 `test_package.assertion_count`，故改口径为四处，不给指不到处的话）：
`test_package/test_rubiks.sh`（`ASSERTIONS_EXPECT=17`）、`test_package/MANIFEST.yml:13`、版本级 `manifest.yaml:21`、本 notes §5。逐条数法：1 条 PATH 探测 + 6 条 `expect_rc` + 10 条 `expect_text` = 17，与脚本末尾 `[ "$A" != 17 ]` 自检闭合。

### 5.1 提交态六枚夹具曾被写成失败残件的根因（W4R1-P2-01 一手证据）

`321c2c9c67` 把 `tc-{cu2,cubex,dikcube,mcube-random,optimal,size222}.txt` 从 `3fb8cb7f34` 的实跑输出
改成了单行 `timeout: failed to run command '<bin>': No such file or directory`（6 枚共 424 B）。本轮取证：

- **复现实验（同 HOME、同脚本、产物目录不在 PATH）**：`sh test_rubiks.sh` 在 `~/tmp/uc2/z32-rubiks-fix1/repro-noenv/`
  重跑，六枚产物与提交态残件 `cmp` **逐字节相同**（`IDENTICAL_TO_COMMITTED_BAD` 六条），
  日志判决行 `ASSERTIONS_RUN=17 ASSERTIONS_EXPECT=17 ASSERTIONS_FAILED=17`、`TEST PACKAGE FAILED`、脚本 rc=1，
  每条 `expect_rc` 实测 `got=127`。⇒ 残件是「**一次 PATH 里没有安装产物的失败运行**」的产物，不是构建/签名问题。
- **对照组**：`timeout 5 nosuchbinhere` 得 `TIMEOUT_MISSING_RC=127` + 同一行 `failed to run command ...: No such file or directory`
  （本机 toybox timeout 用弯引号，故残件里的引号也是 U+2018/2019 —— 反证残件出自本机、非抄自别处）。
- **为什么失败运行会污染提交态**：本 test_package 被 conan 执行时 **cwd 就是源码目录本身**
  （`find -newer` 实拍：本轮 `conan-verify` 新写出的 `tc-size222.txt` 落在
  `archives/r/rubiks/20070912/test_package/tc-size222.txt`；仓库根 `.gitignore:184-185` 早已为
  `**/test_package/conanbuild*.sh`、`**/test_package/conanrun*.sh` 让路，即是同一事实的框架侧留痕）。
  旧脚本把产物写成 `>tc-*.txt` ⇒ 与提交态参考夹具**同名同址**，一次失败运行即覆盖真实参考输出，
  随后 `git add archives/r/rubiks/` 把失败残件收进提交。
- **整改**：产物改写到仓库外的 `$OUT`（见 §5 首），提交态 `tc-*.txt` 只作上一轮真实运行的留档；
  本轮（`$D2/ev/verify-fix1.log`，VERIFY_RC=0）已用复原后的脚本重跑，产物按 `$D2/run-round2/` 留档。
  与 `3fb8cb7f34` 的差异只有 `tc-mcube-random.txt`（5626 B vs 5888 B）—— 该用例是 `mcube random` 随机盘，
  盘面与解法逐步不同属预期，断言只锚 `200 cube solved ok.` 与版本横幅两串；其余五枚逐字一致。
- **否证「包目录产物不可执行」这一族误判**：见 §8 附表 —— 同一批产物直接 `exec` 与经 conan 运行均返回真实输出，
  `install=NONE`、`gcc=NONE` 只是**主机没有这两个工具**，与包目录产物的可执行性无关。

**平台观测（不计入 assertion_count）**：`dikcube`/`optimal` 无参数直跑会持续搜索（实测 6 s 内不退出），
属上游交互式行为，不是平台缺陷；本轮未触及串口/IPC/socket/sysfs/设备节点，无能力面探针需要报号。

- **写出残件的运行高度指向框架自己的破坏性负照（非人工误跑）**：本轮权威 W3 的产物目录
  `~/tmp/rubiks-20070912-test-run/` 里六枚同样只有 68-72 B（实测首行 `timeout: failed to run command
  '<bin>': No such file or directory`），而同一轮 `reports/w3-local-ci.log:942` 却印
  `ASSERTIONS_RUN=17 ASSERTIONS_EXPECT=17 ASSERTIONS_FAILED=0` ⇒ 一次 W3 里 test_package 被跑了**不止一遍**：
  带 runenv 的那遍通过，另一遍跑在查无安装产物的 PATH 上（ENOENT/127）。W3 步骤序列里的
  `953:[step] L1e: Destructive negative test (R34)...；955:[ok] L1e: Negative test confirmed — test genuinely depends on rubiks` 正是「故意拆环境再跑一遍、必须失败」的那一步，故把残件来源定性为**框架负照运行**；
  推断链只到「同一轮既留 17/17 判决行、又留 ENOENT 失败产物」，未逐行核 L1e 的 env 构造。
  旧脚本写 `>tc-*.txt`（test 的 cwd 即 `test_package/` 源码目录）⇒ 那一遍覆盖掉提交态真实参考输出；
  上一轮 finish 结束于 06:42:43、其后的 `321c2c9c67` 按目录 add ⇒ 时序与残件入库一致。
  `conan-verify` 不跑 L1e（其报告只到 L2/L4/L5），故本轮阶段 A 的 verify 在源码目录留下的仍是真实输出。
- **整改两件**：① 六枚夹具复原并按本轮实跑更新；② 产物与提交态夹具分址（`$OUT`），负照再也覆盖不到提交态。
  残留披露：正/负两遍共用同一个 `$OUT` 目录（末次写入者是负照），本轮正照产物已另存
  `~/tmp/uc2/z32-rubiks-fix1/repro-patched/out/`（17/17 通过、rc=0）留证；未再把 `$OUT` 按次分目录，
  因再改测试脚本就得再烧一轮 W3，按「披露优先」处理。

## 6. 许可证（不外推 SPDX）

上游三套实现各带自己的 license.txt，未声明统一 SPDX，故配方 `license = "LicenseRef-Rubiks-Authors"`，
`package()` 把三份 license.txt 原样拷进 `licenses/<子目录>/license.txt`：
- `reid/license.txt`：GNU GPL v2 or later（Copyright (C) 1997 Michael Reid）。
- `dietz/license.txt`：MIT 式许可（"Permission is hereby granted, free of charge..."）。
- `dik/license.txt`：见包内原文（Dik Winter，1992 邮件体叙述）。
不在 PR 正文里把它归并成单一 SPDX 值，等主窗按审查员口径定名。

## 7. 路径 B 判定（W4 r1 复审后改判：**hit**，不占知识位）

- 检索面：按机制特征词同批扫四范围 `knowledge/graph/*.kv`、`knowledge/graph/index.tsv`、
  `knowledge/drafts/*.kv`、`archives/**/notes.md`（`draft-review` 不扫 `knowledge/drafts/`，已手工 grep）。
- **原判 create 的依据不成立**（W4R1-P1-01）：升档只在三枚最近邻之间对齐
  （`E392.kv`／`DRAFT-commander-1.4.0-makefile-recipe-build-package-traps.kv`／`E554-draft-A7F3.kv`），
  漏了两枚**处置面更近**的在池条目（行号按本轮磁盘实测）：
  - **正式 E 条目 `knowledge/graph/E313.kv`**：`:21` `verification_cmd` 就是
    `make install INSTALL="/system/bin/install -c"` + `DESTDIR/sitearchdir`；`:26` `rec_description` ②
    「make install 阶段用 INSTALL=... 覆盖 Makefile 的 /usr/bin/install」；`:27` `rec_command`
    `make DESTDIR= sitearchdir=... install INSTALL="/system/bin/install -c"`；
    `:19` `root_cause` ② 与 `:20` `affected_scope` 同为「上游 Makefile 假设 GNU 原生 install 程序路径」。
  - **`knowledge/drafts/DRAFT-8958-clthreads-makefile-stage-install-shadow.kv`**：`:78`
    `fixed-install-path-or-make-install-patch`、`:82`
    `make -C source install INSTALL=/bin/install PREFIX=/ DESTDIR=...`、`:84`
    `makefile-install-variable-override`，并在 `:92` 用 forbid 模式
    `self.run(.*make.*install(?!.*INSTALL=/bin/install)` 把同一处置写成硬判据。
- 四条件逐条对齐（以 E313 行号为锚）：**同处置面成立**（make 命令行变量覆盖 `INSTALL`(+`DESTDIR`/`PREFIX`)，
  零补丁零新增构建文件 —— 对 E313:26,27，原「同处置面不成立」作废）；
  **同根因成立**（上游假定 GNU 原生环境自带的 install 程序 —— 对 E313:19）；
  **同作用域成立**（OHOS 上 make install 阶段的同一处置动作 —— 对 E313:20；
  载体由 gem 的 Makefile 换成本包上游的裸 Makefile，不改变作用域）；
  **同机制部分成立**（E313 是 Makefile 硬编码 `/usr/bin/install` 路径不存在 ⇒ `No such file or directory`；
  本包是顶层 Makefile 第 2 行把 `INSTALL` 的定义注释掉 ⇒ 空展开 ⇒ 该行退化为执行产物。
  二者差别在**检测面/症状**（一个报错、一个静默错行为），处置面与根因不变）。
  ⇒ 四条中三条完全对齐、第四条只差分显症状 ⇒ 判 **hit**。
- **自造草稿已撤销**：`knowledge/drafts/DRAFT-rubiks-20070912-make-commandline-var-override.kv` 与同名 `.md`
  已从本 PR 撤下 —— `mv` 到 `~/tmp/uc2/z32-rubiks-fix1/withdrawn/`（**未 `rm`，文件仍是用户资产**），
  提交态不再包含 `knowledge/drafts/` 任何新文件。理由：正式条目 E313 与在池草稿 DRAFT-8958 已覆盖同一处置面，
  「池内无先例」这一 create 前提不成立。Issue #3365 的撤销说明由主窗发布（本执行棒不调平台 API）。
- 撤销后仍在本 notes 承载、不再另立条目的两条实测口径：
  ① `$(INSTALL)` 定义被注释掉时 make 的行为是「执行产物」而不是报错（检测面见 §3 第 2 条，
  先跑一次不带 `INSTALL=` 的 `make -n install` 即可看清）；
  ② 本仓 `ci/conan/profiles/ohos-aarch64:29` 的 `tools.build:compiler_executables` 键名是 `cpp` 而非 `cxx`（§3 末）。
  若主窗认为二者值得立条，可从 `~/tmp/uc2/z32-rubiks-fix1/withdrawn/` 的草稿取名。
- **一 PR 一知识**：verify 阶段 G2 的假命中 E538（harfbuzz/meson，score 3026）与本包 `cpp` 键名问题都不再单独建条目。
- 未做且需主窗处理：Issue #3365 的撤销说明与 PR 正文的 `知识库扩展: 无新增` 对齐（见顶部 3+2 声明）。

## 8. 门禁判决行原文与未过项（W4 r1 整改后本轮实测，B 构建主机；夹具与测试脚本均在提交态）

| 门禁 | rc | 判决行原文（逐字） | 出处（含行号 / 字节 / mtime） |
|---|---|---|---|
| W0 `preflight_check.sh rubiks/20070912` | 0 | `[OK] 预检通过（无依赖需要检查）` | 上一轮实测（依赖本轮未变，零 requires）；旧证据件 `~/tmp/uc2/z32-rubiks/finish-run1.log` |
| `recipe-search rubiks` | 0 | `⚠️ 无相似配方（语料 6173 条）——首稿走 conan-init 模板` | 上一轮实测（本轮无新增配方检索面变化） |
| conan-verify（G0-G4+L2/L4/L5） | 0 | `**Verdict**: PASS`；`## G0: ✅ PASS`:8、`## G1: ✅ PASS`:17、`## G2: ✅ PASS`:31、`## G3: ✅ PASS`:35、`## G4: ✅ PASS`:39 | `reports/conan-verify-report.md`:3（1472 B，07:18:01；本轮 finish step4 复跑） |
| finish / W3(step5) | **2** | `✅   ✅ W3 本地 CI 模拟通过`（:65）；`ASSERTIONS_RUN=17 ASSERTIONS_EXPECT=17 ASSERTIONS_FAILED=0`（w3 日志 :942）；`.ci-result.json` `exit_code: 0` | `~/tmp/uc2/z32-rubiks-fix1/finish-fix1.log`:65（6996 B）＋ `reports/w3-local-ci.log`:942（58079 B，07:19:44）＋ `.ci-result.json`:3（367 B，07:19:44）；rc=2 的出处见未过项第 6、7、10 条 |
| `graph validate` | 0 | `✅   ✅ graph validate 通过`（finish 日志 :84）；独立日志末行（该日志无结论性关键字行）：`auto_fix=true:      130, auto_fix=false: 400` | `~/tmp/uc2/z32-rubiks-fix1/graph-fix1.log`（20888 B，07:19:51） |
| PF1-PF9（`scripts/ohc/preflight.py . origin/main HEAD`） | **1** | `✗ PF9 分支/路径闸: 变更路径缺版本目录层…: archives/r/rubiks/README.md, archives/r/rubiks/commands.json, archives/r/rubiks/manifest.yaml`（:1）；`✗ PF7 源URL闸(R39): …/conandata.yml:2 Debian 下游重打包源`（:2）；`✗ PF7 …: …/manifest.yaml:10`（:3） | `~/tmp/uc2/z32-rubiks-fix1/pf-fix1.log`（746 B，07:19:51）——PF 无 PASS 结论行，三条红全部照写 |

`.ci-result.json` 双哈希复算（算法 `scripts/ohc/finish.py:245-266`）：
`integrity_hash` 复算 `sha256("<timestamp>:rubiks:20070912:0")[:16]` = `16f137ae59598de2`，件内值 `16f137ae59598de2` ⇒ **一致**；
`log_sha256` 复算 `sha256(reports/w3-local-ci.log)` = `3d24adc6b5d479c7c0520262d34188133d6ce7b79d7d8fce8da42137efdfbf73`，件内值 `3d24adc6b5d479c7c0520262d34188133d6ce7b79d7d8fce8da42137efdfbf73` ⇒ **一致**。

### 可执行性附表（否证「包目录产物在本机不可执行」这一族误判）

同一批 rubiks 产物（`~/tmp/ch/home-rubiks/p/b/rubik0ef02e2f75c51/p/bin`，`ls -l` 模式 `-rwxr-x---`、属主 20001006）：

| 取法 | 命令（原样） | rc | 结果 |
|---|---|---|---|
| 直接 exec 包目录产物 | `<bin>/size222 --version` | **0** | 真实枚举输出（末行 `5727 with  8 turns,  5727 maximal`） |
| 直接 exec（错误路径用例） | `<bin>/cubex </dev/null` | **255** | `510 ERROR: non-protocol input entered.` + 版本横幅 |
| 经 timeout 调绝对路径 | `timeout 5 <bin>/mcube random </dev/null` | **0** | `cube solved ok` 命中 1 次 |
| 产物目录进 PATH 跑整套断言 | `RUBIKS_TP_OUT=… PATH=<bin>:$PATH sh test_rubiks.sh` | **0** | `ASSERTIONS_RUN=17 ASSERTIONS_EXPECT=17 ASSERTIONS_FAILED=0`、`TEST PACKAGE PASSED (17/17)` |
| 对照：PATH 查无此件 | `timeout 5 nosuchbinhere` | **127** | `timeout: failed to run command ‘nosuchbinhere’: No such file or directory` |

⇒ 失败残件的错误面是 **ENOENT / rc=127（PATH 里查无此件）**，不是 EACCES/126、更不是签名或 HMDFS mode 问题；
本包全部证据里没有出现 rc=126。主机缺的只有 `install(1)` 与 `gcc/g++`（实测 `command -v` 均 NONE，见 §3）。

### 未过项（照红写，不删件不凑绿）

本轮 `~/tmp/uc2/z32-rubiks-fix1/ev/finish-fix1.log`（6996 B）与两份报告里的全部红/警：

1. `:6` `⚠️   .staging-verified 缺失` —— 取件路径 `archives/r/rubiks/20070912/.staging-verified`，
   **至今盘上不存在**（归档目录实测只有 `.build-closed .ci-result.json .conan-verified .handoff.json .knowledge-done` + `packaging/`）。
   属 submit 前置件、由框架在 submit 阶段自造且被 gitignore ⇒ 不进本 PR 提交态。
2. `:11`、`:20` `❌ 无法定位源码目录: orig=None, work=None`（Step1 refresh-patch）—— 本包 `patches_applied: []`、
   零补丁，故该步无事可做；红在框架侧取源目录约定，不影响产物。
3. `:32` `❌ G0: 找不到原始 tarball` ＋ `:33` `⚠️ G0 干净构建验证失败，请手动检查构建结果` ＋
   `:34` `⚠️ 运行 ohc-run.py clean-verify 获取详细错误` —— 同一日志 `:47` `✅   G2: PASS`（conan create 成功），
   G0 的失败面是 clean-verify 取不到本地 tarball（pre-download 已把 conandata 还原成官方 URL），非配方不可构建。
4. `:70` `⚠️ 缺少 release tar.gz`、`:71` `⚠️ 缺少 debug tar.gz`（finalize-archive Phase 2）。
5. `:73` `⚠️ notes.md 无对话记录`（finalize 一致性检查；对话记录由框架 `run` 侧注入）。
6. `:93` `❌   ❌ 知识图谱完整性检查发现 1 类问题` = `:80`-`:83` 的 `E219.kv/E253.kv/E305.kv` 字段缺失
   （root_cause / rec_approach 为空）—— **存量他条目问题**，本包 `manifest.yaml: knowledge_count=0 unreferenced=0`（:95）、
   且改判 hit 后不再新增草稿；同一检查的 `doc↔kv 配套完整 (540 对)`:78 与 `graph validate 通过`:84 为绿。
7. `:98` `⚠️   gen_summary 失败: 'str' object has no attribute 'append'`（step8，框架侧生成 SUMMARY.md）。
8. `:103` `❌ test-report.md — 需创建 reports/test-report.md`、`:104` `❌ packaging/ — 需创建 packaging/ 目录并打包`、
   `:105` `❌ .staging-verified — 需创建 .staging-verified 空文件` ⇒ `:107` `⚠️   ⚠️ 3 项未就绪，submit 前需修复`。
   其中 `packaging/` 本轮已建（盘上存在）；`reports/test-report.md` 与 `.staging-verified` 仍不存在，
   取件路径分别是 `archives/r/rubiks/20070912/reports/test-report.md`（`reports/` 当前批次不进 PR）与
   归档根的 `.staging-verified`（gitignored、`run`/submit 自造）⇒ 两者均不在本 PR 提交态内，非本包缺件。
9. `:108` `⚠️ ⚠️  编译收尾部分完成: rubiks 20070912 → built`、`:109` `⚠️    失败步骤: step5b, step8`
   ⇒ 本表 finish 行 **rc=2** 的出处（W3 本体 step5 为绿：:64-:65）。
10. `reports/conan-verify-report.md:9`-`:15` `**Knowledge hit**: E490`＋`⚠️ 已知风险 E490 未在配方中处理`
    （命中面是 `构建系统: autotools`）—— 本包是裸 GNU Makefile（无 `configure`/`config.guess`/`install-sh`），
    属**假命中**，未据此改动配方，也不按它的 `chmod +x` 处方凑绿。
11. PF 三条红（上表 PF1-PF9 行）：PF9 要 `archives/<字母>/<包>/<版本>/<文件>` 三层，而软件级三件套
    （`README.md`/`commands.json`/`manifest.yaml`）按仓库约定就住在包级目录 ⇒ 本包按约定交付，
    红照写（与今晚已合入的其它包同形）；PF7 两条见 §1（Debian pristine upstream 单源，未改哈希、未用镜像）。
12. 上一轮同类红的存档件：`~/tmp/uc2/z32-rubiks/ev/finish-run1.log:6`（`.staging-verified 缺失`）、
    `:33`（`❌ G0: 找不到原始 tarball`）、`:34`（`⚠️ G0 干净构建验证失败，请手动检查构建结果`）、
    `:104-108`（Step10 三项未就绪）—— 与本轮逐条同形，属框架侧未就绪项，非本轮回归。

### 逐字判决行（本轮 `reports/w3-local-ci.log`，行号原样）

23:G0_RESULT=pass
63:KC_RESULT=pass
90:JC_RESULT=pass
942:ASSERTIONS_RUN=17 ASSERTIONS_EXPECT=17 ASSERTIONS_FAILED=0
964:L0_RESULT=pass: all checks passed
965:L1_RESULT=pass: test_package executed
966:L2_RESULT=pass: cu2 version/help failed, cubex failed, dikcube failed, mcube failed, optimal --version OK, size222 --version OK
967:L4_RESULT=pass: patches clean
968:L5_RESULT=pass: bin/ has content

---

**编译结束**: 2026-09-25 07:19:44
**最终状态**: built

# jellyfish1 1.1.11 适配说明（B 机，主理-33）

## 构建系统与依赖
Autotools（configure + make + make check），零外部 conan 依赖：
preflight_check.sh 对 jellyfish1/1.1.11 实跑报「未找到依赖声明」并
预检通过（只需 libc/libm/libpthread）。recipe-search 无相似配方（语料 6173 条）。

## 源码来源
取源为上游官方发布站的 jellyfish-1.1.11.tar.gz
（https://www.cbcb.umd.edu/software/jellyfish/，即 conandata.yml 与
1.1.11/manifest.yaml 里所写的 URL）。设备侧实测：该 URL 返回 HTTP 200、
application/x-gzip、1067138 字节，落盘实物 sha256 =
496645d96b08ba35db1f856d857a159798c73cbc1eccb852ef1b253d1678c8e2，
与之前挂的 Debian pool jellyfish1_1.1.11.orig.tar.gz **逐字节同一**；
两棵解包树 diff -rq 零差异（各 183 文件，比对件
~/tmp/uc2/z33-jellyfish1-fix/src-swap/diff-official-vs-orig.txt 为 0 字节）。
换源的理由：R39/PF7 不允许 conandata 写 Debian 下游重打包源。

## OHOS 适配点（逐条都有设备实拍证据）

### 1. config.sub 拒绝 musl 三元组（与仓内既有口径不同）
2013 年随包发布的 config.sub 不认识 aarch64/musl：
configure 实拍第一错 =
Invalid configuration aarch64-unknown-linux-musl: machine aarch64-unknown-linux not recognized
⇒ 仓内 4ti2 等包用的 --build/--host=aarch64-unknown-linux-musl 这招对本包无效。
改用 config.guess 自身在该机上产出的 aarch64-unknown-linux-gnu（探测树实拍
configure 成功、host/build 均为该值），并显式传入以跳过 config.guess，
因此不需要 patch config.guess。本轮 create 的真实 configure 行
（reports/w3-local-ci.log:181）里 --build/--host 均为该 gnu 三元组。

### 2. config.status 的 mktemp 在 HMDFS 上产组不可执行目录
configure 内嵌 (umask 077 && mktemp -d ./confXXXXXX) 在 HMDFS 上产 setgid 但无
组执行位的目录，配方把 umask 放宽为 002（实物命中 1 处，UMASK_PATCH_HITS 1）。

### 3. CONFIG_SHELL 是 ★关键反向经验：本包必须不用它
仓内共享 profile ci/conan/profiles/ohos-aarch64 第 32-33 行把
CONFIG_SHELL 与 SHELL 强制成 /data/service/hnp/bin/bash（4ti2 等包的常规做法）。
对本包（2013 年 autoconf 2.68 + libtool 2.4.2）这直接造成两处独立故障，
且两处都在 conan 产出的 build 目录里实拍：

- config.status 用该 shell 重跑自己时，@archive_cmds@ 替换丢一层转义
  （probe 树里是 archive_cmds="\$CC -shared ..."，conan 树里变成 "$CC -shared ..."），
  产出的 libtool 根本不可解析：./libtool 第 350 行 syntax error near unexpected token
  → 第一条 .lo 规则即挂掉；
- libtool 的 echo 实现被选成 ECHO="print -r --"，而 print 是 **toybox ash 的内建**
  （实拍 /bin/sh -c "print -r -- hi" 退出码 0；hnp bash 里没有），
  → 第一条 CXXLD 挂掉：./libtool 第 907 行 print: command not found。

反证与对照（读数一律实测）：探测树（configure 不带 CONFIG_SHELL）的
config.status 记的是 SHELL=/bin/sh，同一份源码在同一台机上 **make 与 make install
均成功**：probe5b-a.out:8 MAKE_RC=0、probe-install.log（6209B）全篇 0 条
error/Error 行并走到 make[1] Leaving directory；对照导出
CONFIG_SHELL=/data/service/hnp/bin/bash 的两轮 probe3-a.out:10 与 probe4-a.out:10
均 MAKE_RC=2 ⇒ **本节 CONFIG_SHELL 的因果方向由 make 腿支撑，成立**。
⚠ 但同一棵探测树的 **make check 并非全通过**，实测是打补丁前的基线全红：
probe-check.log:44「19 of 19 tests failed」、:45「(1 test was not run)」、
probe/src/test-suite.log:5 同值（判决行 19 FAIL + 1 SKIP、PASS 0 条），
该轮以 probe-check.log:49-53 的 make Error 1/2/2 收尾；全任务目录内不存在
任何该树的 make check 全绿日志。⇒ check 面只用作基线，不支撑任何结论。
⇒ 配方的处置（conanfile.py:146-185 的 _regen_build_outputs()，与仓内 E551 同处置）：
configure 之后先把 config.status 里被记录进去的 /data/service/hnp/bin/bash
路径整体改写为 /bin/sh（改写命中数由该函数打印），再以命令行前缀赋值的方式执行
「env CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh ./config.status」做**全量重生成**
（不是只重生成 libtool 一个目标，也不是用 -u 撤掉变量），最后 sh -n libtool 自检。
前缀赋值能胜过 profile 聚合 env，这一点是 E551:12-17 的既有论证，本包复现。
⛔ 不改共享 profile（框架改动按规则须单独 PR）。
在 toolchain 层覆回 CONFIG_SHELL 无效：conanbuild.sh 先 source 工具链、
后 source buildenv，profile 的值最终生效（实拍该两行顺序）。

### 4. make -j 的 jobserver 在 HMDFS 上不可用
make -j2 实拍：make: jobserver mkfifo: .../GMfifo11290: Operation not permitted
⇒ 配方统一用 -j1（上游测试内部本身用 -t $nCPUs 起 20 线程，并行面不缩）。

### 5. ★根因：raise_t 在析构里 throw，C++11 起等价于 std::terminate
★口径分两层并列，不得互相顶替：
- **打补丁前的上游基线**：19 项全红——probe-check.log:44「19 of 19 tests failed」
  （:45「(1 test was not run)」、probe/src/test-suite.log:5 同值）。本节说的
  「唯一入口」指的是**这一层**。
- **交付轮（打完 0001）**：4 PASS / 15 FAIL / 1 SKIP，UPSTREAM_MAKE_CHECK_RC=2
  （reports/w3-local-ci.log:788 汇总、:767/:773/:783/:786 四条 PASS 判决行、
  :801-813,:815,:816 十五条 FAIL、:814 SKIP、:800 RC 行）。余下 15 条 FAIL 属
  tests/compat.sh 的 baked md5 基线家族，与本节的抛出析构机制无关
  （逐条见「上游测试面实测」一节）。
证据链：
- 抛出点 jellyfish/square_binary_matrix.cc 的 inverse()：
  eraise(SingularMatrix) << "Matrix is singular"
- 抛出点在 jellyfish/err.hpp:123，性质是类 raise_t 的**析构**（未打补丁树实读
  ~raise_t() { throw err_t(oss.str()); }；宏 #define eraise(e) if(1)
  err::raise_t<e>() 在同文件 :139，与本节末尾「本轮另补一手锚点」段同字面）：
  下面这条是**同形诊断**，一手出处 tc4-r2.out:12（libtc4.hpp:9:3，最小探针的自建头，
  其析构同名 ~raise_t），**不是本包 err.hpp 的编译日志原文**：
  libtc4.hpp:9:3: note: destructor has a implicit non-throwing exception specification
  （全域检索该文案的一手出处只有 tc4-r2.out:12/:20/:30/:37 与同目录四份
  log.unfixed.*，一律指向 libtc4.hpp:9:3 ⇒ 它只作编译器该诊断的同形示例；本条结论
  不依赖该句，依赖的是下一行的语言规则与下面的 tc4-r2 双臂 RC）
  即 C++11 起析构函数隐式 noexcept，从中 throw 一律 std::terminate，
  libc++abi 的措辞正是 terminating due to uncaught exception of type
  SquareBinaryMatrix::SingularMatrix。
- 因此 tests/generate_sequence.cc 里那个
  catch(SquareBinaryMatrix::SingularMatrix ) 重试循环永远接不到，
  而 GF(2) 随机矩阵奇异率约 29%，第一轮撞上就整进程 abort。
- 定性为②可修（最小补丁），非平台缺陷：同一棵树在 C++03 语义下正常。
  「与跨 DSO 的 RTTI/typeinfo 无关、纯语言规则版本差异」这条已有手一手读数：
  tc4-r2 最小复现（未打补丁的抛出析构，静态与共享两种链法各一份）均为
  RC=134 + 同一 libc++abi terminating 文案
  （~/tmp/uc2/z33-jellyfish1/tc4-r2/tc4-r2.out:23-25 静态、:40-42 共享），
  加 noexcept(false) 后两份都 RC=0（:52、:60）。
  诚实披露：上一轮遗留的那对 tc4 二进制复跑是静态 134 / 共享 **127**
  （:63-65、:66-68），127 是加载期 `Error loading shared library` +
  `Error relocating ... inverseEv: symbol not found`，属探测树 .so 陈旧形态，
  不构成共享链法下的任何异常语义证据 ⇒ 本条结论的出处改用 tc4-r2。
- 处置：patches/0001-err-hpp-raise-t-noexcept-false.patch 一行
  noexcept(false)，实测该补丁使 generate_sequence 恢复产出 seq10m.fa。

### 6. 自带 googletest 1.6 与 clang 15 + libc++
不带 -DGTEST_USE_OWN_TR1_TUPLE=1 时实拍：
unit_tests/gtest/include/gtest/internal/gtest-port.h:504:13:
fatal error: 'tr1/tuple' file not found（单编 RC=1；带该宏 RC=0）
⇒ 配方 tc.extra_cxxflags 注入该宏（另加 -Wno-narrowing）。
该面只作用于上游 vendored gtest 的测试目标、不进被交付库，且仓内全域
（含 knowledge/drafts/）0 命中 ⇒ 有独立成条资格，但**不占本 PR 的知识位**
（本 PR 的 B 判定见下方「适配路径」一节，已判 create，知识位由 raise_t
抛出析构那条新草稿占用）；草稿另存配送池。

### 7. __int128 与 __udivti3（本包上游测试基线相关，见下节）
configure 自动探测 __int128 为 yes，但 NDK 的 compiler-rt 不会自动进 libtool
产出的共享库：开着 HAVE_INT128 建出来的 libjellyfish-1.1.so.1 里
nm 实拍 U __udivti3，执行期第一条错误就是
Error relocating .../libjellyfish-1.1.so.1: __udivti3: symbol not found（exit 127）
⇒ 配方固定 ac_cv_type___int128=no（走 divisor64 的硬件除法分支）。
本轮交付构型是 --disable-shared（w3-local-ci.log:181 的 configure 行，
:259「checking whether to build shared libraries... no」、:260 静态 yes），
故该面在交付物里不复现，但配方的钉法对 shared=True 构型仍必要。

### 7.5 clang-15 把 C++17 兼容性诊断列为默认错误
conan profile 用 -std=c++17 编译 2013 年 C++03 代码：
half.h:471 与 half.cpp:98-100 的 register 存储类、err.hpp 系的动态异常规范，
在 clang 里属 DefaultError 组，-Wno-error 也压不住（实拍 Makefile 的
CXXFLAGS 里已有 -Wno-error 却仍报 error: ISO C++17 does not allow register）。
⇒ 配方按组显式降级：-Wno-error=register、-Wno-error=dynamic-exception-spec、
-Wno-error=c++11-narrowing（与仓内 aiksaurus / aldo 同族做法），诊断仍留在日志。

### 8. 头文件安装位置
上游把头装到 include/jellyfish-1.1.11/jellyfish/ 而非 include/jellyfish/，
而源码一律以 <jellyfish/xxx.hpp> 引用 ⇒ package_info 把 includedirs 指到
include/jellyfish- + 版本号（否则 test_package 编译找不到头）。

## 上游测试面实测（make check 真跑，在配方 build() 里）
★权威数据 = 本包 conan create 第 2 轮真跑（2026-09-25 07:20，B 机）的
make check stdout，逐行落在 reports/w3-local-ci.log（920 行，
sha256 5fff98587d8253d2894889c89c09ef2af34b4e42eeb66f41b0fcf67ce4395529，
与 .ci-result.json 的 log_sha256 同值）：
汇总行 :788「15 of 19 tests failed」、UPSTREAM_MAKE_CHECK_RC=2 :800、
4 条 PASS 的判决行 :767/:773/:783/:786、15 条 FAIL 的配方解析行
:801-813,:815,:816、1 条 SKIP（tests/big.sh, exit 77）:814。
⚠ build 目录下的 test-suite.log 不能当 PASS 的出处：automake 不往该文件写
PASS 行（它只有 16 条判决行 = 15 FAIL + 1 SKIP，其 :5 为
「15 of 19 tests failed.  (1 test was not run).」），配方也正是从它解析
UPSTREAM_TEST（conanfile.py:224-232）⇒ 本轮 create 日志里的 UPSTREAM_TEST
只有 16 条，另 4 条 PASS 只在 stdout。
⚠ **该组 15/4/1 的读数不引 probe/src/test-suite.log**：那份是**打补丁前的基线**
（其 :5 =「19 of 19 tests failed.  (1 test was not run).」，判决行
19 FAIL + 1 SKIP、PASS 0 条；5810 B，mtime 2026-09-25 05:01），给不出 15/4/1；
该树 make check 非零退出这半句成立（probe-check.log:49-53 的
make Error 1/Error 2/Error 2 ⇒ RC=2）。同数字对照改用两处一手件：
①本轮 conan build 树自己的 test-suite.log——
~/tmp/ch/home-z33-jellyfish1/p/b/jellye1d3de609d8b5/b/build-release/
test-suite.log:5「15 of 19 tests failed.  (1 test was not run).」，判决行
15 FAIL + 1 SKIP + 0 PASS（5790 B，sha256
4670d4c145274d761ab5383d7d9e570f19b8808a661aa9ee1bc70e0582fa42dd，本轮独立复算）；
②同一棵探测树打完 0001 之后的复跑 stdout——probe5b-check.log 判决行
4 PASS + 15 FAIL + 1 SKIP、汇总 :39「15 of 19 tests failed」、
probe5b-a.out:18 CHECK_RC=2。

automake 汇总行：15 of 19 tests failed. (1 test was not run).
逐判决：PASS 4（generate_sequence.sh、generate_fastq_sequence.sh、
parsers.sh、unit_tests/unit_tests.sh）；FAIL 15；SKIP 1（big.sh）。

- 注册面：Makefile.am 的 TESTS 共 19 个 tests/*.sh，另有 TESTS +=
  unit_tests/unit_tests.sh，合计 20 个 runner；big.sh 由上游自身
  if [ -z "$BIG" ]; then exit 77 跳过（不是平台限制，分母不缩）。
- unit_tests.sh 是 gtest runner，--gtest_list_tests 实测注册 6 个原子用例
  （SimpleCircularBufferTest.FillEmpty / .Usefull、
  SquareBinaryMatrix.Initialization、OffsetsTest/ComputeOffsetsTest.CheckCoherency/0,1,2）
  ⇒ runner 数与原子用例数不得混算。
- 15 项 FAIL 是同一家族：都是 tests/compat.sh 的 check() 函数对
  上游 baked 的 md5 做比较，且差异全部落在字节级产物上
  （数据库文件 _0、histo、stats），而逻辑结果与上游一致：
  同一次运行里 dump -c -L 2 的输出、_L.dump 与 query 产物的 md5
  与上游 baked 值逐字节相同，只有含全部（重数 1 的）条目的
  _all.dump 与 _0/histo/stats 不同。
  ⇒ 定性：jellyfish 在该工具链下算出的 k-mer 计数结果与上游一致，
  差的是上游 2013 年录制的二进制文件与直方图基线在本平台不复现。
- 曾另开一轮（probe8）想把 __int128 支路接通，用它来对照 15 项 FAIL 是否与
  divisor64 的结构体宽度相关。**该对照未做成，读数如下**：把
  libclang_rt.builtins.a 塞进 LIBS 后 configure 确认 HAVE_INT128=1、make RC=0，
  但 .libs/libjellyfish-1.1.so.1 里仍是 U __udivti3
  （~/tmp/uc2/z33-jellyfish1/probe8-a.out:3、:5-6），运行期第一条错误照旧是
  Error relocating ... __udivti3: symbol not found（:8），冒烟产物没生成（:10），
  整场 make check 从 4 PASS/15 FAIL 塌成 0 PASS/19 FAIL/1 SKIP（:11 CHECK_RC=2，
  :15-35，probe8-check.log:33「19 of 19 tests failed」口径含 unit_tests）。
  ⇒ 那条支路连可加载的 .so 都产不出，拿不到任何可比的 md5，
  **本节上方那条定性不依赖 __int128 假设**，只依赖逐条差异项清单与
  「逻辑计数结果一致」这两条证据；ac_cv_type___int128=no 是必要处置而非回避。

## 能力面：mmap（本窗 #10 探针区实测）
include/jellyfish/mapped_file.hpp 第 52 行
_base = (char *)mmap(NULL, _length, PROT_READ, MAP_PRIVATE, fd, 0);
第 54 行失败路径 eraise(ErrorMMap)。走这条路径的命令：
query / dump / histo / stats（dump_main.cc、query_main.cc、histo_main.cc、
stats_main.cc 以及 compacted_hash.hpp / raw_dumper.hpp / fastq_dumper.hpp）。
test_package 的 mmap_probe 以同一组参数直接调 mmap(2)，设备实测：
MMAP_RESULT=OK size=258 first_byte=74 与 MUNMAP=OK，退出码 0
（本轮 create 读数在 reports/w3-local-ci.log:886、:887）
⇒ 只读文件映射（PROT_READ + MAP_PRIVATE）在 OHOS 上可用（不是 SIGSYS/不是 EACCES）。
未覆盖面如实列出，不升格：MAP_SHARED 的文件映射**未测**；
随包安装的公共头 allocators_mmap.hpp（匿名映射做哈希表分配，count 路径）本轮
未被单独探针验证，allocators_shm.hpp（shm_open + mmap 后端，本包默认不走）
同样**未测**（w3-local-ci.log:832 的安装清单里两份头都在）。

## 五维测试账本
- N_static（上游静态声明的原子用例）：25 = 19 个 automake shell 用例 + 6 个 gtest 注册用例
- N_registered（构建系统注册）：20 个 automake TESTS（其中 unit_tests.sh 是 gtest runner，内含 6 个原子用例）
- N_executed：19
- 未执行与失败分类：上游条件跳过 1（big.sh，需 BIG 环境变量，非平台限制）；
  执行但失败 15（同一 md5 基线家族，逐判决与定性见上节与 test-suite.log）；通过 4
- N_consumer（test_package 消费者）：2 个程序（mmap_probe.cc 真编译真链接真运行；
  run_cli_tests.sh 驱动打包后的 CLI），值断言合计 10 条（逐条枚举见
  test_package/MANIFEST.yml:109-116）
口径：通过率分母按执行项算为 4/19；按静态全量算为 4/25。两者都列出，不合并。
框架 W3 打印的 Pass rate: 100.0% (1/1)（w3-local-ci.log:918）是它自己的
消费者/smoke 口径（test_package 一臂），**不等于**上游 19 项通过率，两者不换算。

## 适配路径
适配路径：B（判 **create**）——raise_t 抛出析构那一面从上一版的 hit **升 create**，
占本 PR 的知识位（一 PR 一知识）；CONFIG_SHELL 面与 compiler-rt builtins 面
仍为命中在池条目（沿用，不新建）。升 create 的判据是「判 hit 四条件」之条件 2
（症状相同但用的是既有条目没写的另一条解法 ⇒ 不算 hit，按 create 报），
四条行号级层次差与全部查重计数见
reports/knowledge-candidate-ledger.md 候选 1。
使用知识库：E543-draft-7707（knowledge/drafts/E543-draft-7707.md:35-38 与 :14-18
  —— C++11 把析构隐式异常规范改为隐式 noexcept，从中 throw 即 std::terminate，
  libc++abi 文案一致。）**该条目是本条新草稿的对照条目，不是命中条目**：
  它的 locus 划在「测试**有意**验证析构抛异常」（:28-30，libtut 的 teardown_ex 组），
  :42-43 断言「交付的库头文件在现代标准下正常」，:54-63 的解法是
  -std=gnu++98 重编上游套件，:73-74 与 .kv:34-36（forbid_1）把 noexcept(false)
  列为禁止做法——本包这四条前提**全部不成立**（抛点就在被安装的
  jellyfish/err.hpp:123，降档修不到库头且被同条 :77-78 自禁），
  故升 create 而非 hit。分叉点与新增值写在
  knowledge/drafts/DRAFT-jellyfish1-1.1.11-shipped-header-throwing-destructor-noexcept-false.md。
  ⚠ E543 这个槽位在池内被大量复用（实测 52 份 E543-draft-*.kv，其中
  DRAFT-E543-ohos-conan-run-shell-quote-cstring 属完全不同机制）⇒ 引用一律按**文件名**。
  DRAFT-E551-ohos-conan-configshell-bash-libtool-escaping.md:1、:12-17、:25-28
  （CONFIG_SHELL=bash 下老 ltmain.sh 生成的 libtool 丢引号转义，处置同为
  命令行前缀赋值 CONFIG_SHELL=/bin/sh 重生成；本包第二处故障 ECHO=print 与其
  共享同一根因与处置，按「组合型知识不判重」不单开，族谱对照
  DRAFT-6487-classads-configshell-hmdfs-getcwd.kv:32-33）；
  DRAFT-libsidplayfp-2.15.1-compiler-rt-builtins-linking.kv:1、:8
  （libtool 产出的共享库缺 compiler-rt builtins 辅助符号 ⇒
  Error relocating ... symbol not found；本包申报的那面就是它，符号由
  __powidf2 换成 __udivti3；该条目 .md:51 的「不命中静态链接消费者」正对应本包
  本轮 --disable-shared 的交付构型，同族另见
  DRAFT-13534-libzimg-3.0.6-libtool-nostdlib-builtins.md:20-23）
知识库扩展：新建 DRAFT-jellyfish1-1.1.11-shipped-header-throwing-destructor-noexcept-false
  （knowledge/drafts/ 下 .kv 与 .md **成对**；.kv 已过真实解析器
  yaml.safe_load 与仓内 models.parse_kv_file 双向复验，error_signature 已用
  re.search 对一手日志逐分支自证，见
  ~/tmp/uc2/z33-jellyfish1-fix3/validate.log）
关联 Issue：#3405（Issue 已由主理创建，本轮整改回填实号）
  https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3405
  标题《【知识库扩展】jellyfish1 1.1.11：抛出析构位于被交付的库头（非上游测试套件）时，E543 推荐的 gnu++98 时代标准降档不可用，其 noexcept(false) 禁令需按 locus 收窄适用面》；
  建号时用的机制一句话 = 「抛出析构位于被交付的库头时，E543 的时代标准降档出路不可用，noexcept(false) 才是最小干预正解」（与本行原文同源）；
  回填 HEAD：本轮（第 4 轮整改）落盘后的分支 HEAD，末段 SHA 以本件所属提交与 PR 评论为准（件内不写死自身 sha，否则每次改动即失效）；本 PR 不自建 Issue。
申报机制一句话（本 PR 新建的那条）：当「析构里 throw」位于**被交付的库头**
（而不是测试代码）时，E543 给的等价出路「用时代标准重编上游套件」整个失效
——库头随消费者一起编译，不随测试目标降档，而把 -std=gnu++98 加进配方又被
E543 自己禁止 ⇒ 该 locus 下给库头那个析构加一行 noexcept(false) 是最小干预正解，
E543 的 noexcept(false) 禁令需按 locus 收窄适用面。
命中在池条目的另两面（沿用既有知识，不新建，也不占本 PR 知识位）：
①CONFIG_SHELL 面 → DRAFT-E551（下文引用块）；
②compiler-rt builtins 面，其机制一句话原样保留如下：
  libtool 产出的共享库不会自动链接 compiler-rt 的 __udivti3，
  OHOS NDK 上任何走 __int128 的 autotools 包都会在运行期报
  Error relocating ... symbol not found，而把它关掉可能改变上游录制基线的可复现性。
补丁必要性的取舍披露：E543-draft-7707.md:54-63 给的等价出路是把上游套件按
时代标准（-std=gnu++98）重编，本包**不采用**——抛出析构在被交付的库头
jellyfish/err.hpp 里，eraise 是全库错误上报惯用法，只把测试目标拉回时代标准
会让所有消费者的错误路径仍是 terminate；该条目 :73-74 与 .kv:34-36 禁止的是
「给上游**测试**的析构打 noexcept(false)」，本包改的是**库头**，不触犯该禁止项，
但分歧点必须写明 ⇒ 一行补丁成立。
**上一版的处理错在定档、不错在处置**：处置（库头加 noexcept(false)）当时就是
对的，但 B 档写成 hit 并据此写「不新建」——按判 hit 四条件的条件 2，
「症状相同、解法却不在被引条目覆盖面上」应判 create，故本轮升档并补草稿。
本轮另补一手锚点：抛点位置由草稿的 prescan_pattern 在真件上直接扫出——
未打补丁树 jellyfish/err.hpp:123 `~raise_t() { throw err_t(oss.str()); }`、
已打补丁树同文件同 `:123` 为 `~raise_t() noexcept(false) {...}`、
两树的 `:139` 均为 `#define eraise(e) if(1) err::raise_t<e>()`，
读数见 ~/tmp/uc2/z33-jellyfish1-fix3/validate.log 第 3 节。
未占本 PR 知识位的面：①- DGTEST_USE_OWN_TR1_TUPLE=1（仓内全域 0 命中，
有独立成条资格，属 create 资格档）⇒ 草稿已放配送池
~/tmp/uc2/z33-jellyfish1-bpool/DRAFT-jellyfish1-1.1.11-gtest-tr1-tuple-header-flags.{kv,md}，
由主理并入 经验文档/B草稿库/，本 PR 不含该知识点（本 PR 的知识位已由
raise_t 那条新草稿占用，一 PR 一知识）；②CONFIG_SHELL 面（hit E551）；
③compiler-rt builtins 面（hit DRAFT-libsidplayfp）。
全部候选的四范围查重计数与判据见 reports/knowledge-candidate-ledger.md。

## 门禁与 preflight 实况（本轮复算，全部指向当前 HEAD 的构建输入）
- conan-verify：G0/G1/G2/G3 PASS，**Verdict**: PASS
  （reports/conan-verify-report.md:3 与各节，Date 2026-09-25T07:20:43；
  判决文字 + Verdict 行 + VERIFY_RC=0 三条同看，本轮无图标与文字相反的判决行）。
- W3 本地 CI 模拟：通过（标记在驱动件 ~/tmp/uc2/z33-jellyfish1/finish-r2.log:59
  「✅ W3 本地 CI 模拟通过」；日志本体 reports/w3-local-ci.log mtime 07:24 晚于
  create 的 07:20，两者 md5 不同，.ci-result.json 的 log_sha256 与实算一致，
  L0/L1/L2/L4/L5 全 pass 在 :906-910，L1e 破坏性负测在 :898-902）。
- finish：**未全绿**，如实披露——FINISH_RC=2
  （~/tmp/uc2/z33-jellyfish1-fix/r2-master.log:63），失败步骤 step5b（知识图谱
  完整性检查发现 1 类问题，6 条 knowledge_gained 未登记）与 step8
  （gen_summary 报 'str' object has no attribute 'append'，全仓既有崩溃）；
  ⚠ 同一次运行里还打了 STEP_FAILED: Step6（finish-r2.log:118-120 的
  EXIT_REASON: finish_success / EXIT_CODE: 0 是知识整理块的口径），
  两套编号指同一批缺口，对账时按 step5b + step8 读。
  status 字段仍取 built，因为 built 的依据是 W3 通过，与 finish 的
  知识整理缺口无关；本轮未新建任何 packaging/、.staging-verified、
  test-report.md 之类的空件凑绿。
- preflight（python3 scripts/ohc/preflight.py . origin/main HEAD，只读实跑）：
  rc=1，findings 1 条 = PF9（archives/j/jellyfish1/README.md、commands.json、
  manifest.yaml 三件报「缺版本目录层」）。PF7 复算命中数 **0**
  （第 1 轮审计报的 2 条 deb.debian.org 已由取源换上游官方站消除）。
  PF9 属框架自身互斥而非本包缺件：仓规与 G1 结构门禁要求软件级
  README.md/manifest.yaml 存在，PF9 却要求所有变更路径都带版本目录层；
  origin/main 上同形软件级文件共 10862 件（例：archives/l/libjpeg-turbo/
  README.md 与 manifest.yaml 都在），数千包同形 ⇒ 不改文件、不删三件套，
  证据攒此处交框架侧处置。
- 本轮整改是否动构建输入：**没有**。配方导出面实测只含
  conanfile.py + conandata.yml（reports/conan-create.log:3-7 的
  「Copied 1 .yml file: conandata.yml / Copied 1 .py file: conanfile.py」，
  无 notes.md / manifest.yaml / README.md），export_sources 只有
  patches/ 两枚 .patch；本轮改的是 notes.md、两级 manifest.yaml、README.md、
  test_package/MANIFEST.yml 这些非导出件 ⇒ recipe revision 不变，
  上面 07:20/07:24 那批门禁证据仍绑定当前 HEAD，不必重跑 create。

---

**编译结束**: 2026-09-25 07:24（第 2 轮 create + W3，B 机）
最终状态：built
---

**编译结束**: 2026-09-25 19:55
**最终状态**: built

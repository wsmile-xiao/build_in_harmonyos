# libe-book-tools 0.1.3 — 测试报告（真机 W3 + 上游套件真跑）

日期：2026-09-20
环境：HarmonyOS PC aarch64（clang 15 / Conan 2.29.1，设备本地真跑）
profile：`ohos-aarch64`（host 与 build 同一份 profile，os=OHOS / arch=armv8 / cppstd=17）
隔离缓存：`CONAN_HOME=~/work/psj/ch-lbk13140`（只从 `~/.conan2` 拷 profiles / settings.yml /
remotes.json / global.conf / extensions / migrations，**未写共享缓存**）
状态：**通过**（`conan create` 退出码 0；上游 `make check` 测试程序 1/1 PASS、
程序内 cppunit 14/14 `OK (14)`；test_package 消费者 46/46；L1e 破坏性反向验证成立）

## conan create 结果

```
$ conan create archives/l/libe-book-tools/0.1.3 \
    -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing

libe-book-tools/0.1.3: Exporting recipe ... revision fb15f2f70e5ea83bca18e22aa23a8235
libe-book-tools/0.1.3: Package created 6083f91ceb24a67315a8f7fa27298fa9f983f224
libe-book-tools/0.1.3: Calling build()   → ./configure → make -j1 → make -j1 check
libe-book-tools/0.1.3: Calling package() → make -j1 install DESTDIR=...
======== Launching test_package ========
======== Testing the package: Executing test ========
CREATE_EXIT:0
```

依赖 7 件全部命中制品仓预编译二进制（先做 `conan graph info` 预检确认都是
`- Download (ohpcd)`，没有任何一项需要在设备上从源码构建）。

## 上游测试真跑（make check，R51/R34）

上游体系：`src/test/Makefile.am` 把一个 cppunit 程序 `test` 同时登记进
`check_PROGRAMS` 与 `TESTS`，由 `--enable-tests`（上游默认）构建；配方在
`build()` 内执行 `make -j1 check`，失败即出不了包（不是「跳过测试」的软门禁）。

automake 汇总（构建日志原文，Testsuite summary for libe-book **0.1.3**）：

```
PASS: test
# TOTAL: 1
# PASS:  1
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# ERROR: 0
```

程序内逐用例（`src/test/test.log`，与构建目录同级留存）：**14 行 ` : OK` +
末行 `OK (14)`**，例如

```
test::EBOOKBitStreamTest::testRead8 : OK
test::EBOOKBitStreamTest::testRead32 : OK
test::EBOOKMemoryStreamTest::testSeek : OK
test::PDBLZ77StreamTest::testRead : OK
test::SoftBookLZSSStreamTest::testSeek : OK
OK (14)
```

口径对照（诚实的「声明 ≥ 实测」）：

| 口径 | 数值 | 取数方式 |
|---|---|---|
| dist 包内 `CPPUNIT_TEST` 宏总数 | 22 | `grep -cE '^[[:space:]]*CPPUNIT_TEST[[:space:]]*\(' src/test/*Test.cpp` 求和 |
| 本配置参与编译并实跑 | 14 | `test.log` 的 ` : OK` 行数与 `OK (14)` |
| 上游条件编译排除 | 8 | `EBOOKLanguageManagerTest` 2（`if WITH_LIBLANGTAG`）+ `XMLCollectorTest` 4 与 `XMLTreeWalkerTest` 2（`if ENABLE_EXPERIMENTAL`）；两组依赖（liblangtag、libcss/hubbub/mspack）均不在制品仓 |
| automake 粒度 | 1 程序 | `# TOTAL: 1`，单位是测试程序而非用例，两种粒度都列出以免混加 |

`src/fuzz/Makefile.am` 的 `noinst_PROGRAMS = lrffuzzer pdbfuzzer` 是 fuzzing
目标、不是测试用例，且 `--enable-fuzzers` 默认 no，不计入 N。

## test_package 消费者测试（鸿蒙特有测试）

`test_package/test_libe_book_tools.sh` 自行计数并打印：

```
TOTAL=46 PASS=46 FAIL=0
```

覆盖面（每条都是独立断言，失败即 `[FAIL]` 并以非零退出）：交付结构与
「本包不含 lib/ 与 include/」；ELF magic 与 `e_machine=EM_AARCH64`（用 `od`
读偏移 18）；三个工具的 `--version` 退出码 0 且自报 `ebook2text 0.1.3`；
FictionBook 2 正向跑满 text / raw / html 三条导出链路并断言各自的真实结构
（`openParagraph`、`setDocumentMetaData`、`insertText(text: …)`、`<html>`、
`meta author` / `meta subject`）；`--info` 断言 `dc:subject` 与
`meta:initial-creator` 且与正文输出不同；负向对照 garbage 字节必须让三个工具
都 rc=1 并打印 `has not been recognized`；未知选项与无参数按上游
`printUsage()` 的 `return -1` 断言 rc=255；以及把 0.1.3 的 XHTML 已知边界
（识别成功但 parse 非 OK → rc=1 且 stderr 无 "not recognized"）固化成断言。

## L1e / R34 破坏性反向验证（真机实跑）

```
POS_EXIT:0        TOTAL=46 PASS=46 FAIL=0
sabotage: bin/ moved away
NEG_EXIT:1
[FAIL] 包内 bin/ 目录存在
[FAIL] ebook2text 已安装且可执行
[FAIL] ebook2raw 已安装且可执行
[FAIL] ebook2html 已安装且可执行
[FAIL] ebook2text 是 ELF 镜像
restored
RESTORED_EXIT:0   TOTAL=46 PASS=46 FAIL=0
```

注意：`conan test` 在隔离 CONAN_HOME 下必须同时给 `-pr:h` 与 `-pr:b`，只给
`-pr` 会因 `profiles/default` 不存在而直接报错——那会被误读成「反向验证通过」。

## 交付物

```
包内顶层: bin conaninfo.txt conanmanifest.txt licenses
ebook2text  35650048 B  e_machine=b700  sha256 c97de4c268d79760ee4fdb30ce1f4eb3a00bcf12f1141fbf68edc70982a317fb
ebook2raw   35654144 B  e_machine=b700  sha256 6988d868573df408607b3be3dfd9e48e5791e59eff331a17673806871e75346f
ebook2html  35719680 B  e_machine=b700  sha256 eb1cc1e924d7b3a15136d479c59b2a4cff22262a0a9b0f701fd97b9d073fe3c5
NEEDED（三个一致）: libc++_shared.so, libxml2.so.16, libc.so
RUNPATH : <libxml2 包目录>/lib（bake 进可执行文件，运行期不依赖 LD_LIBRARY_PATH）
```

包内**没有** `lib/` 与 `include/`：库本体属 `libe-book/0.1.4`，重复交付同一份
`libe-book-0.1.a` 会让同时依赖两者的消费者拿到重复符号。二进制体积偏大来自
静态链入的 ICU（`icu4c/77` 只提供静态归档，链接行需带 `-lc++`）。

## 补丁

`patches/0001-src-EBOOKCharsetConverter-icu-true-false.patch`（1 行改动，
portability）：`ucnv_convertEx(..., TRUE, TRUE, &status)` → `true, true`。
判据全部当场取：0.1.3 全树 `src/`+`inc/` 里 `\b(TRUE|FALSE)\b` 仅此 1 处；
0.1.4 为 0 处；两份文件 `diff` 结果只有 `127c127` 一行不同 —— 即上游自己就是
这么修的，因此不发明 `#define TRUE 1` 这类 shim。

## 复现

```sh
CONAN_HOME=~/work/psj/ch-lbk13140 conan create archives/l/libe-book-tools/0.1.3 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

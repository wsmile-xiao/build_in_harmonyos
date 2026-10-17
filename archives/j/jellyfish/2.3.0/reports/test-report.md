# jellyfish 2.3.0 — 测试报告（真机 conan create + 上游套件真跑）

日期：2026-09-21
环境：HarmonyOS PC aarch64（`uname -s = HarmonyOS`，harmonybrew SDK clang / Conan 2.29.1，设备本地真跑）
profile：`ohos-aarch64`（host 与 build 同一份 profile）
隔离缓存：`CONAN_HOME=~/work/psj/ch-jellyfish`（只从 `~/.conan2` 拷 profiles / settings.yml /
remotes.json / global.conf / extensions / migrations，**未写共享缓存、未改任何人的 `global.conf`**；
起跑前 `pgrep -f conan` 确认无他人 `conan create`，被占用时 10 min 轮询等待，不抢占也不向别人发信号）
状态：**通过**（`conan create` 退出码 0；上游 `make check` `# TOTAL: 15 / # PASS: 10 / # SKIP: 5 /
# FAIL: 0 / # ERROR: 0`；其内层内置 googletest `[  PASSED  ] 51310 tests` 0 失败；
test_package 消费者 11/11；L1e/R34 破坏性反向验证成立）

## conan create 结果

```
$ conan create archives/j/jellyfish/2.3.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing

jellyfish/2.3.0: Exported: jellyfish/2.3.0#48d56d89a329eca0a88421faefa4b675
jellyfish/2.3.0: Calling source()  → 官方 dist 包 jellyfish-2.3.0.tar.gz（1151287 B，
    sha256 e195b7cf7ba42a90e5e112c0ed27894cd7ac864476dc5fb45ab169f5b930ea5a）
jellyfish/2.3.0: Apply patch (portability) × 7
jellyfish/2.3.0: Calling build()   → ./configure --disable-htslib --disable-shared --enable-static
                                   → make -j1 → make -j1 check
jellyfish/2.3.0: UPSTREAM 'make check' RESULTS: TOTAL=15 PASS=10 FAIL=0 SKIP=5 ERROR=0
jellyfish/2.3.0: Calling package() → make install
jellyfish/2.3.0: Full package reference:
    jellyfish/2.3.0#48d56d89a329eca0a88421faefa4b675:21b17f8b2bc0e9511e276e3d57a23893067cefe5#17174b04d41a561c6eeb843d894d106c
======== Launching test_package ========
jellyfish/2.3.0(1): RUN: bash test.sh   (env=conanrun)
ASSERTIONS: 11, FAILURES: 0
CREATE_EXIT:0        （运行窗口 23:32:49 → 23:47:17 CST）
```

`dependencies: []` —— 全程无第三方包需解析（`jellyfish-2.0.pc` 的 `Libs` 仅 `-ljellyfish-2.0 -lpthread`；
内置 googletest 随 dist 包发布）。

## 上游测试真跑（`make check`，配方 build() 内执行、非 0 退出即出不了包）

automake 汇总与逐条结果：

```
# TOTAL: 15   # PASS:  10   # SKIP: 5   # XFAIL: 0   # FAIL: 0   # XPASS: 0   # ERROR: 0
PASS: tests/generate_sequence.sh   PASS: tests/parallel_hashing.sh   PASS: tests/merge.sh
PASS: tests/bloom_filter.sh        SKIP: tests/big.sh                PASS: tests/subset_hashing.sh
PASS: tests/multi_file.sh          PASS: tests/bloom_counter.sh      PASS: tests/large_key.sh
SKIP: tests/sam.sh                 PASS: tests/small_mers.sh         SKIP: tests/swig_python.sh
SKIP: tests/swig_ruby.sh           SKIP: tests/swig_perl.sh          PASS: unit_tests/unit_tests.sh
```

5 个 SKIP 全部是**上游脚本自身的 `exit 77` 分支**，不是配方关的：

| 脚本 | 上游代码 | 本包未满足的条件 |
|---|---|---|
| `tests/big.sh` | `if [ -z "$BIG" ]; then ... exit 77` | 需显式 `BIG=1` 跑 1G 数据集 |
| `tests/sam.sh` | `if ! grep -q '#define HAVE_HTSLIB' ../config.h; then exit 77` | 配方显式 `--disable-htslib`（制品仓无 htslib 发布，不能依赖构建机系统库） |
| `tests/swig_python.sh` | `[ -z "$ENABLE_PYTHON_BINDING" ] && exit 77` | configure 未探测到 SWIG，未生成绑定 |
| `tests/swig_ruby.sh` / `tests/swig_perl.sh` | 同上（`ENABLE_{RUBY,PERL}_BINDING`） | 同上 |

### 内置 googletest（`unit_tests/unit_tests.sh` → `bin/test_all`）

```
Named pipes unavailable: excluding mkfifo-based gtest cases
[==========] Running 51310 tests from 52 test cases.
[==========] 51310 tests from 52 test cases ran. (94761 ms total)
[  PASSED  ] 51310 tests.
```

**口径核对（防「少报」）**：

```
$ cd <build-release> && ./bin/test_all --gtest_list_tests | grep -c '^  '
51313                                   # 未过滤：51313 个用例 / 55 个 suite
$ ./bin/test_all --gtest_filter=-TmpPipes.*:GeneratorManager.OneLiners --gtest_list_tests | grep -c '^  '
51310                                   # 过滤后：51310
$ # 两者差集
GeneratorManager.OneLiners
TmpPipes.CreateDestroy
TmpPipes.Discard
```

即上游声明口径 **51313**、本平台实跑 **51310**，差的 3 个都是直接调用
`jellyfish::tmp_pipes` → `mkfifo(2)` 的用例，由 `patches/0006` 的**运行期能力探测**排除
（在允许命名管道的平台上这 3 个用例照常执行）。宏计数口径另附：
`grep -rhoE '\b(TEST|TEST_F|TEST_P|TYPED_TEST)\(' unit_tests/*.cc` → TEST 61 / TEST_F 2 / TEST_P 11 / TYPED_TEST 13
= 87 个宏，经 `INSTANTIATE_TEST_CASE_P` 的 `Range`/`Combine` 参数组合展开为上面数万实例，故报告与 PR 正文均按 gtest 实例数记。

## 鸿蒙特有测试（`test_package/test.sh`，跑的是已安装的 `bin/jellyfish`）

```
PASS: jellyfish --version                      （精确等于 "jellyfish 2.3.0"）
PASS: jellyfish count produces a non-empty database
PASS: histo output                             （逐行黄金值 1 3;6 1;7 1;）
PASS: dump -c output                           （5 条 canonical mer 逐行比对）
PASS: query ACGTA
PASS: query TACGT canonicalized                （反向互补归一化）
PASS: query -s line count                      （从 FASTA 读序列，16 行）
PASS: query -s ACGTA hits                      （7 次命中）
PASS: jellyfish info reads the database
PASS: count rejects a missing input file       （负例）
PASS: histo rejects a missing database         （负例）
ASSERTIONS: 11, FAILURES: 0
```

## L1e / R34 破坏性反向验证（真机实跑）

```
=== baseline (expect pass) ===            ASSERTIONS: 11, FAILURES: 0   POS_EXIT:0
$ mv <pkg>/bin <pkg>/bin_hidden
=== bin/ moved away (expect fail) ===     ASSERTIONS: 11, FAILURES: 9   NEG_EXIT:1
    FAIL: jellyfish --version did not run
    FAIL: jellyfish count did not produce out.jf
    FAIL: jellyfish histo failed
    FAIL: jellyfish dump failed
    FAIL: jellyfish query ACGTA failed
    FAIL: jellyfish query TACGT failed
    FAIL: jellyfish query -s failed
    FAIL: query -s ACGTA hits (got: '0', want: '7')
$ mv <pkg>/bin_hidden <pkg>/bin
=== restored (expect pass) ===            ASSERTIONS: 11, FAILURES: 0   POS2_EXIT:0
```

9 条失败（另外 2 条是「必须被拒绝」的负例，二进制不在时它们仍然"通过"，正是设计如此），
证明这 11 项断言确实依赖交付的 `bin/jellyfish`，不是自我实现的空壳。

## 命名管道能力取证（补丁 0003/0004/0006 的前提）

```
$ python -c 'os.mkfifo("~/work/psj/jf13942-fifo-probe")'
FAIL  /storage/Users/currentUser/work/psj  PermissionError: [Errno 1] Operation not permitted
FAIL  /storage/Users/currentUser           PermissionError: [Errno 1] Operation not permitted
FAIL  /dev/shm                             PermissionError: [Errno 13] Permission denied
FAIL  /tmp                                 OSError: [Errno 30] Read-only file system
$ ctypes.CDLL("libc.so", use_errno=True).mkfifo(...)
libc.mkfifo rc=-1 errno=1 Operation not permitted
$ mkfifo x            # toybox
inaccessible or not found   → mkfifo_rc=127、fifo_type=absent
```

## 交付物

```
包内顶层：bin  conaninfo.txt  conanmanifest.txt  include  lib  licenses  share
bin/jellyfish                 571968 B   ELF64 小端   e_machine=0xb7 (EM_AARCH64)
  $ bin/jellyfish --version   →  jellyfish 2.3.0
lib/libjellyfish-2.0.a (+ .la)   lib/pkgconfig/jellyfish-2.0.pc
include/jellyfish-2.3.0/jellyfish/**
licenses/{LICENSE-BSD-3-Clause, LICENSE-GPL-3.0, README}
```

## 过程中真机实测到并修掉的两次失败（记录以免后人重踩）

1. `patches/0003` 最初把 `${pref}_gunzip_cmds` 的 heredoc 一起缩进进 `if` 分支 →
   mksh 报 `warning: here-document at line 23 delimited by end-of-file (wanted 'EOF')` +
   `syntax error: unexpected end of file from 'if' command on line 21`，`FAIL: tests/multi_file.sh`、
   `# FAIL: 1`、`CREATE_EXIT:1`。`<<EOF` 不是 `<<-EOF`，终止符必须顶格；改成在 heredoc **之后**才开始包 `if` 后转绿。
2. `source()` 拉官方 dist 包时 `github.com` connect 30 s 超时（conan 自带重试耗尽）→
   `ERROR: jellyfish/2.3.0: Error in source() method`、`CREATE_EXIT:1`。同一 URL 另一次实测 56 s 下载完成，
   确认是抖动而非不可达；且 tag 归档（codeload，679144 B）不含预生成 `configure`/`Makefile.in` 而不能作备用源，
   故在 `source()` 里对同一 URL 同一校验和做最多 5 次有界重试（校验和不匹配立即抛出、不重试）。

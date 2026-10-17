# jellyfish 2.3.0 — OpenHarmony PC 适配笔记

## 一、上游识别

| 项 | 值 |
|---|---|
| 上游项目 | `gmarcais/Jellyfish` — DNA/RNA k-mer 计数工具（C++ / Autotools / libtool） |
| 版本 | 2.3.0（tag `v2.3.0`，官方 release 资产 `jellyfish-2.3.0.tar.gz`） |
| 官方 dist 包 | `https://github.com/gmarcais/Jellyfish/releases/download/v2.3.0/jellyfish-2.3.0.tar.gz` |
| sha256 | `e195b7cf7ba42a90e5e112c0ed27894cd7ac864476dc5fb45ab169f5b930ea5a`（1,151,287 字节，2026-09-21 本机与真机双端下载实测同值） |
| 许可 | 双许可 BSD-3-Clause OR GPL-3.0（`LICENSE-BSD-3-Clause` / `LICENSE-GPL-3.0`） |
| 构建产物 | `bin/jellyfish`（CLI）+ `libjellyfish-2.0.a`（C++ 库）+ `include/jellyfish-2.3.0/jellyfish/**` + `jellyfish-2.0.pc` |

**为什么必须是 dist 包而不是 tag 归档**：`https://codeload.github.com/gmarcais/Jellyfish/tar.gz/refs/tags/v2.3.0`
（679,144 B，sha256 `23819da9edb579a0cfb8baac9eff473a9477f4f749930cdb754dce1d117495cd`）只含被 git 跟踪的文件——
顶层有 `Makefile.am`/`configure.ac`，**没有预生成的 `configure`、`Makefile.in`、`config.guess`、`compile`、`ltmain.sh`**。
真机与 CI worker 都没有 autoconf/automake/libtoolize 可以再生成，用它必然在 configure 前停摆。
因此 `conandata.yml` 只保留官方 release 资产这一个源（也不挂任何第三方镜像，PF7），
针对真机侧 `github.com` connect 阶段偶发 >30 s 超时（同一 URL 实测一次 56 s 跑完、一次 connect 超时），
在 `source()` 里对**同一 URL 同一校验和**做最多 5 次有界重试；校验和不匹配时立即抛出、不重试。

## 二、依赖分析

- **无强制第三方依赖**：`configure.ac` 只可选探测 htslib（SAM/BAM/CRAM 输入）与 SWIG（Python/Ruby/Perl 绑定）；
  `jellyfish-2.0.pc` 的 `Libs` 仅 `-ljellyfish-2.0 -lpthread`。内置 googletest 随 dist 包发布（`unit_tests/gtest/`），不是外部依赖。
- 本配方显式 `--disable-htslib`：制品仓没有 htslib 发布，放任 configure 探测构建机系统库会让包内容随构建机漂移。
  上游 `tests/sam.sh` 按自身逻辑 `grep -q '#define HAVE_HTSLIB' ../config.h` 不成立即 `exit 77` 跳过。
- 制品仓预检：`GET /api/registry?keyword=jellyfish` → `total: 0`，`jellyfish/2.3.0` 首次适配（不撞 R37/L0j）。

## 三、适配实现（7 个补丁，全部可移植性、无平台宏）

1. `0001-config.guess.patch` — `uname -s = HarmonyOS` 不在 2018 版 config.guess 的已知系统里，报
   `cannot guess build type`。在 `case "$UNAME_SYSTEM" in` 里加
   `HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl ;;`，让下面 `aarch64:Linux:*:*)` 分支产出
   `aarch64-unknown-linux-musl`（E160）。
2. `0002-configure.patch` — 两处：
   - `config.status` 用 `umask 077 && mktemp -d "./confXXXXXX"` 建临时目录；HMDFS 强制 setgid 与权限归一化后
     该目录连属主都不可写，报 `config.status: ./confXXXXXX/subs1.awk: Permission denied`。两处 `umask 077` 放宽为
     `umask 022`（`mktemp` 失败的回退分支给 `mkdir` 补 `2>/dev/null`）——E011/E114 标准解法。
   - 增加 `unix2dos` 功能探测：toybox 的 `unix2dos` 不支持测试脚本使用的 `-n <in> <out>`，探测失败则置空
     `UNIX2DOS`，`tests/parallel_hashing.sh` 走 `cp` 回退分支；否则 `generate_sequence.sh`/`parallel_hashing.sh`
     在 `set -e` 下误失败。
3. `0003-tests-multi_file.sh.patch` / `0004-tests-bloom_counter.sh.patch` / `0006-unit_tests-unit_tests.sh.patch`
   — 命名管道：HarmonyOS 对 `mkfifo(2)` 返回 EPERM（系统调用级实测见第五节），toybox 亦不提供 `mkfifo` 命令。
   三处依赖 FIFO 的测试改为**运行期能力探测**：
   - `bloom_counter.sh`：管道可用时逐字执行原 `-g/-G` 命令；不可用时把同一份 `seq1m_0.fa` 作为两个普通参数喂给
     `jellyfish bc`，装载的 k-mer 集合与 `-G 2` 相同，后续过滤率/碰撞率/`query` 断言与 md5 黄金值原样保留。
   - `multi_file.sh`：不可用时跳过 generator 子测试并 `cp` 出同名 `${pref}_m15_s2M_zip.histo`，
     脚本末尾的 `check ${pref}.md5sum` 仍逐字节比对两份直方图；「打不开文件必须失败」负例不动。
     **踩坑记录**：`${pref}_gunzip_cmds` 的 heredoc 必须留在补丁的未改动上下文里——`<<EOF` 不是 `<<-EOF`，
     终止符必须顶格；把它随 `if` 一起缩进会让 mksh 报
     `here-document delimited by end-of-file (wanted 'EOF')` / `syntax error: unexpected end of file`，
     整条测试以 exit 2 失败（本轮真机实测踩过，故 0003 改为在 heredoc **之后**开始包 `if`）。
   - `unit_tests.sh`：不可用时用 `--gtest_filter` 排除 `TmpPipes.CreateDestroy`、`TmpPipes.Discard`、
     `GeneratorManager.OneLiners`（`--gtest_list_tests` 前后差实测正好这 3 个），
     其余用例全量运行；管道可用的平台上这三个用例照常执行（不是无条件关测试）。
4. `0005-unit_tests-test_stream_iterator.cc.patch` — 单元测试硬编码 `/tmp` 建临时目录，OHOS `/tmp` 只读（EROFS）。
   改为 `TMPDIR → /tmp → .` 依次尝试（E002），与 `jellyfish::tmp_pipes` 自身的回退策略一致。
5. `0007-unit_tests-test_misc.cc.patch` — `unit_tests/test_misc.cc` 用 `std::bind2nd`（C++11 起弃用、C++17 移除），
   OHOS 工具链 `cppstd=17` + libc++ 下编译期即报 `no member named 'bind2nd'`。用等价 lambda
   （`[i](int v) { return std::less<int>()(v, i); }`）改写，比较语义不变；上游 2.3.1 已自行移除该用法。

## 四、上游测试账目

`conanfile.py build()` 里先 `make -j1` 再 `make -j1 check`（非 0 退出即构建失败、出不了包），
并从各测试自己的 `.trs` 汇总出 `UPSTREAM 'make check' RESULTS` 一行、从 gtest 的 `.log` 汇总
`UPSTREAM UNIT TESTS unit_tests.log` 一行——automake 会把每个测试脚本的 stdout 单独收进
`tests/*.log`，不主动回显就永远进不了 conan 日志，也就没法给 PR 表格取数。

### 实跑账目（真机，2026-09-21 23:32:49 → 23:47:17 CST，`CREATE_EXIT:0`）

automake 汇总（15 个注册 TESTS 全执行）：

```
# TOTAL: 15   # PASS: 10   # SKIP: 5   # XFAIL: 0   # FAIL: 0   # XPASS: 0   # ERROR: 0
PASS: tests/generate_sequence.sh   PASS: tests/parallel_hashing.sh   PASS: tests/merge.sh
PASS: tests/bloom_filter.sh        SKIP: tests/big.sh                PASS: tests/subset_hashing.sh
PASS: tests/multi_file.sh          PASS: tests/bloom_counter.sh      PASS: tests/large_key.sh
SKIP: tests/sam.sh                 PASS: tests/small_mers.sh         SKIP: tests/swig_python.sh
SKIP: tests/swig_ruby.sh           SKIP: tests/swig_perl.sh          PASS: unit_tests/unit_tests.sh
```

内置 gtest（`unit_tests.log`，由 `conanfile.py::_report_unit_test_totals()` 回显进 conan 日志）：

```
Named pipes unavailable: excluding mkfifo-based gtest cases
[==========] Running 51310 tests from 52 test cases.
[==========] 51310 tests from 52 test cases ran. (94761 ms total)
[  PASSED  ] 51310 tests.
```

口径核对（防「少报」）：`bin/test_all --gtest_list_tests` 未过滤为 **51313** 个用例（55 个 suite），
带 `--gtest_filter=-TmpPipes.*:GeneratorManager.OneLiners` 为 **51310**，差值恰为被排除的 3 个
（`TmpPipes.CreateDestroy`、`TmpPipes.Discard`、`GeneratorManager.OneLiners`）。PR 正文的上游表按 51313 声明、适配后表按 51310 记。

## 五、真机验证

- 设备：HarmonyOS PC aarch64（`uname -s = HarmonyOS`），Conan 2.29.1，profile `ohos-aarch64`（host == build）
- 隔离缓存：`CONAN_HOME=~/work/psj/ch-jellyfish`（只从 `~/.conan2` 拷 profiles/settings.yml/global.conf/remotes.json，
  未写共享缓存；起跑前 `pgrep` 确认无他人 `conan create`，被占用时按 10 min 轮询等待而非抢占、更不 SIGTERM 别人）
- 配方 rev `48d56d89a329eca0a88421faefa4b675`，包 ID `21b17f8b2bc0e9511e276e3d57a23893067cefe5`，
  包 rev `17174b04d41a561c6eeb843d894d106c`
- `CREATE_EXIT:0`；上游 `# TOTAL: 15 / # PASS: 10 / # FAIL: 0 / # ERROR: 0`（5 个 SKIP 全为上游自身 `exit 77`），
  其内层 `[  PASSED  ] 51310 tests` 0 失败
- 消费者 `test_package/test.sh`：`ASSERTIONS: 11, FAILURES: 0`
- L1e/R34 破坏性反向验证（真机实跑）：还原态 `POS_EXIT:0`（11/11）→ 把包内 `bin/` 整个改名 `bin_hidden` →
  `NEG_EXIT:1`，`ASSERTIONS: 11, FAILURES: 9`，首条失败 `FAIL: jellyfish --version did not run`，随后
  count/histo/dump/query×4/info 逐条失败 → 还原后 `POS2_EXIT:0`（11/11）。
  证明这 11 项断言真的依赖交付的 `bin/jellyfish`，而不是自我实现的空壳
- 命名管道能力取证（`tools/probes/jf13942_probe8.sh`）：`os.mkfifo()` 在 `~/work/psj` 与 `~`（HMDFS）
  均 `PermissionError: [Errno 1] Operation not permitted`，`/dev/shm` `[Errno 13] Permission denied`，
  `/tmp` `[Errno 30] Read-only file system`；绕开 Python 用 `ctypes` 直调 `libc.mkfifo()` → `rc=-1 errno=1`；
  toybox 无 `mkfifo` 命令（runner 里 `mkfifo_rc=127`、`fifo_type=absent`）
- 交付物：包内顶层 `bin include lib licenses share`；`bin/jellyfish` 571968 B，
  ELF64 小端、`e_machine=0xb7`（EM_AARCH64），`--version` → `jellyfish 2.3.0`；
  `lib/libjellyfish-2.0.a`（+ `.la`、`lib/pkgconfig/jellyfish-2.0.pc`）、`include/jellyfish-2.3.0/jellyfish/**`、
  `licenses/{LICENSE-BSD-3-Clause,LICENSE-GPL-3.0,README}`
- 两次失败-修复记录（都在真机实测到、已在配方里改掉）：
  ① 0003 最初把 `${pref}_gunzip_cmds` 的 heredoc 一起缩进 → mksh `here-document delimited by end-of-file` →
     `FAIL: tests/multi_file.sh`、`CREATE_EXIT:1`（`# FAIL: 1`）；改为在 heredoc 之后才包 `if` 后转绿。
  ② `source()` 拉官方 dist 包时 `github.com` connect 30 s 超时（conan 自带重试耗尽）→
     `Error in source() method`、`CREATE_EXIT:1`；加同一 URL 的 5 次有界重试后通过（同轮真机另测同一 URL 56 s 可下完，确认是抖动不是不可达）

## 六、平台限制（如实记录）

- **命名管道不可用**：`mkfifo(2)` 在 HarmonyOS 用户进程被拒（HMDFS EPERM(1)、`/dev/shm` EACCES(13)、`/tmp` EROFS(30)），
  toybox 也不提供 `mkfifo` 命令。因此 jellyfish 的 **generator 输入模式（`-g <cmds>` + `-G <n>`）在本平台不可用**；
  核心文件输入计数路径不受影响，且已由 `make check` 的 9 个 shell 套件与 gtest 实例覆盖。
  该限制与用户/内核策略有关（E074/E345），本次以「运行期能力探测 + 等价回退/精确排除」处理，未伪造任何通过状态。
- 可选功能未启用：htslib（SAM/BAM/CRAM）、SWIG 的 Python/Ruby/Perl 绑定；对应上游测试按上游自身逻辑 skip。
  这不是配方回避——制品仓无 htslib 发布，且启用绑定会让产物随构建机工具链漂移。

## 七、知识库对应

本包每一个坑都命中原有正式条目，无图谱 0 命中的新机制，故按路径 A 提交、不新立草稿：

| 现象 | 条目 |
|---|---|
| `config.guess` 不认 HarmonyOS | E160 |
| `umask 077` + `mktemp -d ./confXXXXXX` 在 HMDFS 属主不可写 | E011 / E114 |
| `/tmp` 只读，需 `TMPDIR` 回退 | E002 |
| 禁止创建 FIFO（`make -j` jobserver / 测试用例 / generator 输入） | E074 |
| 可写路径仍可能拒绝 FIFO；测试前逐个探测所需文件系统操作，正向检查要配破坏性反向验证 | E345 |
| 上游测试按清单分层记账（可执行 / 需额外环境 / 不可执行） | E292 |

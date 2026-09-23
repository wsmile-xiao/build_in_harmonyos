# teseq 1.1.1 适配笔记

## 编译环境
- 构建系统: autotools (configure + make，in-source 构建)
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18, aarch64-unknown-linux-ohos)
- Conan: 2.29.1 (OHOS-adapted) + profile `ohos-aarch64-device`
- 验证设备: HarmonyOS PC aarch64 真机
- 状态: built

## 软件简介
GNU teseq（Escape Sequence Illuminator）把含终端控制序列的文件翻译成人类可读
的描述，配套 `reseq` 脚本可逆向还原（可往返），常用于调试终端模拟器、
`script` typescript 去控制序列、终端演示编辑等。纯 C + POSIX shell，产物为
`bin/teseq`（C 程序）与 `bin/reseq`（由 reseq.in 生成的 Perl 脚本），另有
info 手册与两张 man page。

## 上游测试结构（configure.ac / Makefile.am 实测）
`make check` 依次执行：
1. `check-teseq`：`tests/run-tests`，28 个用例，以 `tests/<name>/expected` 比对 teseq 输出；
2. `check-reseq`：`tests/run-tests -r`，28 个用例，用 reseq 还原并与原始输入逐字节比对
   （`prompt-descript-only`、`hardstatus-color` 两个用例 vars 声明 `run_reseq=false`，
   由上游 harness 输出 `(skipped)`）；
3. `check-seqs`：`exercise-seqs` Perl 脚本，穷举各类控制序列验证 teseq 不崩溃；
4. `check-TESTS`：当 `PKG_CHECK_MODULES([libcheck], [check])` 探测到 check 时，
   `check_PROGRAMS = src/test-ringbuf src/test-inputbuf` 编译并执行（可选内部单测）。

本适配使用 ohpcd 制品仓的 `check/0.15.2`（test_requires），因此 4 组全部真实执行。

## 编译步骤

```bash
# 1. 官方 tarball 解压（conan source()，strip_root）
# 2. 应用 patches/0001-Makefile.in.patch（stamp-vti 规则改 no-op）与
#    patches/0002-configure.patch（configure 两处 umask 077 → 022）
# 3. AutotoolsToolchain 生成环境（CC/CXX/flags/PKG_CONFIG_PATH/LD_LIBRARY_PATH/TMPDIR/TEMP）
#    + PkgConfigDeps（生成 check.pc，供 configure 探测）
# 4. ./configure --disable-silent-rules ... && make -j
# 5. make check -j1（上游完整测试：28+28+exercise-seqs+2 libcheck 单测）
# 6. make install DESTDIR=<package_folder>
```

关键环境（配方 `generate()` 注入）：
- `LD_LIBRARY_PATH += <check_pkg>/lib`：check 包同时含 `libcheck.a` 与
  `libcheck.so`，链接器优先 .so，运行单测需能找到它；
- `TMPDIR/TEMP = <build_folder>/tmp`：libcheck 的 `open_tmp_file`（check_msg.c）
  探测顺序为 `TEMP → P_tmpdir → TMPDIR → "."`，而 musl 的 `P_tmpdir` 固定为
  `/tmp`（OHOS 只读），只设 TMPDIR 无效，必须设 TEMP（E547）；
- `HELP2MAN/CHECKMK/MAKEINFO=true`：OHOS 无 help2man/checkmk/texinfo，发行
  tarball 已附生成好的 man/info，覆盖为 true 防止重建。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 尾段失败：`./confObCbdF/subs1.awk: Permission denied` → `config.status` 报 `could not setup config files machinery` | HMDFS 对 umask 077 新建目录强制 setgid，得到 `drwx--S---`，owner 也无法写入；autoconf 2.69 生成的 configure/config.status 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录（E129/E112/E136） | `patches/0002-configure.patch` 将 configure 内两处 `umask 077` 改为 `umask 022`（GNU patch/toybox 均实测可应用；与 a52dec/0.7.4 已合入补丁一致） |
| 2 | `make install` 时 `doc/teseq.info` 被判定过期，调用 `makeinfo` 失败（`makeinfo: command not found`，Error 127） | 打补丁/构建会刷新 `configure` mtime → automake `doc/stamp-vti` 规则重跑 → teseq 自带 mdate-sh 不识别 HarmonyOS `ls -l` 的 ISO-8601 日期（无月份名）解析失败 → 裸 `set` 将环境变量表写进 doc/version.texi（内容损坏）→ teseq.info 先决条件变“新”触发重建 | `patches/0001-Makefile.in.patch` 把 `stamp-vti` 规则的配方改为 no-op，保持发行 tarball 自带的 version.texi/info/man 原样安装（无需 makeinfo/help2man）；同时采用 in-source 构建（同 a52dec） |
| 3 | test_package 断言失败：`teseq --help \| grep --describe` | 断言写错：teseq/reseq 实际暴露的选项是 `-t, --timings=TIMINGS/FILE`，没有 `--describe`/`--timing` | 断言改为 `--timings`（实测两二进制 --help 均含该选项） |
| 4 | test_package 往返断言失败：`reseq decoded.txt > roundtrip.bin` 打印用法 | reseq 非 replay 模式要求 **两个** 文件参数（`reseq INPUT OUTPUT`），stdout 重定向不合法；上游 harness 也是两参数调用 | 改为 `reseq decoded.txt roundtrip.bin` 后 `cmp` |
| 5 | libcheck 单测运行报 `Error loading shared library libcheck.so` | check 包同时发布 libcheck.a 与 libcheck.so，动态链接器需要 .so 所在目录 | `generate()` 将 `<check_pkg>/lib` 追加进 `LD_LIBRARY_PATH` |
| 6 | libcheck 单测运行报 `Unable to create temporary file for communication; may not have permissions`（check_msg.c:317） | libcheck `open_tmp_file` 探测顺序 `TEMP → P_tmpdir → TMPDIR → "."`，musl `P_tmpdir`=/tmp 只读，仅设 TMPDIR 无法生效（E547） | `generate()` 设 `TMPDIR=TEMP=<build_folder>/tmp`（预先 mkdir） |

## 源码修改
- `patches/0001-Makefile.in.patch`：把 automake `stamp-vti` 规则的配方改为
  `@:`（no-op），原因是该规则依赖 mdate-sh，而 mdate-sh 无法解析 HarmonyOS
  `ls` 的 ISO-8601 日期（失败时还会把环境变量表写进 doc/version.texi）；
  OHOS 无 texinfo/makeinfo，发行 tarball 已附正确的 info/man。
- `patches/0002-configure.patch`：仅改 `configure` 中两处
  `(umask 077 && ...)` → `(umask 022 && ...)`（mktemp 与 mkdir 回退两处）。
- 两个补丁均不改 C 源码、不注入 `__OHOS__`；补丁段落均为上游发行时不变量。

## 依赖版本
- 运行时依赖：无（纯 C + POSIX shell，仅 libc）
- 测试依赖：check/0.15.2（test_requires，仅 `make check` 使用）

## 验证结果

```bash
# conan-verify（G0–G4 全 PASS，profile ohos-aarch64-device）
$ python3 scripts/ohc-run.py conan-verify teseq 1.1.1 --profile ohos-aarch64-device
✅ 配方验证通过: teseq 1.1.1

# conan create 期间 make check（全部真实执行）
RUNNING TESEQ TESTS ... Ran 28 total tests / Passed: 28 / Failed: 0
RUNNING RESEQ TESTS ... Ran 28 total tests / Passed: 28 / Failed: 0  (2 skipped by harness vars)
exercise-seqs: Results: All runs look okay.
check-TESTS: # TOTAL: 2  # PASS: 2  # FAIL: 0
  src/test-ringbuf: 100%: Checks: 7, Failures: 0, Errors: 0
  src/test-inputbuf: 100%: Checks: 3, Failures: 0, Errors: 0

# 包产物
$ conan create archives/t/teseq/1.1.1 -pr:h=ohos-aarch64-device ...
teseq/1.1.1@ohpcd/stable: Package '6b129b06...' created
package_folder: bin/teseq bin/reseq share/info/teseq.info share/man/man1/{teseq,reseq}.1 licenses/COPYING

# 设备冒烟
$ bin/teseq --version | head -1
GNU teseq 1.1.1
$ printf '\033[1mBOLD\033[0m\n' | bin/teseq | bin/reseq - /dev/stdout | cmp - <(printf ...)
（test_package 内 13 条断言全部通过，含 SGR 描述生成与 reseq 往返 cmp）
```

## test_package 设计（消费者视角回归，13 断言）
teseq 是命令行工具、无编译期 API，因此 test_package 不做链接测试，而是
直接执行包内二进制：
1. `bin/teseq`、`bin/reseq` 存在且可执行；
2. `teseq --version` 输出含 `GNU teseq 1.1.1`；
3. `teseq --help`/`reseq --help` 均含 `--timings`；
4. `printf '\033[1mBOLD\033[0m\n'` → teseq 输出含 `SGR` 描述行与字面 `BOLD`；
5. reseq 两参数还原后与原始输入 `cmp` 逐字节一致（往返闭环）；
6. 1.1.1 修复的 fuzz 回归输入 `'\033!!\177'` 能即时正常退出（RC=0）。
---

## 对话记录

### 对话 #1（2026-09-20，人工协作）

- 人工确认"在现有 teseq 工作基础上继续，用 configure 补丁修复 HMDFS umask 问题"的方案。
- 人工在设备上维护/恢复反向 SSH 隧道（`ssh -N -R 2200:127.0.0.1:8022 amax@...`），
  构建、验证与提交因此可以连续执行。
- 人工保持物理设备唤醒/解锁状态，保证真机验证可信。

状态: built
---

**编译结束**: 2026-09-20 14:37
**最终状态**: built

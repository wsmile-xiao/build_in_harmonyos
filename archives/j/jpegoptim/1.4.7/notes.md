# jpegoptim 1.4.7 适配笔记

## 编译环境
- 构建系统: autotools（`configure` + 手写 `Makefile.in`；tarball 里那份 `CMakeLists.txt` 只是作者本地开发用的 Glob 构建，无安装规则，不用）
- 编译日期: 2026-09-19
- 编译器: clang 15（OpenHarmony SDK llvm，harmonybrew profile `ohos-aarch64`）
- 链接器: 默认 lld（本库不依赖 libxml2，无需 jhead 那样的 ld.bfd 绕行）
- 状态: built

## 编译步骤

1. `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
2. 配方 `source()` 拉官方 dist 包（`https://www.kokkonen.net/tjko/src/jpegoptim-1.4.7.tar.gz`，
   备用源 `https://codeload.github.com/tjko/jpegoptim/tar.gz/refs/tags/v1.4.7`，两者字节一致、同一 sha256），
   然后 `apply_conandata_patches`
3. `generate()` 出 `AutotoolsDeps` + `AutotoolsToolchain`，并把依赖的 libdir 追加进 `LD_LIBRARY_PATH`（build scope）
4. `build()` 内 `configure` + `make -j1`
5. `package()` 走 `make install`，产物 `bin/jpegoptim`
6. `test_package/` 用 `sh test.sh <绝对路径二进制> <夹具>` 跑 5 个端到端用例

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one` | tarball 自带 `tools/config.guess`（timestamp `2012-02-10`）没有 HarmonyOS 分支 | 补丁 0002 注入 `*:HarmonyOS:*:*)` 分支；补丁 0003 让 `config.sub` 两处 pattern 接受 `linux-ohos` |
| 2 | 仓库自带 `scripts/patch-autotools-ohos.pl` 对本版本「打了等于没打」 | 该脚本注入的分支以 `GUESS=${MACHINE}-unknown-linux-ohos` 赋值收尾，依赖 config.guess 主 case 之后的 `if test "x$GUESS" != x; then echo "$GUESS"; exit; fi` 兜底；这段兜底是 2015 年前后才有的，2012 版副本主 case 之后直接进 `set_cc_for_build` 编译器探测，最后以 `unable to guess system type` 收场 | 手写分支为自终止形态：`echo ${MACHINE}-unknown-linux-ohos; exit 0`（判据：`grep -c 'x$GUESS' tools/config.guess` → 0 即本代副本） |
| 3 | `config.status: error: could not setup config files machinery`（`can't create ./confXXXXXX/subs1.awk: Permission denied`） | E011（同族签名 E114）：HMDFS 上目录映射属主 UID 与进程 UID 不同，`umask 077` 建的 `drwx--S---` 临时目录连属主都不可写 | 补丁 0001 把 `configure` 里两处 `umask 077` 改成 `umask 022` |
| 4 | `make` 报 `fatal error: 'config.h' file not found` | 手写 `Makefile.in` 的编译规则是 `$(CC) $(CFLAGS) -c $<`，不给构建目录加 `-I`，即不支持 out-of-tree/VPATH 构建 | 配方用 in-source 布局：`folders.source = folders.build = "src"`（同 ncurses 做法） |
| 5 | `make -j` 卡住/报 FIFO 权限 | HMDFS 不允许创建 jobserver 管道（E074） | `autotools.make(args=["-j1"])` |
| 6 | 测试图不能用 `cjpeg` 现生成 | OHOS 上 libjpeg 自带工具的 `DT_RPATH` 是相对路径，加载器按 CWD 解析成 `../libjpeg.so` 而失败 | 夹具以 base64 写在 `test_package/conanfile.py` 里，由 conan 自身的 Python 落盘（不依赖外部解释器/工具） |
| 7 | `/tmp` 不可写 | OHOS 根文件系统只读挂载 | `test.sh` 的临时目录用 `${TMPDIR:-$HOME/tmp}` 下带 `$$` 的子目录，`trap` 清理 |

## 源码修改

| 文件 | 原因 | 方式 | 补丁 |
|------|------|------|------|
| `configure` | E011 临时目录不可写 | 编辑：两处 `umask 077` → `umask 022` | 0001 |
| `tools/config.guess` | 识别 HarmonyOS 三元组 | 编辑：注入自终止的 `*:HarmonyOS:*:*)` 分支 | 0002 |
| `tools/config.sub` | 接受 `-linux-ohos` | 编辑：两处 pattern 增加 `linux-ohos*` / `-linux-ohos*` | 0003 |

三个补丁都用 `patch -p1 --dry-run` 在 pristine tarball 上验过可干净应用（无 fuzz）。

## 依赖版本

- libjpeg/10（ohpcd 制品仓已发布，满足 R36）
- clang 15（OpenHarmony SDK，profile `ohos-aarch64`）

## 验证结果

真机：HarmonyOS / HongMeng Kernel 1.12.0 / aarch64（Toybox 用户态），
profile `ohos-aarch64`（os=OHOS 6.0，clang 15 取自 harmonybrew 的 `ohos-sdk@26.0.0.18`）。

```
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
CREATE_EXIT:0

jpegoptim/1.4.7: Sources correctly downloaded from
    https://www.kokkonen.net/tjko/src/jpegoptim-1.4.7.tar.gz
libjpeg/10: Downloaded recipe revision b07f96290a88f086bad3124186e29fc7  (remote ohpcd)
checking build system type... aarch64-unknown-linux-ohos
checking host system type...  aarch64-unknown-linux-ohos
config.status: creating Makefile
config.status: creating config.h
jpegoptim/1.4.7: RUN: make -j1
jpegoptim/1.4.7: Created package 'd5cfe388d43c3a56a59395e6c64c07fc5f732c56'
                 (recipe 2901bbbc7495477f7b4d95079a0cbd54, pkg rev f89f30902892ac2c04ca63996660a3c7)

# test_package（安装包内的真实二进制）
PASS: version banner
PASS: usage text
PASS: trial decode (16x16, [OK], totals, file untouched)
PASS: lossless optimize (319 -> 319 bytes, markers intact)
PASS: --strip-all drops COM segment (319 -> 303 bytes)
All tests passed.

$ bin/jpegoptim --version
jpegoptim v1.4.7  aarch64-unknown-linux-ohos (Sep 19 2026)
libjpeg version: 10  25-Jan-2026

$ readelf -d bin/jpegoptim | grep NEEDED
  0x0000000000000001 (NEEDED)       Shared library: [libc.so]
```

产物：`bin/jpegoptim` + `share/man/man1/jpegoptim.1`；上游测试 0/0（无套件），
消费者测试 5/5（17 项断言）。

## 测试四维账本

| 维度 | 数量 | 说明 |
|------|------|------|
| 上游静态声明 N_static | 0 | `find . -maxdepth 3 -type d \( -name 'test*' -o -name 'spec*' \) \| wc -l` → 0；`grep -cE '^[[:space:]]*(check\|test\|distcheck)[[:space:]]*:' Makefile.in` → 0；`grep -cE 'add_test\|enable_testing\|BUILD_TESTING' CMakeLists.txt` → 0；`grep -rlE 'BOOST_AUTO_TEST_CASE\|TEST_CASE\(\|^[[:space:]]*TEST\(' . \| wc -l` → 0；`configure.in` 无 `AM_INIT_AUTOMAKE`，故无 `make check` |
| 实际执行 N_executed | 0 | 上游没有任何可执行测试套件 |
| 跳过/未执行 | 0 | — |
| 新增消费者测试 N_consumer | 5 | `test_package/test.sh` 5 个用例 / 17 项断言（`grep -c '^echo "PASS' test.sh` → 5、`grep -c 'FAIL:' test.sh` → 17） |

## 注意事项

- jpegoptim 只处理 JPEG，默认原地改写；`-n` 是「只试算不写」，`-o` 只在配合 `-d` 时有意义
- 长选项齐全：`--version`（等价 `-V`）、`--help`（`-h`，走 `print_usage()` 后 `exit 0`，输出在 stderr）、`--strip-all`（`-s`）、`--totals`（`-t`）、`--quiet`（`-q`）
- 本版本是单二进制 CLI 工具：`package_type = "application"`、`package_info` 里 `libs = []`、`bindirs = ["bin"]`，并按 R38 在软件级 `commands.json` 登记版本（与已合入的 1.5.5 共用该文件，未删除既有版本条目）
- 上游 1.5.x 起改 CMake 且默认 `USE_MOZJPEG=1`（构建期下载 MozJPEG）；1.4.7 走 autotools，两版配方互不影响

**编译结束**: 2026-09-19
**最终状态**: built

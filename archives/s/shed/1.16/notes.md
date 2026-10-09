# shed 1.16 适配笔记

## 编译环境

- 构建系统: autotools（上游发布包自带 autoconf 2.71 生成的 configure / Makefile.in）
- 编译日期: 2026-09-28
- 编译器: OHOS SDK clang 15（aarch64-unknown-linux-ohos），CI profile `ci/conan/profiles/ohos-aarch64`
- 本地构建机: x86_64 runner（qemu-aarch64 binfmt），交叉目标 aarch64-linux-ohos
- 状态: built（`conan-verify` 通过；交付产物的运行验证由 aarch64 OHOS CI 执行，见「鸿蒙特有测试」）

## 上游与源码

- 项目: shed — Simple Hex EDitor，C + ncurses 的全屏十六进制编辑器（类 pico 操作），GPL-2.0-or-later
- 主页: https://sourceforge.net/projects/shed/
- 源码: `https://downloads.sourceforge.net/project/shed/shed/shed%201.16/shed-1.16.tar.gz`（SourceForge 官方发布文件）
- sha256: `39fdf7d1bed6527d801f71b84e505d02e7a931799250f16d36db291e54635883`，与 SourceForge 文件页公布值一致，下载后本地复核
- 语言预检: `lang-preflight` 判定 c（shed.c + util.c，主体 100%），与任务 cpp 同族，继续

## 前置检查

- W0 依赖: `conan download ncurses/6.6 -r=ohpcd --only-recipe` → 已发布（revision 3dcfd3b6…）；仓库内引用最多的 ncurses 版本也是 6.6
- W0b 历史: 仓库无 shed 历史归档
- 配方底稿: `recipe-search shed -b make -d ncurses` 无可用配方（唯一候选 levee/4.0 只有本地残留、无配方）；
  配方按 xtail/2.1（autotools CLI）、cdargs/1.0.0 与 termbox/1.1.4（OHOS ELF 自签名）、ptpd/remctl（configure 临时目录）先例手写

## 适配步骤

1. `init-build` 下载解包；`.work` 与 `.orig` 为硬链接（草稿 E543-draft-7C1A），解包后立即逐文件复制断链，并按 `.orig` 恢复时间戳（否则 automake 会重跑 aclocal/autoconf）。
2. 手工交叉编译：`CC=clang CPPFLAGS=-I<ncurses>/include LDFLAGS=-L<ncurses>/lib LIBS=-lncursesw ./configure --prefix=/ --host=aarch64-linux-ohos && make` 一次通过（仅 2 条上游原型告警）。
3. 在 `.work` 修改 `shed.c`（stdin 缓冲文件），`refresh-patch --auto` 生成 `patches/0001-shed.c.patch`。
4. 手写 `conanfile.py` / `conandata.yml` / `test_package/`，`conan-verify` 实际执行的 G0–G3 通过（G4/L2/L4/L5 被跳过，见「验证结果」），finish 的 W3 本地 CI 通过。
5. 用 conan create 与 test_package 实际编出的 `.o` 静态重链后，在本机 qemu 下以非 root 身份实跑全部消费者用例（见「验证结果」）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `producer \| shed` 直接退出：`shed: tmpfile() failed.` | shed 用 `tmpfile()` 缓冲管道输入；OHOS musl 的 `tmpfile()` 写死 `/data/local/tmp/tmpfile_XXXXXX`（NDK `libc.a` 的 `tmpfile.o` 字符串实证），不读 `TMPDIR`，普通进程无权写该目录（E272 同源） | 补丁 0001：`$TMPDIR` 非空时在其下 `mkstemp()` + 立即 `unlink()`（与 `tmpfile()` 同为匿名文件），未设置时仍回落 `tmpfile()`；报错附带 `strerror(errno)`。无平台宏 |
| 2 | 本机 W3（build/host 同为 OHOS profile）configure 报 `cannot run C compiled programs. If you meant to cross compile, use --host` | Conan 判定非交叉，不传 `--host`；autoconf 2.71 在非交叉模式必须执行 conftest，x86 上执行 OHOS 动态 ELF 失败（缺 `/lib/ld-musl-aarch64.so.1`，E544） | `settings.os == OHOS` 且 Conan 未判交叉时只传 `--host=aarch64-linux-ohos`、不写死 `--build`（草稿 cvsgraph-1.7.0-autotools-no-canonical-host 与 E543-draft-419E 的同款处置）：configure 进入 `cross_compiling=maybe`，设备上 conftest 能跑即原生，x86 上跑不了即交叉。shed 的 `configure.ac` 无 `AC_CANONICAL_HOST`，不调用 config.sub/config.guess，所以不需要 E543-draft-419E 里补 config.* 的补丁 |
| 3 | CI 构建目录在 HMDFS：config.status 用 `umask 077 && mktemp -d` 建 0700 临时目录，目录内建文件被拒（E129/E114） | HMDFS 对 0700/setgid 临时目录的权限处理 | OHOS 上 `replace_in_file` 改为普通 `mkdir "./conf$$"`（remctl/pipexec 同款），strict 匹配，文本变化即构建失败而非静默 |
| 4 | `AC_CHECK_LIB(ncurses, initscr)` 结果为 no | ncurses/6.6 只发布宽字符库 `libncursesw.a` 等，无 `libncurses` | 不在依赖包目录造软链；由 `AutotoolsDeps` 提供 `LIBS=-lformw -lmenuw -lpanelw -lncursesw`，检测失败不影响最终链接 |
| 5 | G0 提示已知风险 E490（发布包 autotools 脚本执行位丢失） | 部分 OHOS 路径不保留 POSIX 执行位 | configure 前对 `configure/compile/depcomp/install-sh/missing` 补 `+x`（G0 的判定表只识别 E007/E011/E090/E092，处理后仍提示，属非阻塞告警） |
| 6 | SDK 链接器插入的 `.codesign` 段不被 OHOS 加载器认可（E077/E077B） | — | `package()` 中对 `bin/shed` 执行 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`；调用时剔除 buildenv 注入的 `LD_LIBRARY_PATH`（否则签名工具加载到 SDK libc++，见 DRAFT-binary-sign-tool-buildenv-ldlibrarypath）；工具不存在时告警跳过（本机 x86 即此分支）。test_package 对新链接的测试程序同样处理 |
| 7 | 本机以 root 实跑 ncurses 界面：`ncurses: cannot initialize terminal type ($TERM="vt100"); exiting`，`TERMINFO` 已正确指向可读 terminfo | 据 ncurses 6.6 源码与库内符号推断：ohpcd 构建时 configure 把系统判为非多用户系统，`USE_ROOT_ENVIRON` 未定义，`_nc_env_access()` 对 uid 0 返回假，`TERMINFO/TERMINFO_DIRS/~/.terminfo` 全部失效（`libncursesw.a` 里 db_iterator/home_terminfo/write_entry 三个目标文件通过 `use_terminfo_vars()` 引用 `_nc_env_access`——两个 `USE_*_ENVIRON` 宏都定义时它是常量 1、不会有这些引用；`access.o` 含仅在 `USE_ROOT_ACCESS` 未定义时才编译的 `_nc_safe_fopen`；comp_error 的引用是 `--with-trace` 下的直接调用，不计；root 失败、nobody 通过的实测与之一致） | 本地实跑降权为 `nobody`（`setpriv`）；CI worker 若以非 root 运行则不受影响（其 uid 未直接核实，CI 日志须确认用例确实执行）。沉淀知识草稿 **E429-draft-5ED1**（root 下失败这一现象与已合入的 DRAFT-12001 旁注相互印证，见草稿查重节） |
| 8 | 首版配方下 test_package 的 `conanrunenv` 只有 `PATH`，没有 `TERMINFO` | application 包对静态库依赖默认 `run=False`，消费者图把 ncurses 列为 Skipped binaries，其 runenv 不注入；但 terminfo 数据库仍在 ncurses 包内（DRAFT-tinyirc 同源） | `requires("ncurses/6.6", run=True)`（tack/tinyirc 先例），重跑后 `conanrunenv` 导出 `TERMINFO`/`TERMINFO_DIRS` |

## 源码修改

- `patches/0001-shed.c.patch`（+34/-2，`patch_type: portability`）：新增 `shed_tmpfile()`，stdin 模式改用它创建缓冲文件
  （路径用带长度的 `snprintf` 拼接——首版用 `sprintf` 被 W3 L4 危险函数扫描告警，已改）；
  `$TMPDIR` 已设置时只用 `$TMPDIR`（不回落），使「`TMPDIR` 是否生效」可被测试区分；未设置时行为与上游一致（`tmpfile()`）。
- 配方内对 configure 的两处临时目录文本替换仅在 `os == OHOS` 时执行，不产生补丁文件。

## 依赖版本

- ncurses/6.6（ohpcd，静态宽字符库），`run=True`：运行期 `TERMINFO` 由其 runenv 经 `conanrun` 提供（问题 8，已在 test_package 生成的 `conanrunenv` 中核实）

## 上游测试清点（R51）

| 项 | 结果 | 证据 |
|---|---|---|
| 测试目录 | 0 | 发布包 21 个文件，无 `tests/`、`test/`、`t/` |
| ctest/pytest 注册 | 不适用 | 无 CMake/Python 构建 |
| `make check` 注册用例 | 0 | `Makefile.am` 无 `TESTS`/`check_PROGRAMS`；配方在 build() 中实际执行 `make check`，W3 日志 `reports/w3-local-ci.log` 中为 `make: Nothing to be done for 'check'.` |
| 上游用例数 N / 适配后可运行 N′ / 通过率 | 0 / 0 / 不适用 | 上游确无测试 |

补全：test_package 新增 7 个消费者用例（37 条断言），其中 2 个为鸿蒙特有用例，见下。

## 验证结果

### conan-verify 与 W3

- conan-verify：G1、G0、G2（conan create 干净构建 + test_package 编译）、G3 实际执行并通过；报告里 G4/L2/L4/L5 记为 PASS，
  但实际为「无法找到程序包 ID / 无 cache 路径」而跳过（框架取包 ID 的问题，已写入 SKILL_FEEDBACK），不作为验证依据。
- finish W3（`ci/conan/build_and_test.sh`）：L0、L1（test_package 编译 + test()）、L1e 破坏性反向验证、L4、L5 为 pass；
  L2 冒烟为 skip——x86 上无法执行 OHOS 动态 `bin/shed --version`。
- 本机 test() 走 x86 分支，输出 `WARN: x86 runner: shed pty consumer tests are executed on the aarch64 OHOS builder, not here`（原因见下节）。

### 本地实跑（同源 .o 静态重链 + qemu-aarch64，非 root）

x86 runner 跑不起 OHOS 动态产物（E544：缺 `/lib/ld-musl-aarch64.so.1`）。做法：取 **conan create 编出的**
`shed.o/util.o` 与 **test_package 编出的** `test_shed_consumer.c.o/test_shed_ohos.c.o`，用同一 OHOS clang 加 `-static`
重链，`setpriv --reuid=nobody` 下运行（问题 7）：

```
$ setpriv --reuid=nobody --regid=nogroup --clear-groups env HOME=$D TERMINFO=$D/terminfo ./test_shed_consumer $D/shed $D/work
shed consumer tests: 5/5 passed          exit=0
$ setpriv --reuid=nobody --regid=nogroup --clear-groups env HOME=$D TERMINFO=$D/terminfo ./test_shed_ohos $D/shed $D/work
shed OHOS-specific tests: 2/2 passed     exit=0
```

对照组：

- 同一 `test_shed_ohos` 驱动**未打补丁**源码构建的 shed：0/2（`tmpfile() failed.`，本机同样没有 `/data/local/tmp`），exit=1——用例确实覆盖适配点；
- 以 root 运行 `test_shed_consumer`：1/5（进入 curses 的 4 个用例均 `cannot initialize terminal type`），即问题 7。

**说明**：以上是同源目标文件的静态重链副本，**不等于交付产物（动态链接 musl 的 `bin/shed`）已在本地运行**；
交付产物由 CI 在 aarch64 OHOS 构建机上经 test_package 实际执行，**本地未实跑、由 CI 执行**。

## 鸿蒙特有测试（rule12）

| 项 | 内容 |
|---|---|
| 用例文件 | `test_package/test_shed_ohos.c`（共享 `test_package/shed_pty.h`），CMake 构建，`test()` 中执行 |
| 消费者流程 | Conan 以 OHOS profile 消费本包 → 编译 C 消费者程序 → 以包内 `bin/shed` 为被测对象：stdin 接管道、终端接伪终端（24x80，`TERM=vt100`，terminfo 来自 ncurses runenv），写入 16 字节并按键 `x` 退出 |
| 用例 1 `stdin_pipe_buffered_in_tmpdir`（8 条断言） | 标题行 `(stdin) (read only)`、16 位偏移表头、16 行字节逐列（asc/hex/dec/oct/bin）与状态行 `0/16 (dec)` 精确比对；运行中与退出后 `$TMPDIR` 均无残留（匿名缓冲）；终端按键在 stdin 为管道时仍生效，退出码 0 |
| 用例 2 `tmpdir_honoured_for_stdin_buffer`（3 条断言） | `$TMPDIR` 指向不存在目录时退出码 1，报 `shed: tmpfile() failed (No such file or directory).`，无旁路文件——与用例 1 仅 `TMPDIR` 不同，证明缓冲确实建在 `$TMPDIR` |
| 覆盖的鸿蒙差异 | OHOS musl `tmpfile()` 写死 `/data/local/tmp` 且不读 `TMPDIR`（补丁 0001 的代码路径） |
| 执行证据 | 本地：同源 `.o` 静态重链 + qemu（非 root）2/2，未打补丁对照 0/2；交付产物：本地未实跑、由 CI 执行 |
| 统计 | 鸿蒙特有测试 N = 2 |

通用消费者用例 `test_package/test_shed_consumer.c`：5 个用例 / 26 条断言——命令行契约（`--version` 输出
`shed 1.16 (lfs)`、`--help`、文件不存在、多余参数）、首屏渲染（标题/表头/16 行/状态/帮助行）、hex 列搜索 `7F FF` 与
asc 列搜索 `OS`（跳过 `OH` 部分匹配）、`j 3` 跳转 + hex 编辑 `7a` 写回磁盘（其余 15 字节不变）、`d` 导出 dump 并逐字节比对。

## 注意事项

- 交付的 `bin/shed` 动态链接 musl，ncurses 静态链入；`TERMINFO` 需指向 ncurses 包内的 terminfo 数据库（`conanrun` 导出）。
- 以 root 在设备上运行时 ncurses 会忽略 `TERMINFO`（问题 7），需以普通用户运行。
- 管道模式建议设置 `TMPDIR`（如 `$HOME/tmp`）；未设置时沿用 libc `tmpfile()`，在 OHOS 上会失败并给出 errno。
---

**编译结束**: 2026-09-29 01:50
**最终状态**: built

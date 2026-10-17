# cdtool 2.1.8-release 适配笔记

## 编译环境

- 构建系统: autotools（上游 tarball 自带 pre-generated `configure`，Autoconf 2.59+ 生成）
- 编译日期: 2026-09-13
- 编译器: clang 15（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标平台: HarmonyOS PC (OHOS) aarch64（conan profile `ohos-aarch64`，
  `os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 libcxx=libc++ cppstd=17`）
- 状态: built（`conan create` + `test_package` 通过，尚未经 CI release 上传）

## 命名与"重复包"声明

- 上游项目名、Debian 包名、平台任务卡软件名**均为单数 `cdtool`**（上游官网正文
  "cdtool is a free software package…"，tarball `cdtool-2.1.8.tar.gz`）。
- 版本串 `2.1.8-release` 取自 Debian 上游版本号（`cdtool_2.1.8-release-9.dsc` 的
  `Version: 2.1.8-release-9`）；其 orig tarball 与官网 tarball
  **sha256 逐字节相同**（`73de81ea…76a21`，116847 B）。
- 仓库内另有历史归档 `archives/c/cdtools/2.1.8/`（任务 contrib-4078，
  2026-08-28 完成，PR #6850 已合并，制品 `cdtools/2.1.8` 已发布到 ohpcd），
  其源码与本包**是同一份上游 tarball**。两者是不同 Conan ref：
  `cdtools/2.1.8`（已发布）与 `cdtool/2.1.8-release`（本包）。
- 本包按平台任务卡与 CI L0n 分支名门禁（分支 `feat/cdtool-2.1.8-release`，
  要求"分支名去前缀 == 包目录名-版本"精确匹配）取 `cdtool` + `2.1.8-release`。
  如实声明上述关系，不做隐瞒。

## 编译步骤

1. 源码：`https://hinterhof.net/cdtool/dist/cdtool-2.1.8.tar.gz`
   （sha256 见 `conandata.yml`；HTTP 会 302 跳 HTTPS，最终 200）
2. 解包后确认主体语言为 C（`*.c`/`*.h` 共 4129 行），
   `ohc-run.py lang-preflight` → `detected=c`
3. W0 依赖检查：**零第三方依赖**。`configure.ac` 仅
   `AC_CHECK_LIB(socket, connect)`（musl 下 socket 在 libc，探测失败即不追加
   `-lsocket`），头文件 `getopt.h`/`mntent.h`/`linux/cdrom.h` 由 OHOS sysroot 提供。
   无 `requires()`，故无 `conan install --build=never` 需求。
4. 设备真实构建（三条真实错误逐条驱动补丁，见下）：
   ```bash
   conan create archives/c/cdtool/2.1.8-release \
     -pr:h=<MAIN_REPO>/ci/conan/profiles/ohos-aarch64 \
     -pr:b=<MAIN_REPO>/ci/conan/profiles/ohos-aarch64 --build="cdtool/*"
   ```
5. `test_package` 消费测试（16 断言）自动执行并全过。

## 遇到的问题与解决方案（全部由设备上第一条真实错误驱动）

### 1. configure 静默失败 → `make: No targets specified and no makefile found`

**第一条真实错误**（首轮 `conan create`，未打补丁）：

```
configure: creating ./config.status
./config.status: line 441: ./confstat2m7Fln/subs.sed: Permission denied
./config.status: line 506: ./confstat2m7Fln/subs.frag: Permission denied
./config.status: line 718: ./confstat2m7Fln/out: Permission denied
rm: ./confstat2m7Fln/stdin: Permission denied
mv: bad './confstat2m7Fln/out': Permission denied
./config.status: line 891: ./confstat2m7Fln/config.h: Permission denied
mv: bad './confstat2m7Fln/config.h': Permission denied
...
make: *** No targets specified and no makefile found.  Stop.
```

- **根因**：autoconf 生成的 `configure` 用 `tmp=\`(umask 077 && mktemp -d -q
  "./confstatXXXXXX") 2>/dev/null\`` 建 `config.status` 的临时目录。OHOS 文件系统
  上 0700 目录对构建进程不可写（知识库 **E011**：HMDFS UID 映射 + setgid），
  `config.status` 的重定向全部失败，`config.h`/`Makefile` 未生成。
- **最危险的一点**：`configure` 自身**返回 0**（静默失败），错误推迟到 `make`
  才以"找不到 makefile"暴露，极易误判为编译器缺失。**只看退出码会被骗**，
  必须核对产物文件（`config.h`/`Makefile`）是否真实生成。
- **修复**：补丁 `0001-configure-umask-000.patch`，两处 `umask 077` → `umask 000`。

### 2. `commands.c` 缺 `<fcntl.h>` → `use of undeclared identifier 'O_RDONLY'`

**第二条真实错误**（打完 0001 后）：

```
/data/service/hnp/bin/clang -O3 -Wall -DNDEBUG  -c -o commands.o commands.c
commands.c:59:15: warning: call to undeclared function 'open'; ISO C99 and later
                  do not support implicit function declarations
commands.c:59:27: error: use of undeclared identifier 'O_RDONLY'
commands.c:59:38: error: use of undeclared identifier 'O_NONBLOCK'
1 warning and 2 errors generated.
make: *** [<builtin>: commands.o] Error 1
```

- **根因**：`commands.c:59` 用 `open(cddev, O_RDONLY | O_NONBLOCK)`。
  该文件已 `#include <sys/file.h>`，但 **OHOS musl 的 `sys/file.h` 不引入
  `fcntl.h`**（本机最小探针实测：仅 `#include <sys/file.h>` 时 `O_RDONLY` 与
  `O_NONBLOCK` 均 undeclared），与 glibc 行为不同。
- **修复**：补丁 `0002-commands-include-fcntl.patch`，在 `#include <stdio.h>` 后补
  `#include <fcntl.h>`。
- **边界（实测澄清）**：`cdown.c:137` 同样使用 `O_NONBLOCK` 且同样未包含
  `fcntl.h`，但在本任务构建中**不报错**（其 include 链已传递引入相关定义）。
  因此**没有**对 `cdown.c` 补 `fcntl.h` —— 补丁只针对真实报错的文件，
  不做"看起来同类"的预防性修改。用已生成 `config.h` 的构建副本直接做
  `clang -fsyntax-only cdown.c` 复核，首条错误是下文第 3 条的 `getline` 冲突。

### 3. `cdown.c` 自定义 `getline()` 与 musl POSIX `getline()` 冲突

**第三条真实错误**（打完 0001/0002 后，`clang -fsyntax-only` 探针与 `make` 一致）：

```
cdown.c:343:7: error: conflicting types for 'getline'
char *getline(void) {
      ^
…/sysroot/usr/include/stdio.h:155:9: note: previous declaration is here
ssize_t getline(char **__restrict, size_t *__restrict, FILE *__restrict);
cdown.c:454:21: error: too few arguments to function call, expected 3, have 0
  message = getline();
```

- **根因**：`cdown.c` 自定义 `char *getline(void)`（从 CDDB 服务器读一行），
  与 musl `stdio.h` 声明的 POSIX.1-2008 `ssize_t getline(char**, size_t*, FILE*)`
  同名冲突。
- **修复**：补丁 `0003-cdown-getline-rename.patch`，把自定义函数定义、
  **全部 13 处引用**（含函数头注释里的两处说明文字）统一改名为
  `cdtool_getline`，避免与系统 `getline` 冲突。

### 4. OHOS `/tmp` 只读

- `configure` 的编译器探测（`ac_link` 编译并运行 conftest）需要可写临时目录，
  否则探测失败并静默降级。配方内所有 `configure`/`make`/`make install` 调用
  一律显式 `TMPDIR=<build_folder>`（cdrecord 同款教训）。

### 5. make jobserver

- `make -j1` 固定单任务：规避 OHOS 上 `make -j>1` 创建 jobserver fifo 被拒
  （catdoc/boa 同款）。

## 源码修改（补丁）

| 补丁 | 修改内容 | 错误依据 |
|------|----------|----------|
| `0001-configure-umask-000.patch` | `configure` 中两处 `umask 077` → `umask 000` | `config.status: ./confstatXXXXXX/...: Permission denied`，`make: No targets specified and no makefile found` |
| `0002-commands-include-fcntl.patch` | `commands.c` 补 `#include <fcntl.h>` | `commands.c:59: error: use of undeclared identifier 'O_RDONLY' / 'O_NONBLOCK'` |
| `0003-cdown-getline-rename.patch` | `cdown.c` 自定义 `getline` → `cdtool_getline`（定义 + 13 处引用 + 注释） | `cdown.c:343: error: conflicting types for 'getline'`；调用点 `too few arguments to function call, expected 3, have 0` |

补丁生成方式：手工 GNU `diff -u`（`a/`/`b/` 前缀，默认 strip=1），
每个补丁均用 **conan 实际执行路径的 `patch_ng` 库调用**验证
（`patch_ng.fromfile(f).apply(strip=1, root=<独立 pristine 副本>)`），并与修改副本
`cmp` 逐字节比对一致。验证与生成使用两份独立副本（`patch_ng.apply()` 是就地改写）。

## 安装布局（实测，与上游 `Makefile.in` 的 `install-files`/`install-links` 对应）

| 路径 | 内容 |
|------|------|
| `lib/cdtool/cdtool` | **唯一真实二进制**（55744 B，aarch64 PIE，`/lib/ld-musl-aarch64.so.1`，`NEEDED` 仅 `libc.so`） |
| `bin/` 10 个别名 | `cdplay cdpause cdstop cdclose cdeject cdir cdinfo cdreset cdvolume cdshuffle` → 相对符号链接 `../lib/cdtool/cdtool`（argv[0] 分派） |
| `bin/` 5 个独立产物 | `cdctrl`(ELF) `cdown`(ELF) `cdtool2cddb`(ELF) `cdadd`(`#!/bin/sh`) `cdloop`(`#!/bin/sh`) |
| `share/man/man1/` | 16 份：6 份实体（cdctrl/cdloop/cdadd/cdown/cdtool/cdtool2cddb）+ 10 份别名符号链接 → `cdtool.1` |

**注意**：`bin/` 下**没有**名为 `cdtool` 的入口（上游设计如此），
`package_info()` 不得想当然声明 `bin/cdtool`。

## 依赖版本

零第三方依赖（socket 由 libc 提供；`getopt.h`/`mntent.h`/`linux/cdrom.h` 由
OHOS sysroot 提供）。

## 上游测试

上游**无自动化测试**，如实声明 **TOTAL=0**，不伪造通过率。审计三项实跑证据：

```bash
# ① tarball 顶层无 tests/ test/ 目录（顶层 39 个条目，全为源文件/文档/手册）
python3 -c "import tarfile; print(sorted({n.split('/')[1] for n in tarfile.open('<tgz>').getnames() if len(n.split('/'))>1}))"
# ② Makefile.in 无 check/test 目标（实跑零命中）
grep -nE '^(check|test)[a-zA-Z_-]*[[:space:]]*:' Makefile.in
#    实际 target: build / debug / cdtool / cdctrl / cdown / install /
#                 install-files / install-links-local / install-links / clean / distclean
# ③ configure.ac 无测试宏（实跑零命中，全文 88 行）
grep -nE 'AC_CONFIG_TESTDIR|AM_PATH_|AX_|AC_TEST|TESTS' configure.ac
```

替代性功能验证：构建期对 4 个刚构建的二进制做 `-V`/`-h` 冒烟
（`cdtool -V` / `cdctrl -h` / `cdown -V` / `cdtool2cddb -h`，均无需光驱与网络），
消费测试再对已安装产物做 16 项断言（含 5 个命令真实运行）。

## 验证结果

- `conan create`（含 test_package）：见 `reports/conan-create-log.md`（逐字日志）
- `test_package` 消费测试：16 断言全 PASS（见 `reports/`）
- `conan-verify` G0-G4 / L2 / L4 / L5：见 `reports/conan-verify-report.md`
- 上游测试 TOTAL=0（无套件），如实声明不判 PASS

## 注意事项

- 上游发布的 2.1.8 tarball 内 **pre-generated `configure` 来自更早的
  `configure.ac`**：`configure` 里 `PACKAGE_VERSION='2.1.8pre3'`（第 272 行），
  而包内 `configure.ac` 已写 `AC_INIT(CDTOOL, 2.1.8, …)`。构建走 pre-generated
  `configure`（不重新 autoreconf），故**二进制自报版本串是 `2.1.8pre3`**
  （`cdplay -V` 输出 `CDTOOL 2.1.8pre3`）。测试断言**不可绑死**上游自报版本串，
  本包断言只校验 `CDTOOL` 字样与 rc。
- 本包是**外设/硬件类工具**：核心功能（CD-ROM 播放/停止/弹出等 ioctl）需要真实
  光驱，OHOS 设备无光驱，无法真机验证。消费测试只覆盖安装布局、产物属性与
  版本/用法路径。**该缺口如实声明，不写成 PASS。**
- 上游 `configure` 是生成物：本包对它打补丁属于 E011 的标准处置（源码模板
  `configure.ac` 里没有 `umask` 逻辑，无处可改——该逻辑由 autoconf 的
  `config.status` 机制生成）。

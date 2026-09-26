# yudit 3.1.0 适配笔记

## 编译环境
- 构建系统: **autotools（手写变体）** —— autoconf 生成的 `configure` + 手写 `Makefile.in` / `Makefile.conf.in` + 每个子目录一个手写 Makefile（**非 automake**，无 `make check` 目标）
- 编译日期: 2026-09-22
- 编译器: clang / clang++ 15.0.4（OHOS SDK 26.0.0.18）
- profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS / os.version=6.0 / arch=armv8 / clang 15 / libc++ / cppstd=17 / Release）
- 状态: built
- 目标平台: OpenHarmony / HarmonyOS PC aarch64（`uname -s` = `HarmonyOS`）

## 编译步骤

```bash
# 1) 依赖（W0 已核验可消费，conan create 未构建任何依赖）
#    libx11/1.8.13 + xorgproto/2025.1（显式）+ 传递 libxcb/1.17.0 / libxau/1.0.11 /
#    libxdmcp/1.1.5 / xtrans/1.4.0 / xcb-proto/1.17.0

# 2) configure（X11 搜索路径必须靠 CPPFLAGS/LDFLAGS 注入，configure 不认 pkg-config）
CPPFLAGS="-I<libx11>/include -I<xorgproto>/include ..."
LDFLAGS="-L<libx11>/lib -L<libxcb>/lib -L<libxau>/lib -L<libxdmcp>/lib"
LD_LIBRARY_PATH="<上述 lib 目录>"        # configure 会**运行** conftest，缺了会报
./configure --prefix=/ \
    --x-includes=<libx11>/include --x-libraries=<libx11>/lib

# 3) 构建 + 安装
make -j
make install DESTDIR=<package_folder>
```

`--prefix=/` + `DESTDIR` 使包布局落在 `<pkg>/{bin,share}`（Conan 惯例，`cpp_info.bindirs=["bin"]`、
`resdirs=["share"]`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` RC=1：`cannot run C++ compiled programs`（config.log: `Error loading shared library libxcb.so.1/libXdmcp.so.6/libXau.so.6 (needed by ./conftest)`） | configure 的 `AC_PROG_CXX`/`AC_PATH_XTRA` 会**运行** conftest；链接期注入的 `LIBS=-lX11 -lxcb …` 让 conftest 带上 X11 的 DT_NEEDED，而这些 `.so` 不在 loader 搜索路径 | 不导出 `LIBS`；把依赖 lib 目录加入 `LD_LIBRARY_PATH`（配方 `build()` 中设置）。首次 configure 日志 `.probe/logs/03_configure_first.log` |
| 2 | `config.status: error: could not setup config files machinery`（`can't create ./confPIDIag/subs1.awk: Permission denied`），**configure RC=1** | HMDFS：autoconf 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录，得到 `drwx--S---`（0700）；本机进程 uid 20020084 而文件属 uid 20001006，同组对 0700 目录无写权限，且 HMDFS 上 `chmod` 无效（实测 `chmod 755` 后仍为 0700） | **patches/0002**（configure）：`umask 077` → `umask 022`（实测 `umask 022` 产出的目录 `drwxr-s--x` 可写）。知识库 E011，先例 `archives/a/adns/1.6.2`、`archives/a/a52dec/0.7.4` |
| 3 | `./configure[5953]: can't create /tmp/gaspar57210.cpp: Read-only file system` | `configure`/`configure.ac` 硬编码 `/tmp/gaspar$$.cpp` 探测 C++ 编译器，而 OhOS 的 `/tmp` 是只读 erofs | **patches/0002**（configure）+ **patches/0003**（configure.ac）：改用 `${TMPDIR:-/tmp}`。知识库 E002 |
| 4 | `make install` 后二进制执行报 `operation not permitted`（构建目录里的未 strip 二进制可正常执行） | OhOS 要求 ELF 签名；strip 会破坏签名，被 strip 的二进制完全无法执行（实测 `strip` → `operation not permitted`，`llvm-strip` → `permission denied`；未 strip 的同一二进制正常） | **patches/0001**（Makefile.conf.in）： `INSTALL_PROGRAM = install-sh -c -s` 去掉 `-s` |

### E490（autotools helper 可执行位）核验结论
`conan-verify` G0 命中 E490 提示风险，但**本库不适用**：`get()` 从 tar 包解压时保留
归档内的权限位，`configure` 在源码树内为 `-rwxrwx---`（可执行），手工构建与
`conan create` 两次均正常执行（G2 PASS）。因此未添加 `chmod` 兜底（避免无证据的
防御性代码）。

## 依赖版本

| 依赖 | 版本 | 类型 | X11 角色 |
|---|---|---|---|
| libx11 | 1.8.13 | 直接强制（`configure.ac:37 AC_PATH_XTRA`、`-lX11`） | 唯一外部库 |
| xorgproto | 2025.1 | 直接（显式 require） | `X11/X.h` 等协议头；仅传递时 conan 标 “Skipped binaries” 不装头文件 |
| libxcb | 1.17.0 | 传递（libx11） | libX11.so.6 的 DT_NEEDED |
| libxau | 1.0.11 | 传递（libx11 / libxcb） | 同上 |
| libxdmcp | 1.1.5 | 传递（libxcb） | 同上 |
| xtrans | 1.4.0 | 传递（libx11） | 头文件/数据 |
| xcb-proto | 1.17.0 | 传递（libx11 / libxcb） | 数据包 |

## 上游测试

上游**无自动化测试套件**（SUBDIRS 不含 `tests/`；全仓无 `check:`/`test:` 目标；
`tests/ToolTest.cpp` 的 `main()` 为空函数体；`tests/RasterizerTest.cpp` 是需 X display
的 GUI 演示且无断言）。因此按 R51 三步法：清点入口 → 实际运行上游样例 → 如实回填。

- 上游 22 个样例（`tests/testtext/*.txt` 19 个 + `tests/{nam,yuu,z}.txt` 3 个）
  全部用被测 `uniprint` 渲染为 PostScript，并用 `uniconv` 做 UTF-8↔UTF-16 往返：
  **22/22 PASS**（22 份 PS 均通过 `%!PS-Adobe-3.0` / `%%EOF` / `%%Pages` 结构校验）
- `tests/toolTest` RC=0；`tests/rasterizerTest` 在无 X server 下 RC=139
  （`Can not open display.` ×2 → SIGSEGV），属上游 GUI 用例的环境限制
- 详见 `reports/test-report.md`

## 验证结果

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=yudit/3.1.0
...
yudit/3.1.0: Package 'aaa36621d5020ccfae7b024d38905f1758ac7036' created
======== Testing the package: Executing test ========
CASE T1       PASS uniconv UTF-8->UTF-16->UTF-8 往返一致（BOM ff fe，rc=0/0）
CASE T2       PASS uniprint 输出合法 PostScript（26276 字节，uniprint: printed 1 page.）
CASE T3       PASS yudit 加载 libX11 依赖链成功并到达显示层（无 X server，预期 'Can not open display.'）
CASE HMOS-1   PASS  ELF64 AArch64(e_machine=0xB7) + /lib/ld-musl-aarch64.so.1（鸿蒙 PC 目标）
CASE HMOS-2   PASS  含 .symtab，未被 strip（可正常执行，见 patches/0001-Makefile.conf.in.patch）
RC=0

$ python3 scripts/ohc-run.py conan-verify yudit 3.1.0
✅ 配方验证通过: yudit 3.1.0     RC=0
```

## 注意事项

- **`YUDIT_DATA` 是编译期常量**（`stoolkit/Makefile:87 -DYUDIT_DATA=\"$(YUDIT_DATA)\"`），
  取自 `--prefix`，本配方为 `//share/yudit`。数据文件（keymap/fonts/syntax/config、209 个
  `.my`、136 个 `.kmap`、2 个 `.ttf`）随包安装在 `<pkg>/share/yudit/`。运行期若需指向
  其他位置，可用 `~/.yudit/yudit.properties` 的 `yudit.datapath` / `yudit.fontpath` /
  `yudit.syntaxpath` 覆盖（上游设计即如此，Linux 分支不做可执行文件相对路径推导）。
- `yudit` 是 X11 GUI 程序，**运行需要 X server**（本机无，故 test_package 只验证到
  “依赖链完好 + 到达显示层”）。
- 本包产出 4 个命令行工具：`yudit`、`uniconv`、`uniprint`、`mytool`（软件级
  `commands.json` 已声明）。
- 4 个二进制均 DT_NEEDED `libX11.so.6`（`ALL_LIBS` 是全工程共享的），消费方需通过
  `conan install` + VirtualRunEnv 提供 `libX11/libxcb/libXau/libXdmcp` 的 lib 目录。
## 发现与知识

（本节为 W5 知识沉淀清单；每条均已在流程中提取，✅ = 已入库/已建草稿）

✅ E011（已有正式条目）— HMDFS 上 autoconf 的 `umask 077 && mktemp -d ./confXXXXXX` 建出的 0700 临时目录对构建用户不可写，`config.status` 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery`，configure RC=1；改 `umask 022` 可解（同 `archives/a/adns/1.6.2`、`archives/a/a52dec/0.7.4`）。

✅ E002（已有正式条目）— OhOS `/tmp` 是只读 erofs；configure 硬编码 `/tmp/gaspar$$.cpp` 的 C++ 编译器探测必然失败并打印 `Read-only file system`；改用 `${TMPDIR:-/tmp}`。

✅ E429（本次新建草稿 `E429-draft-7060.kv`）— autoconf 的 `AC_PROG_CXX`/`AC_PATH_XTRA` 会**运行** conftest；把第三方库经 `LIBS`/`LDFLAGS` 注入后 conftest 带上该库 DT_NEEDED，若这些 `.so` 不在 loader 搜索路径，configure 直接以 `cannot run C++ compiled programs` 失败（config.log 内为 `Error loading shared library …(needed by ./conftest)`）。对策：不导出 `LIBS`，把依赖 lib 目录加入 `LD_LIBRARY_PATH`。

✅ E543（本次新建草稿 `E543-draft-687A.kv`）— OhOS 要求 ELF 签名；`make install` 的 `INSTALL_PROGRAM = install-sh -c -s` 会 strip，strip 后的二进制在鸿蒙 PC 上完全无法执行（实测 `strip` → `operation not permitted`，`llvm-strip` → `permission denied`；同一未 strip 二进制正常）。对策：安装阶段去掉 `-s`。

✅ E490 核验结论：conan-verify G0 命中 E490（autotools helper 可执行位），本库**不适用** —— `get()` 从 tar 包解压保留归档权限位，`configure` 为 `-rwxrwx---`，手工构建与 `conan create` 两次均正常执行（G2 PASS），故未添加无证据的 `chmod` 兜底。

✅ libx11 的 X11 头文件依赖 xorgproto：`<X11/Xlib.h>` 内部 `#include <X11/X.h>`；xorgproto 只作传递依赖时 conan 标为 `Skipped binaries`、不安装头文件，必须在配方中显式 `self.requires("xorgproto/2025.1")`（同 `archives/l/libfltk/1.3.11` 先例）。

✅ `YUDIT_DATA` 为编译期常量（`stoolkit/Makefile` 用 `-DYUDIT_DATA=\"$(YUDIT_DATA)\"`），取自 `--prefix`；包内数据位于 `<pkg>/share/yudit/`，运行期如需改指可用 `~/.yudit/yudit.properties` 的 `yudit.datapath`/`yudit.fontpath`/`yudit.syntaxpath`（上游 Linux 分支不做可执行文件相对路径推导）。
---

**编译结束**: 2026-09-22 02:00
**最终状态**: built

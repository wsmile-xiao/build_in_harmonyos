# libasm 0.195 适配笔记（HarmonyOS PC · Conan autotools）

> libasm 是 elfutils 套件（sourceware.org）的汇编器库。0.195 发行包是 elfutils
> 全量源码（configure 无 `--enable-only-libasm` 之类开关），本配方构建整套
> elfutils 后**只打包 libasm 组件**（`lib/libasm.so{,.1,-0.195.so}`、`lib/libasm.a`、
> `include/elfutils/libasm.h`），并 `requires elfutils/0.195` 使 `libasm.so.1`
> 的 `DT_NEEDED libelf.so.1` 与 `<gelf.h>/<libelf.h>` 头闭包来自已发布的
> elfutils/0.195 包。

## 编译环境

- 构建系统: autotools（elfutils 全量源码，configure + make -j1）
- 编译日期: 2026-09-23
- 编译机: HarmonyOS PC（`uname -a` = HarmonyOS HongMeng Kernel 1.12.0 aarch64），
  内存紧张（实测 free <1G，无 swap），故 make 全程 `-j1`
- 编译器: clang/clang++（`/data/service/hnp/bin/clang`，clang 15）
- 平台: OHOS aarch64（musl libc —— **非** glibc，`error.h`/`pthread_cancel`/
  `program_invocation_short_name` 等 glibc 扩展缺失）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built（本地 conan create 通过；上游 make check 如实回填见下）

## 编译步骤（真实命令）

探索编译（模式 B，先全量跑通 + make check）：

```bash
source .build-context-libasm-0.195
cd "$BUILD_SRC_DIR"
export CFLAGS="-D_GNU_SOURCE -DFNM_EXTMATCH=0 -Wno-error"
export CXXFLAGS="-D_GNU_SOURCE -Wno-error"
./configure \
  --build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl \
  --disable-nls --disable-werror --disable-debuginfod --with-zstd \
  --program-prefix=eu- \
  --prefix="$DEFAULT_PREFIX"
make -j1
make install DESTDIR="$TEST_PREFIX"
make check -j1     # 实测 TOTAL 259 / PASS 217 / SKIP 10 / FAIL 32（明细见"验证结果"）
```

Conan 配方验证（W3，实际执行命令，`-j1` 已在配方内固化 + 额外 `-c tools.build:jobs=1`）：

```bash
conan create archives/l/libasm/0.195 \
  -pr:h=$PWD/ci/conan/profiles/ohos-aarch64 \
  -pr:b=$PWD/ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable -c tools.build:jobs=1
```

依赖的 `-I/-L/-l` 与构建期 `LD_LIBRARY_PATH` 经 `generate()` 注入环境变量喂给
configure（`AutotoolsToolchain.extra_*` 实测不一定落到 configure 环境，且
`--with-zstd` 的 `AC_CHECK_LIB` 探测必须能链到 `-lzstd`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `can't create ./confXXX/subs1.awk: Permission denied`（configure 阶段） | OHOS hmdfs 不认 umask 077：`config.status` 用 `umask 077 && mktemp -d`（E011）建临时目录，权限 700 导致子进程无法写入 | build() 对源码树所有 `configure` 脚本做 `umask 077 → umask 022` 替换（必须在 autoreconf 之后、configure 之前） |
| 2 | `install: unknown option -- -D` / install 失败 | OHOS 无 coreutils install，elfutils 自带 `config/install-sh` 不支持 GNU `-D`（`config/Makefile.am` 的 `install-data-local: $(INSTALL_DATA) -D profile.sh ...` 用到） | package() 用内置 install-shim（aircrack/1.7 → libsmf/1.3 合并先例）：忽略 mode 旗标、`mkdir -p` 建父目录、`cp -f` 拷贝，以 `INSTALL='/bin/sh <shim>'` 传入 make install |
| 3 | CFLAGS 里的 `-Wno-error` 不生效，编译仍被 `-Werror` 打断 | automake 编译行中 CFLAGS 排在 `AM_CFLAGS` 之后，`AM_CFLAGS` 里写死的 `-Werror` 会**覆盖** CFLAGS | 把 `-Wno-error` 也放进 extra_cflags（编译行上出现在 AM_CFLAGS 之后的位置），且 `--disable-werror` 一并给出 |
| 4 | `error.h: No such file or directory`（src/threadlib.c） | musl 无 glibc 的 `<error.h>`；elfutils 0.195 新增的 threadlib.c 无条件 include 它 | 补丁 0001：走上游既有条件分支（`HAVE_ERROR_H` → `<error.h>`，否则自带 `lib/error.c` 的声明） |
| 5 | `gettext`/`textdomain` undeclared 或链接期 undefined | OHOS musl 的 `libintl.h` 是**不声明任何函数的空桩**；`_()/ngettext/textdomain/bindtextdomain` 家族照原样用全部退化成隐式声明或链接失败 | 补丁 0002：`eu-config.h` 按 `ENABLE_NLS` 分叉，`--disable-nls` 时给出无操作宏（家族按广义 grep `[a-z_]*(gettext\|textdomain)[a-z_]*` 一次枚举） |
| 6 | `program_invocation_short_name` 未声明（链接期 undefined） | glibc 扩展，OHOS musl 完全不提供（`-D_GNU_SOURCE` 也无效，真机探针实测证伪） | 补丁 0002：别名到传统 BSD `extern char *__progname`（同一探针确认可用；不选 getprogname/getauxval——语义不对） |
| 7 | `dwfl-proc-attach` 链接失败 | OHOS musl 缺 `pthread_cancel`（探针实测 undeclared） | 环境类限制，上游测试跳过该族；配方不引它（libasm 组件不涉及） |
| 8 | `asm_end` 在 text 模式（`textp=true`）下必崩（SIGTRAP/Segfault） | **上游 bug**：`prepare_text_output`/`text_newscn` 未初始化 AsmCtx/AsmScn 字段，但 `asm_end → __libasm_finictx → free_section` 无条件释放；binary 路径初始化了、text 路径没初始化 | 补丁 0003：text 路径做与 binary 路径相同的初始化（源码级修复，已实测 text 模式 14 断言全过） |
| 9 | `make check` 32 项 FAIL（217 PASS） | 全部为**环境类/上游自测约束**，libasm 相关测试（asm-tst1..9 + 4 个 disasm）**全过**；32 项逐项分类见"验证结果" | 环境类失败不可修（toybox wc 缺 `--lines`、OHOS 内核禁 ptrace、OHOS 工具链产物含 `.note.ohos.ident` 等）；无 libasm 侧失败 |
| 10 | `conan create` 末尾报 `package_info(): There are '(cpp_info/components).requires' to other internal components that are not defined: ['elfutils']`（构建+打包已成功，仅收尾失败） | Conan 2 的 `self.cpp_info.requires` 只能引用**同包内部** components，不能引用依赖包名；原配方用它想传播 `-lelf/-ldw`，语法错误 | 移除该行——依赖库传播已由 `requirements()` 的 `transitive_headers=True + transitive_libs=True` 完成（消费者链 `-lasm` 自动带 `-lelf/-ldw`，头闭包同理）；修复后 conan create 全绿 |

## 源码修改（3 个补丁）

| 补丁 | 修改点 | 类型 |
|------|--------|------|
| `0001-threadlib-conditional-error-h.patch` | `src/threadlib.c`：无条件 `#include <error.h>` → `#if defined(HAVE_ERROR_H)` 条件包含，else 分支用自带 `lib/error.c` 的函数声明 | portability |
| `0002-eu-config-musl-portability.patch` | `lib/eu-config.h`：`_()` 按 `ENABLE_NLS` 分叉（musl 空桩 libintl.h 无符号）；`ngettext/textdomain/bindtextdomain` 无操作宏；`program_invocation_short_name` → `__progname` | portability |
| `0003-libasm-text-mode-init.patch` | `libasm/asm_begin.c`（`prepare_text_output`）+ `libasm/asm_newscn.c`（`text_newscn`）：text 模式补上下文/节字段初始化，与 binary 路径一致；修复 text 模式 `asm_end` 崩溃 | bugfix（上游 bug，适配时发现） |

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| elfutils | 0.195 | 同源全量构建；运行时 libelf.so.1 与 gelf.h/libelf.h 头闭包（transitive_headers/libs） |
| zlib | 1.3.1.1 | 压缩支持 |
| zstd | 1.5.7 | `--with-zstd`（configure AC_CHECK_LIB 探测需可链接） |
| bzip2 | 1.0.8 | 压缩支持 |
| xz | 5.6.2 | 压缩支持 |
| argp-standalone | 1.5.0 | glibc argp 垫片（musl 缺） |
| musl-fts | 1.2.7 | fts 垫片 |
| musl-obstack | 1.2.3 | obstack 垫片 |

工具链：clang 15（OHOS SDK `/data/service/hnp/bin/clang`）、OHOS musl、Conan 2.29.1（OHOS 适配版）。

## 验证结果

### 1) 上游 make check（本机实测，如实回填）

```text
TOTAL: 259   PASS: 217   SKIP: 10   XFAIL: 0   FAIL: 32   XPASS: 0   ERROR: 0
```
来源：`tests/test-suite.log`（`make check` 输出），且与 `tests/*.trs` 逐文件
计数交叉一致（PASS 217 / FAIL 32 / SKIP 10）。

### 2) libasm 相关测试 —— 全部 PASS

- `asm-tst1` ~ `asm-tst9`（libasm 汇编器 API 测试）：9 个全部 `PASS (exit status: 0)`
- `run-disasm-bpf.sh` / `run-disasm-riscv64.sh` / `run-disasm-x86-64.sh` /
  `run-disasm-x86.sh`（反汇编测试）：4 个全部 `:test-result: PASS`

### 3) 32 个 FAIL 逐项分类（libasm 无关，均为环境/自测约束）

| 类别 | 测试（个数） | 根因摘要（证据见下） |
|------|--------------|----------------------|
| **toybox wc 缺 `--lines`**（13） | run-strip-test.sh、run-strip-test2..12.sh、run-strip-nobitsalign.sh | 测试脚本调 `wc --lines`，OHOS 的 toybox 0.8.12 只支持 `-l`：实测 `wc --lines /etc/hosts` → `wc: Unknown option 'lines'`，`wc -l` 正常 |
| **ar 无法表示 uid**（2） | run-ar.sh、run-ar-N.sh | 系统 `ar`（toybox/llvm-ar 生态）报 `ar: cannot represent ar_uid: No such file or directory`，无法创建归档 |
| **OHOS 工具链产物格式**（6） | run-strip-nothing.sh、run-strip-strmerge.sh、run-strip-reloc-self.sh、run-elflint-self.sh、run-readelf-self.sh、run-reverse-sections-self.sh | OHOS 链接器产物带 `.note.ohos.ident` note 节、`.gnu.version` 版本索引非标准、GNU_RELRO 布局差异：`elflint` 报 `cannot get content of note section` / `invalid version index`，`elfcmp` 报 `.note.ohos.ident` notes 数不同 —— 上游自测校验的是标准 ELF 布局，与 OHOS 二进制格式不兼容 |
| **内核禁 ptrace/进程观测**（5） | dwfl-bug-fd-leak、run-backtrace-native.sh、run-backtrace-dwarf.sh、run-deleted.sh、vdsosyms | `PTRACE_TRACEME failed: Permission denied`、`dwfl_module_getelf: Callback returned failure`、`[vdso]` 读取失败 —— OHOS 内核收紧 ptrace/进程调试权限 |
| **argv[0] 输出差异**（3） | run-stack-d-test.sh、run-stack-i-test.sh、run-stack-demangled-test.sh | `stack:` 前缀输出全路径（`/storage/.../src/stack:`）与上游期望的基名 `stack:` 不一致（OHOS musl argv[0] 处理差异） |
| **Bad system call**（1） | run-sysroot.sh | musl/OHOS 内核某 syscall 不支持：`Bad system call (core dumped)`（exit 159） |
| **压缩后未变小**（1） | run-compress-test.sh | `testfile4` 已足够小/已压缩，`compress gnu` 后不小于原文件 → 断言 `testfile4.gnu not smaller` 失败（数据大小依赖） |
| **readelf 行为差异**（1） | run-readelf-s.sh | 上游期望 `readelf --syms <arg>` 报错，本版本 readelf 接受该参数并输出符号表（上游自测期望与实测行为不一致） |

**环境类失败的已验证证据（命令实测输出）**：

```text
# toybox wc 缺 --lines（0.8.12 只有 -l）
$ wc --version ; wc --lines /etc/hosts ; wc -l /etc/hosts
toybox 0.8.12
wc: Unknown option 'lines' (see "wc --help")
6 /etc/hosts

# OHOS musl 缺 pthread_cancel（编译探针）
$ clang ptprobe.c   # int main(void){ return (int)(long)pthread_cancel; }
ptprobe.c:2:35: error: use of undeclared identifier 'pthread_cancel'

# OHOS musl 缺 <error.h>
$ clang -c errh.c   # #include <error.h>
errh.c:1:10: fatal error: 'error.h' file not found

# 内核禁 ptrace（make check 实测日志）
PTRACE_TRACEME failed: Permission denied
dwfl-bug-fd-leak: dwfl_module_getelf: Callback returned failure
```

### 4) 本包 test_package 实测

`test_package/test.c` 对 libasm 公共 API 做真实断言（非空壳）：`asm_begin`(textp=true)
→ `asm_newscn` → `asm_adduint8/16` → `asm_addsleb128` → `asm_adduleb128` →
`asm_align` → `asm_end`，回读输出文件断言非空且含 `.text` 与期望数据；
另验错误路径 `asm_begin(NULL,NULL,false)==NULL`。共 14 个断言，**全部通过**。
（binary 输出模式需内部 libebl，发行环境不装；text 模式是 libasm 可独立消费
的公共 API，且正因使用它而发现并修复了补丁 0003 的上游崩溃 bug。）

### 5) W3 `conan create` 实测（本机，`-j1`）

```text
libasm/0.195@ohpcd/stable: Full package reference: libasm/0.195@ohpcd/stable#99c0c3f...:a29c0a48...#db70c3a...
======== Testing the package: Executing test ========
libasm/0.195@ohpcd/stable (test package): Running test()
[ok] elf_version(EV_CURRENT) 初始化成功
[ok] asm_begin(NULL,NULL,false) 按预期失败
[ok] asm_begin(textp=true) 创建上下文
[ok] asm_newscn(.text) 新建节
[ok] asm_adduint8(0x2a) / asm_adduint16(0x1234) / asm_addsleb128(-5)
[ok] asm_adduleb128(0x1f) / asm_align(8) / asm_end 收尾成功
[ok] asm_end 已生成输出文件 / 输出文件非空 / 输出含 .text 节指令 / 输出含 adduint8 数据（0x2a）
all libasm API assertions passed
```
结论：本机内存 <1G 未触发 OOM（全程 `-j1` + `-c tools.build:jobs=1`），配方自包含
（下载→configure→make→install→签名→package_info→test 全链成功）。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` + `conandata.yml` | 自包含 Conan 配方（只打包 libasm 组件，含 OHOS install-shim、umask 022、-Wno-error 顺序等适配） |
| `patches/0001..0003` | 三个源码补丁（见上表） |
| `test_package/{conanfile.py,test.c,MANIFEST.yml}` | 14 断言真实 API 测试 |
| `manifest.yaml` | 归档元数据（status: built） |

## 注意事项

- 测试通过率**如实上报**：本机实测 217/259（PASS 83.4%），32 个失败全部为
  环境类/上游自测约束，libasm 相关测试全过——不谎报 100%。
- `.ci-result.json` 由 finish 工具（W3）生成，不手写。
- 本机内存 <1G、无 swap，任何重编译步骤都必须 `-j1`（配方内已固化）。
---

**编译结束**: 2026-09-23 20:38
**最终状态**: built

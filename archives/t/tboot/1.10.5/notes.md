# tboot 1.10.5 适配笔记

## 编译环境
- 构建系统: makefile（手写多级 Makefile，无 configure/cmake/meson）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，默认 target `aarch64-unknown-linux-ohos`）+ llvm-ar/llvm-ranlib
- 平台: HarmonyOS PC aarch64（musl，`/tmp` 只读）
- 状态: built

## 目标范围（重要）

上游顶层 `Makefile:17` 的 `SUBDIRS := tboot safestringlib lcptools-v2 tb_polgen utils docs`。
aarch64/OHOS 上**只构建宿主侧可移植部分**，两个 x86 专属产物按平台剔除（补丁 0002/0009）：

| 子项目 | 是否构建 | 依据 |
|---|---|---|
| `tboot` | ❌ | freestanding x86-32 引导固件：`tboot/Config.mk:50 LDFLAGS = -melf_i386`、`:21 -march=i686`、`:22 -nostdinc` |
| `safestringlib` | ✅ | 纯 C 边界检查字符串库（源码树自带，`-DSTDC_HEADERS`） |
| `lcptools-v2` | ✅ | 4 个 LCP 策略工具，链接 `-lcrypto -llcp -lz` |
| `tb_polgen` | ✅ | 策略生成器，链接 `-lcrypto -lz` |
| `utils` | 部分 | `txt-stat` / `txt-parse_err` ✅；`txt-acminfo` ❌（`#include ../tboot/include/processor.h`、`io.h`，读 x86 MSR/IO 端口） |
| `docs` | ✅ | 仅安装 man8 手册 |

产物：7 个可执行文件（`bin/`）+ 7 个 man 手册（`share/man/man8/`）+ 许可（`licenses/COPYING`）。

## 编译步骤（真实命令）

```bash
# 依赖：conan 制品仓（openssl/3.5.6.1、zlib/1.3.1.1，均为静态归档）
conan install --requires=openssl/3.5.6.1 --requires=zlib/1.3.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd

# 构建（CFLAGS/LDFLAGS 经环境传入，避免命令行覆盖各层 Makefile 的 += 追加）
cd tboot-1.10.5.work
CFLAGS="-I<openssl>/include -I<zlib>/include" \
LDFLAGS="-L<openssl>/lib -L<zlib>/lib" \
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1        # → rc=0

# 上游单元测试（唯一可运行的上游自动化套件）
make -C safestringlib safestringtest CC=clang -j1       # → rc=0
(cd safestringlib && ./safestringtest)                   # → rc=0，214 个 Test # 用例

# 安装（staging 验证）
make install DESTDIR=<staging> INSTALL=/bin/install CC=clang -j1   # → rc=0，15 个文件
```

日志（真实输出/退出码留档于任务工作区）：
`tboot-1.10.5-logs/07-build-attempt1.log`（首个错误）…`38-final-build.log`、`40-final-test-run.log`、`41-final-install.log`。

## 遇到的问题与解决方案

| # | 问题（首个错误原文） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `clang-15: error: unsupported argument 'i686' to option '-march='`（`tboot/Config.mk:20-21`，发生在第 1 个子项目 `tboot`） | `Config.mk` 用 `TARGET_ARCH=$(shell uname -m …)` 判定，非 x86_64 一律进 `else` 分支加 `-m32 -march=i686`；aarch64 上 clang 拒绝该参数 | 补丁 0001：只有 `TARGET_ARCH` 为 `x86_32/x86_64` 才加 x86 机器参数 |
| 2 | `make` 进入 `tboot` 子项目后必有 x86 汇编/链接（`-melf_i386`） | 该子项目是 x86-32 固件，与目标平台无关 | 补丁 0002：非 x86 目标的 `SUBDIRS` 去掉 `tboot` |
| 3 | `clang-15: error: -z noexecstack: 'linker' input unused [-Werror,-Wunused-command-line-argument]`（`safestringlib/makefile:29`） | 编译规则里带 `$(LDFLAGS)`（含 `-z …`），且 `-Werror` 把它升级为致命错误；另 `-z relo` 是上游拼写错误（应为 `-z relro`） | 补丁 0006：编译规则去掉 `$(LDFLAGS)`；`-z relo` → `-z relro` |
| 4 | `safeclib/strpbrk_s.c:95:13: error: variable 'len' set but not used [-Werror,-Wunused-but-set-variable]` | 上游 `strpbrk_s()` 的 `len` 只写不读（历史遗留死代码） | 补丁 0007：删除该变量（行为不变） |
| 5 | `include/lcp3.h:269:29: error: field 'pcr_selection' with variable sized type … not at the end of a struct … [-Wgnu-variable-sized-type-not-at-end]`；`tb_polgen/param.c` 的 `[-Wgnu-designator]`；`utils/txt-stat.c:281 [-Wunused-function]`；`lcptools-v2/lcputils.c:962/1125 [-Wnon-literal-null-conversion]`（`#define SM2_ID '\0'`） | 上游 `Config.mk` 自带 `-Werror`，老代码使用 GNU 扩展（packed 结构里变长成员、老式指定初始化、`'\0'` 当空指针），这些诊断 GCC 默认不报、clang 15 默认报 | 补丁 0001 第二段：只对这 4 条诊断追加 `-Wno-error=`（**保留告警输出**，不整体取消 `-Werror`，不改这些源码） |
| 6 | `utils/txt-acminfo.c` 编译报 `../tboot/include/io.h:55: invalid output constraint '=a' in asm` | `txt-acminfo` 通过 `io.h`/`processor.h` 使用 x86 `in/out`/MSR 内联汇编，仅 x86 可编译 | 补丁 0009：非 x86 目标的 `TARGETS` 去掉 `txt-acminfo` |
| 7 | `lcptools-v2/pollist2.c:930: error: variable 'pubkey' is used uninitialized whenever 'if' condition is true [-Wsometimes-uninitialized]` | OpenSSL 3 分支 `EVP_PKEY *pubkey;` 未初始化，错误路径会 `free` 它 | 补丁 0005：`= NULL` |
| 8 | `lcptools-v2/crtpol.c:362: error: variable 'use_only_version' is used uninitialized whenever 'if' condition is false` | 声明未初始化，clang 控制流分析发现潜在路径 | 补丁 0003：`= 0` |
| 9 | `unittests/test_wmemmove_s.c:407/433: error: incompatible integer to pointer conversion passing 'wchar_t' to parameter of type 'wchar_t *'` | **上游用例自身缺陷**：`(wchar_t)(((char *)mem1)+1)` 少写了 `*`（GCC 只告警） | 补丁 0008：改为 `(wchar_t *)` |
| 10 | `unittests/test_strcasestr_s.c:132…425: error: incompatible integer to pointer conversion assigning to 'char *' from 'int'`（6 处） | 用例要与 libc 的 GNU 扩展 `strcasestr` 对比，但 musl 只在 `_GNU_SOURCE` 下声明它 → 隐式声明返回 int | 补丁 0006 第三段：仅测试编译规则加 `-D_GNU_SOURCE` |
| 11 | `lcp2_mlehash --create …` 输出 `creating a temporary file to uncompress ... : failed!`（工具失效） | `mlehash.c:300` 用 `tmpfile()`，固定落在 `/tmp`；**OHOS `/tmp` 是只读挂载（E002，实测 `touch /tmp/x` → Read-only file system）** | 补丁 0004：新增 `open_scratch_stream()`，在 `$TMPDIR` 下 `mkstemp`+`unlink`（保持匿名临时文件语义）；`TMPDIR` 未设置时回落 `/tmp`（与原行为一致） |

**HANDOFF 次数**: 0（全部错误可在本机定位与修复，无需人工交接）

## 源码修改（9 个补丁，全部不含 `__OHOS__` 平台宏）

| 补丁 | 内容 | 类型 |
|---|---|---|
| `0001-Config.mk.patch` | x86 机器参数改为 arch 条件；4 条 clang 诊断有界降级 | portability |
| `0002-Makefile.patch` | 非 x86 目标 `SUBDIRS` 去掉 `tboot` | portability |
| `0003-lcptools-v2-crtpol.c.patch` | `use_only_version = 0` | bugfix |
| `0004-lcptools-v2-mlehash.c.patch` | 解压临时文件改用 `$TMPDIR` | portability |
| `0005-lcptools-v2-pollist2.c.patch` | `EVP_PKEY *pubkey = NULL` | bugfix |
| `0006-safestringlib-makefile.patch` | `-z relro` 拼写；编译规则去掉链接选项；测试 `-D_GNU_SOURCE` | portability |
| `0007-safestringlib-safeclib-strpbrk_s.c.patch` | 删除只写不读的 `len` | portability |
| `0008-safestringlib-unittests-test_wmemmove_s.c.patch` | `(wchar_t)` → `(wchar_t *)` | bugfix |
| `0009-utils-Makefile.patch` | 非 x86 目标 `TARGETS` 去掉 `txt-acminfo` | portability |

补丁生成：`ohc-run.py refresh-patch --auto tboot 1.10.5`（逐文件 unified diff）；
9 个补丁全部对上游原始树 `patch -p1 --dry-run` 通过。

## 依赖版本

| 依赖 | 版本 | 用途 | 证据 |
|---|---|---|---|
| openssl | 3.5.6.1 | `libcrypto`：LCP 策略 RSA/ECDSA/SM2、EVP 摘要 | `lcptools-v2/Makefile:69`、`tb_polgen/Makefile:18` 的 `-lcrypto`；`lcputils.c` 使用 OpenSSL 3 provider API |
| zlib | 1.3.1.1 | `lcp2_mlehash` 的 gzip 输入、`tb_polgen` 压缩策略输入 | 同上两处 `-lz`；`mlehash.c:42`、`commands.c:41` 的 `#include <zlib.h>` |

二者均为 conan 静态归档，最终产物 `DT_NEEDED` 仅 `libc.so`。
（上游 `lcptools-v2/Makefile:69` 的 `-llcp`、`safestringlib/libsafestring.a` 是源码树自带，不是第三方依赖。）

## 验证结果

```bash
# 1. 全量干净构建
$ make clean CC=clang && make CC=clang -j1
make rc=0；错误数 0（保留 32 条已知告警：gnu-variable-sized-type 18 / gnu-designator 11 / unused-function 1 / non-literal-null 2）

# 2. 上游单元测试（唯一可运行的上游套件）
$ make -C safestringlib safestringtest CC=clang -j1 && (cd safestringlib && ./safestringtest)
rc=0；用例 214（源码中 "Test #" 字面量 214，全部执行）；BEGIN/END TEST 齐全；
  异常行 4 条，全部来自 test_strcmp_s 与 libc strcmp 的“返回值量级一致”对照：
    test_strcmp_s 141/164/209/232  ind=-32/-32/4/-4  std_ind=-128/128/70/-70
  说明：安全库自身断言（`ind != -32` 等）全部通过，差异来自 musl/OHOS libc 的
  strcmp 返回量级（glibc 返回字节差），不影响 strcmp_s 语义。

# 3. staging 安装
$ make install DESTDIR=<staging> INSTALL=/bin/install CC=clang -j1   # rc=0，15 个文件
$ <staging>/usr/sbin/{lcp2_mlehash,lcp2_crtpol,lcp2_crtpollist,lcp2_crtpolelt,tb_polgen,txt-stat,txt-parse_err} -h
  7/7 可执行（ELF64 AArch64，musl 动态加载器）

# 4. conan create（消费者测试 22 条断言，见 test_package/test.sh）
$ conan create . --version=1.10.5 -pr:h=ci/conan/profiles/ohos-aarch64
```

## 上游测试清点（R51）

| 入口 | 类型 | 是否可运行 | 说明 |
|---|---|---|---|
| `safestringlib/unittests/` | 65 个 `test_*_s.c` + 主驱动 | ✅ 已实跑 | `make -C safestringlib safestringtest && ./safestringtest`，214 用例，rc=0 |
| `txt-test/txt-test.c` + `txt-test/Kbuild` | Linux 内核模块 | ❌ | 需要内核源码树做外部模块构建；上游 `Makefile:16` 注释明确排除 |
| `test-patches/{e820,mtrrs,tpm,vsprintf}-test.patch` | 内核测试补丁 | ❌ | 同需内核源码树 |
| `uml/*.plantuml` | 流程图（launch/load_sinit/prepare_cpu/shutdown） | — | 不是测试 |
| `tboot/` | 无 | — | x86 引导模块，本平台不构建 |

上游没有 `make check` 目标，也没有 CI 测试配置；`safestringlib` 单元测试是唯一自动化套件。

## 交付物

| 文件 | 说明 |
|---|---|
| `bin/lcp2_mlehash` | MLE 哈希（`SHA256(SHA256(cmdline)||SHA256(image))`） |
| `bin/lcp2_crtpol` / `lcp2_crtpollist` / `lcp2_crtpolelt` | LCP 策略 / 策略列表 / 策略元素 |
| `bin/tb_polgen` | Verified Launch Policy 生成与维护 |
| `bin/txt-stat` / `bin/txt-parse_err` | TXT 状态读取 / ERRORCODE 解析 |
| `share/man/man8/*.8` | 上述 7 个工具的手册（不含未构建的 txt-acminfo） |
| `licenses/COPYING` | BSD-3-Clause |

## 注意事项

1. **提交阶段已知框架缺陷（PF9）**：`preflight.check_branch_and_paths()` 用
   `len(path.split("/")) < 5` 判定，会把 R38/ARCHIVE-SPEC 规定的软件级文件
   （`archives/t/tboot/commands.json`、`README.md`、`manifest.yaml`）判为
   "缺版本目录层"并拦截建 PR —— 与 PF8（要求软件级 `commands.json`）自相矛盾。
   实测复现：
   ```python
   from ohc import preflight as pf
   pf.check_branch_and_paths(Path(repo), ["archives/t/tboot/commands.json", ...])
   # → ['PF9 分支/路径闸: 变更路径缺版本目录层 … : archives/t/tboot/commands.json, …']
   ```
   这是已有多份 SKILL_FEEDBACK 记录过的已知误报，提交时需按既有做法用
   `OHC_PREFLIGHT=0`（或 `--no-preflight`）旁路并在 PR 说明。
2. **`-Werror` 的处置口径**：只对 4 条 clang 新增诊断 `-Wno-error=`，告警仍打印；
   未整体取消 `-Werror`（本机构建日志中仍能看到这 32 条告警）。
3. **`/tmp` 只读**：任何新增的临时文件路径都必须走 `$TMPDIR`（`test.sh` 全程只在
   工作目录下读写，从不使用 `/tmp`）。
4. **静态链接**：openssl/zlib 均为静态归档，工具无需 rpath；`test.sh` OH-3/OH-4
   断言产物 `DT_NEEDED` 仅 `libc.so` 且无 RUNPATH/RPATH。
5. **源码 URL 的选择**：`conandata.yml` 用
   `https://downloads.sourceforge.net/project/tboot/tboot/tboot-1.10.5.tar.gz`
   而不是页面式 `.../files/tboot/tboot-1.10.5.tar.gz/download`。两者实测返回完全
   相同的字节（907657 B，sha256 `3b4be16c…b393`），但页面式链接末段是 `download`
   没有扩展名，Conan 的 `get()` 会据此猜错归档格式而报 `BadZipFile`。
6. **G0 干净构建校验（框架侧已知限制）**：本包是手写 Makefile 工程（无 `./configure`），
   而 `clean_verify` 目前只对 CMake/Meson 工程跳过 `./configure`，因此 G0 报
   `configure 失败 (exit 127)`。该步骤在 finish 中标注为非阻塞，干净构建由 W3 的
   `conan create` 覆盖（已通过）。G0 的补丁应用子步骤（9/9 成功）实际有效。
7. **推到远端前注意**：`finish` 的 Step 8 会重新生成框架索引 `SUMMARY.md`，
   `git status` 会显示为已修改；PR 只允许提交 `archives/t/tboot/**`，
   提交时请只 `git add archives/t/tboot/`（不要 `git add -A`）。
## 对话记录

### 对话 #1 — 依赖分析与 W0 预检（2026-09-24，前置阶段）
- 目标：确认 tboot 1.10.5 的第三方依赖已发布，避免适配到一半断链（W0/R36）。
- 结论：强制第三方依赖只有 **openssl/3.5.6.1** 与 **zlib/1.3.1.1**，`conan download -r=ohpcd --only-recipe`
  两者均 exit 0（负向对照 `zzzz-control-nonexistent/1.0.0` exit 1）；trousers/libtspi/grub/tpm-tools 不可消费但属排除项。
- 证据目录：`GPQworkspace/tboot-1.10.5-deps/`（DEPENDENCY-REPORT.md + logs/ + evidence/）。
- 上游源码可取：SourceForge 官方 `tboot-1.10.5.tar.gz`，sha256 `3b4be16c…b393`（与 Debian orig tarball 逐字节一致）。

### 对话 #2 — 建 worktree、源码核验与首次构建（2026-09-24 16:48-17:05）
- W1：`git fetch origin main` + `git worktree add tboot-1.10.5-wt -b feat/tboot-1.10.5 origin/main`（基线 d47316a87d）。
- 源码核验：`sha256sum` 命中 conandata 声明的 sha256；`.hg_archival.txt` 记录 tag v1.10.5 / node 9c406d76。
- 语言预检（R47）：`lang-preflight` → detected=c（task=cpp，c↔cpp 兼容族）→ 继续。
- 首个真实错误：`clang-15: error: unsupported argument 'i686' to option '-march='`（`tboot/Config.mk` 非 x86_64 一律加 `-m32 -march=i686`）。
- 逐项修复（详见上文"遇到的问题与解决方案"1-11）：x86 机器参数分支 → 非 x86 剔除 `tboot` 子项目 →
  clang 诊断有界降级 → 两处未初始化读取 → `-z relo` 拼写 → 上游用例类型错误 → `-D_GNU_SOURCE` →
  **`tmpfile()` 改用 `$TMPDIR`**（/tmp 只读，E002）。
- 全量 `make` rc=0；`make install DESTDIR=… INSTALL=/bin/install` rc=0（15 个文件）。

### 对话 #3 — 上游测试执行与配方固化（2026-09-24 17:05-17:40）
- 上游唯一可运行套件：`make -C safestringlib safestringtest && ./safestringtest` → rc=0，214 个 `Test #N` 用例全跑；
  4 处异常输出均为 `test_strcmp_s` 与 libc `strcmp` 返回值量级的对照（安全库断言 0 失败）。
- 补丁：`refresh-patch --auto` 生成 **9 个** 补丁（逐文件 unified diff，全部对原始树 `patch -p1 --dry-run` 通过，无 `__OHOS__` 宏）。
- 配方：`conanfile.py`（application + bindirs + 7 工具 + man8）、`conandata.yml`（官方源 + sha256 + 9 补丁）、
  `test_package/{conanfile.py,test.sh,MANIFEST.yml}`、软件级 `commands.json`/`manifest.yaml`/`README.md`。
- `conan create` rc=0（test_package **22/22**，含 tb_polgen 黄金摘要 `1d 76 7f d6 …` 与 4 条鸿蒙特有断言）；
  `conan-verify` PASS（G0-G4 + L2/L4/L5）。
- `finish tboot 1.10.5 built` rc=0：W3 本地 CI 100%（L0/KC/JC/L1(含 L1e 负向)/L2/L5 pass，L4 仅 1 条误报 warn），
  W5 知识图谱一致，W2 只涉及单一软件目录。
- 已知框架侧事项：G0（clean-verify）对手写 Makefile 工程会误跑 `./configure`（exit 127，非阻塞）；
  PF9 会把软件级 `commands.json`/`README.md`/`manifest.yaml` 误判为"缺版本目录层"（提交时需按既有做法走逃生口）。
- 本轮所有日志留档于任务工作区 `GPQworkspace/tboot-1.10.5-logs/`（01…58，含退出码）。
---

**编译结束**: 2026-09-24 19:23
**最终状态**: built

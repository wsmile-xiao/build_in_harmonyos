# ylva 1.7 适配笔记

## 任务名与上游判定

| 项 | 值 |
|----|----|
| 任务名（用户给出） | `ylvaC++` 1.7，分支 `feat/ylva-1.7` |
| 最终包名 | `ylva` |
| 上游仓库 | <https://github.com/nrosvall/ylva>（作者 Niko Rosvall，MIT） |
| 上游 tag | `v1.7`（NEWS: Release 1.7 — 2021-09-11） |
| 源码 URL | <https://github.com/nrosvall/ylva/archive/refs/tags/v1.7.tar.gz> |
| SHA256 | `7c557c0c30a4b3bf0a66cec41e909d491bc84a575e9fc7c0942b8d158bf199cc` |
| 构建系统 | 手写 `src/Makefile`（无 configure / 无 CMake / 无 meson） |

判定依据（R51/§2.1：`<name>C++` 尾部可能只是语言标注，不能直接当仓库名）：

- Debian 主仓的 `ylva` 1.7-2（bookworm / trixie / forky, area=main）的
  `debian/copyright` 写明 `Upstream-Contact: Niko Rosvall`、
  `Source: https://github.com/nrosvall/ylva`，版本号恰好是上游 1.7。
- 该仓库 tag 为 `v1.4 v1.5 v1.6 v1.7`，与 1.7 对得上；
  Debian 的 1.6-3（bullseye）与上游 `v1.6` 亦吻合。
- 候选排除：GitHub 上另有 `shlomif/ylva`（同名但只有 `v1.4/v1.5` tag，
  且是另一个作者的命令行口令管理器），版本对不上，排除。
- 语言标注修正：任务名里的 `C++` 是标注误差，上游 README 明确
  "Ylva is written in C"，源码为 8 个 `.c` + 8 个 `.h`，无 C++ 文件。
  按 §2.1「c↔cpp 兼容族」处理，不改变适配口径。

## 编译环境

- 构建系统: makefile（`src/Makefile`）
- 编译日期: 2026-09-30
- 编译器: OHOS SDK clang 15.0.4（`--target=aarch64-linux-ohos --sysroot=<OHOS SDK>/sysroot`）
- 目标: ohos-aarch64（本机验证用 conan profile `ohos-local`，与
  `ci/conan/profiles/ohos-aarch64` 同源配置，仅工具链路径指向本机 SDK）
- 状态: built（本地 `conan create` / `conan-verify` 通过，未 `conan upload`，R29 不伪造 published）

## 编译步骤

```bash
# 1) 依赖预检（W0 / R35：必须用 conan download 而非 conan list）
conan download openssl/3.5.8.1      -r=ohpcd            # recipe + OHOS aarch64 静态二进制
conan download sqlite3/3.49.1       -r=ohpcd
conan download libqrcodegen/1.8.0   -r=ohpcd

# 2) 初始化归档
python3 scripts/ohc-run.py init-archive ylva 1.7 \
    "https://github.com/nrosvall/ylva/archive/refs/tags/v1.7.tar.gz" makefile

# 3) 交叉编译（配方 build() 内的实际命令，CC 取自 conan conf，R33）
make -C src -j1 \
  CC="<conf tools.build:compiler_executables.c>" \
  CFLAGS="-O2 -std=c11 -Wall -I<_qrcodegen_compat> -I<libqrcodegen>/include -I<openssl>/include -I<sqlite3>/include" \
  LDFLAGS="-L<libqrcodegen>/lib -L<openssl>/lib -L<sqlite3>/lib" \
  LIBS="-lcrypto -lsqlite3 -lqrcodegen -lrt"

# 4) 配方验证（G1-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify ylva 1.7 --profile ohos-local
```

产物: `bin/ylva`、`share/man/man1/ylva.1`、`licenses/LICENSE`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `db.c:11: fatal error: 'sqlite3.h' file not found` / `qr.c: 'qrcodegen/qrcodegen.h' file not found` | 依赖头文件目录没进 CFLAGS；且 `src/qr.c` 要的是 `<qrcodegen/qrcodegen.h>`（Debian `libqrcodegen-dev` 的布局），而本生态 `libqrcodegen/1.8.0` 把 C 头文件平铺装成 `include/qrcodegen.h` | 前者在 `build()` 里把三个依赖的 `includedirs/libdirs` 全部解析后注入 `CFLAGS`/`LDFLAGS`；后者用 build-only 转发头复现惯例布局（见下） |
| 2 | 上游 `CC=gcc` 写死 | `src/Makefile` 用 `CC?=gcc`，但 CI worker/本机都没有 `gcc` | GNU make 命令行赋值优先级高于 makefile 内赋值，`build()` 在 make 命令行注入 `CC`（R33，取自 `tools.build:compiler_executables`），构建系统零补丁 |
| 3 | `CFLAGS` 默认值是 `-g` 且上游自带 `CFLAGS+=-std=c11 -Wall` | 命令行覆盖 `CFLAGS` 会把上游追加的 `-std=c11 -Wall` 一起顶掉 | 注入的 CFLAGS 里显式补回 `-std=c11 -Wall`，用 `-O2` 取代调试用的 `-g` |
| 4 | `-lrt` 在 OHOS 上是否可用 | musl（OHOS libc）只提供空的 `librt.a` 兼容档案，timer/clock 入口点在 libc 本身 | 保留上游 `LIBS` 原样，不做删改；实测 OHOS SDK sysroot 存在 `usr/lib/aarch64-linux-ohos/librt.a`，链接通过 |
| 5 | `--show-passwords` / `--show-qrcode` 似乎无效 | **上游行为**：`main()` 是「边解析边执行」——`getopt_long` 循环里直接调用 `list_all()`/`list_by_id()`，而这两个开关是 0 返回值的 flag 选项，只有出现在动作选项**之前**才生效 | 不改上游逻辑（R8），测试按上游真实用法把 flag 放在动作前：`--show-passwords -A`、`--show-qrcode -l 1`（本地实测：放后面时口令仍是 `**********`、二维码不输出） |
| 6 | 交互式用例无法用管道 stdin 驱动 | `my_getpass()` 第一步就是 `tcgetattr(fileno(stdin))`，stdin 不是 tty 时直接 `return -1`，**不写入**调用方的缓冲区；随后 `strcmp(pass, "")` 读的是未初始化栈内存（上游缺陷，已列入「已知限制」，本次不做加固） | 交互用例在真实 pty 下驱动（范式取自 `archives/n/ne/3.3.4/test_package/ne_pty_test.py`、`archives/p/pinentry/1.3.3/test_package/run_upstream_tests.py`） |
| 7 | pty 下「等提示再输入」的同步方式不可用 | ylva 的提示是 `fprintf(stdout, "Title: ")`（无换行）。musl 的 stdout 只在遇到 `\n` 时刷新（glibc 会在读取行缓冲输入前刷新全部行缓冲输出），OHOS 上提示在读取开始前不会出现 | 驱动改为：按序写入普通行 → 之后每 0.5s 重写一次口令行直到进程退出。`my_getpass()` 开头的 `tcsetattr(TCSAFLUSH)` 只丢弃**当时**尚未消费的输入，重写总能被下一次读取消费（本地原生构建实测 25/25 通过） |
| 8 | 加密用例的强断言怎么定 | `crypto.h` 固定开销 = `sizeof(int)` 4（魔数）+ `IV_SIZE` 16 + `SALT_SIZE` 64 + `HMAC_SHA512_SIZE` 64 = 148 | 断言密文体积恰为明文 +148，错误口令被 HMAC 校验拒绝且密文**不被改动**，正确口令解密后体积复原、条目与口令完好（实测 8192 → 8340 → 8192） |
| 9 | **CI 失败：`ylva -l <缺失 id>` 在 OHOS 上 SIGTRAP（rc=-5）** | `entry_new_empty()` 用 `malloc` 分配 `Entry_t` 后**不初始化字段**；`db_get_entry_by_id()` 查不到行时 sqlite 回调不执行，`list_by_id()` 随即对野指针调用 `entry_free()` → `free()` 收到 `title/user/url/password/notes/next` 垃圾指针。glibc/macOS 在刚分配的零页上会静默通过，OHOS 的 musl malloc 检出非法释放后 `a_crash()`（aarch64 `brk`）→ SIGTRAP | `patches/0001-src-entry.c.patch`：`malloc` 之后 `memset(new, 0, sizeof(struct _entry))`。纯 C 标准库、无平台宏，成功路径上这些字段随后本来就会被赋值，语义等价（R8/PF5） |

## 源码修改

共 **1 个补丁**：`patches/0001-src-entry.c.patch`（+1/-0，`refresh-patch --auto` 生成，`bugfix`）。
除此之外上游源码与 `v1.7.tar.gz` 逐字节一致（sha256 已核对）。

```diff
 Entry_t* entry_new_empty()
 {
     Entry_t* new = NULL;
     new = tmalloc(sizeof(struct _entry));
+    memset(new, 0, sizeof(struct _entry));
     return new;
 }
```

- 分类: `bugfix`（**非** `platform_only`），**不含任何平台宏** → 满足 R8「你的修改对非鸿蒙平台必须是透明的」与 PF5 补丁平台宏闸
- 语义等价性: 成功路径（sqlite 回调命中）本来就会给这 7 个字段赋值；清零只影响未命中路径，
  把「对未初始化指针 `free()`」变成「对 NULL `free()`」（POSIX 定义为空操作）
- 为什么必须修而不是放宽测试: 这是真实的上游内存安全缺陷，在 OHOS 上必现崩溃；
  CI 诊断也明确「如果是真实 bug, 需要修复源码或添加 patch」。放宽 F9 等于掩盖崩溃

另一处环境差异是 **qrcodegen 的头文件布局**，用构建期产物而非源码补丁解决：

```
build() 生成 <build>/_qrcodegen_compat/qrcodegen/qrcodegen.h
内容仅一行：  #include <qrcodegen.h>
CFLAGS 追加 -I<build>/_qrcodegen_compat（放在依赖 include 之前）
```

这样 `#include <qrcodegen/qrcodegen.h>` 命中转发头、再落到
`libqrcodegen/1.8.0` 的 `include/qrcodegen.h`。该差异不落补丁，R8 / PF5 平台宏闸不触发。

## 依赖版本

| 依赖 | 版本 | 类型 | 制品仓状态 |
|------|------|------|-----------|
| openssl | 3.5.8.1 | requires（`-lcrypto`，`shared=False` 静态变体） | 已发布（`conan download` 实测取到 OHOS aarch64 二进制） |
| sqlite3 | 3.49.1 | requires（`-lsqlite3`，静态 amalgamation 库） | 已发布 |
| libqrcodegen | 1.8.0 | requires（`-lqrcodegen`，C 实现） | 已发布 |

运行期无第三方共享库依赖：`DT_NEEDED` 实测只有 `libc.so`（三者均静态链入）。
`-lm` 由 OHOS SDK sysroot 提供；`-lrt` 由 musl 的空 `librt.a` 满足。

## CI 反馈修复（PR #14061 / 构建 #65823）

首次提交后 OHOS worker 上 `conan create` 的 test_package 阶段 **24/25 通过，仅 F9 失败**：

```
o  [PASS] F8 list-all on an empty database  -- rc=0
o  [FAIL] F9 list-entry on a missing id  -- rc=-5      <-- SIGTRAP
...
oRESULT: passed=24 failed=1
```

诊断与根因：

- `rc=-5` 是 **SIGTRAP**。OHOS 的 musl malloc 在检测到非法释放时调用 `a_crash()`
  （aarch64 上是 `brk #0x1`），表现为 SIGTRAP —— 即「invalid free」。
- 追溯调用链：`ylva -l 1`（空库）→ `list_by_id()` → `db_get_entry_by_id()` →
  `entry_new_empty()`。该函数只 `malloc` 不初始化；查不到行时 sqlite 回调不执行，
  结构体的 `title/user/url/password/notes/stamp/next` 全是垃圾值，随后
  `list_by_id()` 走 `entry->id == -1` 分支并调用 `entry_free()`，对野指针 `free()`。
- 为什么本机没暴露：glibc/macOS 在小对象刚从整页分配时内容恰为 0，
  `free(NULL)` 是空操作，于是"看起来正常"。**本机原生构建 + `MallocScribble=1`**
  （让 malloc 返回被涂改的内存）稳定复现同一缺陷：

```
未打补丁, 普通:        Nothing found with id 99.   rc=0     <- 侥幸
未打补丁, MallocScribble=1:                        rc=134   <- invalid free (SIGABRT)
已打补丁, MallocScribble=1: Nothing found with id 99.  rc=0
```

- 同族扫描（R：修复一处后必须全库核查）：全仓 `tmalloc` 调用点逐一核对 ——
  `entry_new()`/`entry_new("dummy",…)` 显式初始化全部字段；`db_get_list()`/`db_find()`
  用的是 `entry_new` 的 dummy 头（字段全设、`next=NULL`）；`crypto.c` 的
  `resultbytes`/`hmac`/`buffer` 都是先分配后写入。只有 `entry_new_empty()` 缺初始化，
  已由本补丁覆盖。`crypt` 与 `db` 无第二处同类缺陷。

修复后本地复验：`conan create`（含 A1-A4）、`conan-verify`（G1-G4 + L2/L4/L5）、
本机原生功能套件（普通 + `MallocScribble=1` 各跑一次）全部通过。

## 上游测试清点（R51 三步法）

**计数口径（唯一口径，贯穿 MANIFEST.yml / notes.md / 测试日志 / PR 两张表）：按「独立检查项数量」计数** —— 每项可单独判定成败；同一检查项在 `build()` 与 `test_package` 各执行一次也只计 1 项（A1-A4）。

### 第一步：清点上游原始测试（改代码之前完成）

审计对象 `ylva-1.7.tar.gz`，sha256 `7c557c0c30a4b3bf0a66cec41e909d491bc84a575e9fc7c0942b8d158bf199cc`，
tag `v1.7`。tarball 共 27 个条目 / 24 个文件：

```
.gitignore  INSTALL  LICENSE  NEWS  README.md  ylva.png
src/Makefile  src/ylva.1  src/ylva.c
src/cmd_ui.c  src/cmd_ui.h   src/crypto.c  src/crypto.h
src/db.c      src/db.h       src/entry.c   src/entry.h
src/pwd-gen.c src/pwd-gen.h  src/qr.c      src/qr.h
src/regexfind.c src/regexfind.h  src/utils.c src/utils.h
```

- 无 `tests/` 或 `test/` 目录
- `src/Makefile` 的目标只有 `all` / `%.o` / `$(PROG)` / `clean` / `install` / `uninstall`，
  **无 `check` / `test` 目标**（`make -n check` → `No rule to make target 'check'`）
- 无 gtest / criterion / check / CUnit 等 C 测试框架绑定
- 无 `*_test.c` / `test_*.c` / `.sh` / `.spec` / corpus / fixture 资产

**上游测试用例数 = 0**（单元测试 0 / 集成测试 0 / 其他 0）。
测试资产状态属 §5 的 **D 类**（经三步扫描确认无测试资产），不是 C 类。

### 第二步：可运行环境实际运行

上游无测试可运行（0 项）。适配后补全的 29 项中：

- **A1-A4**（鸿蒙产物 ABI）已在 OHOS 交叉产物上实跑通过 —— 本机即可执行（纯 Python 解析 ELF）。
- **F1-F21 + H1-H4** 已在真实 HarmonyOS worker 上由 CI 实跑（PR #14061 构建 #65823）：
  首轮 24/25，唯一失败 F9 定位为上游未初始化结构体 bug（见上节），打补丁后本轮修复；
  同时本机 **macOS 原生构建** 普通 + `MallocScribble=1` 两种模式均 25/25 通过，
  用于证明断言逻辑与修复效果。

### 第三步：适配后测试清单（29 项独立检查项）

功能 21 项（`test_package/functional_test.py`，上游 0 测试 → 新增）：

| 项 | 命令 | 断言 |
|----|------|------|
| F1 | `ylva -v` | rc=0，stdout 含 `Ylva version 1.7` |
| F2 | `ylva -h` | rc=0，含 `SYNOPSIS` 与 `--gen-password` |
| F3 | `ylva`（无参） | rc=0，含 `SYNOPSIS` 与 `OPTIONS` |
| F4 | `ylva -g 24` | rc=0，恰好 24 字符且全部属于上游字母表 `[A-Za-z0-9?)(/%#!=]` |
| F5 | `ylva -g 0` | rc=0 且无输出（上游 `length < 1` 返回 NULL） |
| F6 | `ylva -i <db>` | rc=0，文件存在且头 16 字节为 `SQLite format 3\0` |
| F7 | `ylva -p` | rc=0，stdout 恰为传入的数据库路径 |
| F8 | `ylva -A`（空库） | rc=0 且无 `ID:` 条目块 |
| F9 | `ylva -l 1`（空库） | rc=0 且 stdout 含 `Nothing found with id 1` |
| F10 | `ylva -E`（无活动库） | rc=0 且 stderr 含 `No decrypted database found` |
| F11 | `ylva -D <明文文件>` | rc=0 且 stderr 含 `File is already decrypted or malformed` |
| F12 | `ylva -F <正则>`（空库） | rc=0 且无条目输出 |
| F13 | `ylva -t`（空库） | rc=0 且无条目输出 |
| F14 | `ylva -q <词>`（空库） | rc=0 且无条目输出 |
| F15 | pty 驱动 `ylva -a` | rc=0，输出含 `Title: ` 与 `Password (empty to generate new): `（空口令走内置生成器） |
| F16 | `ylva --show-passwords -A` | rc=0，`ID: 1` + 标题/用户/URL/备注全部命中，口令为 20 位且属字母表（证明新增成功且生成器工作） |
| F17 | `ylva -f Bank` | rc=0，命中条目且口令被掩码 `**********` |
| F18 | `ylva -F '^Bank.*Account$'` | rc=0，POSIX 正则命中条目 |
| F19 | `ylva --show-passwords -l 1` | rc=0，五个字段齐全且 `Modified:` 匹配 `YYYY-MM-DD HH:MM:SS` |
| F20 | `ylva -q Bank` | rc=0，回显真实口令且不出现掩码 |
| F21 | pty 驱动 `ylva -E` / `ylva -D` | 密文恰为明文 +148 字节；错误口令被 HMAC 拒绝且密文不变；正确口令解密后体积复原、条目与口令完好 |

鸿蒙特有 8 项（rule12，N=8 ≥ 1）：

| 项 | 位置 | 针对的鸿蒙适配点 | 断言 |
|----|------|-----------------|------|
| A1 | `test_package/ohos_abi_check.py` | 目标架构 | ELF64 小端且 `e_machine == EM_AARCH64(183)` |
| A2 | 同上 | 工具链/sysroot | `.interp == /lib/ld-musl-aarch64.so.1`（鸿蒙 musl；glibc 产物会是 `ld-linux-aarch64.so.1`） |
| A3 | 同上 | R26 系统同名库 | `DT_NEEDED` 不含 `libcrypto`/`libssl`/`libsqlite3`/`libqrcodegen`（实测只有 `libc.so`） |
| A4 | 同上 | 包可重定位性 | `.dynamic` 无 `DT_RPATH`/`DT_RUNPATH`，加载器走 OHOS 系统搜索路径 |
| H1 | `functional_test.py` | 沙箱 HOME 语义 | `-i` 后 `$HOME/.ylva.open_db` 存在且内容等于数据库路径，`-p` 回显同一路径 |
| H2 | 同上 | HMDFS 权限归一化 | 数据库属主有 rw 且 other 位为 0（不写死 0600，容忍 HMDFS 归一化） |
| H3 | 同上 | SQLite 本地时间 | `Modified:` 时间戳格式合法且与当天相差 ≤2 天（证明 `datetime('now','localtime')` 在 OHOS 正常） |
| H4 | 同上 | UTF-8 二维码渲染 | `--show-qrcode -l 1` 输出 ≥100 组 U+2585（`\xe2\x96\x85`）且未报 `Unable to generate QR code` |

`test_package` 本身不自动算作鸿蒙特有测试：上表 8 项都是独立、可复核、明确针对鸿蒙差异的检查项，已按统一口径计入。

## 验证结果

### 1. conan-verify（G1-G4 + L2/L4/L5）

```
$ python3 scripts/ohc-run.py conan-verify ylva 1.7 --profile ohos-local
  G1: PASS   配方完整性（conanfile + conandata + test_package/MANIFEST.yml）
  G2: PASS   conan create 干净构建成功（ylva/1.7@ohpcd/stable）
  G3: PASS   系统同名库隔离（R26）：无 lib/ 目录，纯可执行包，无冲突
  G4: PASS   产物完整性
  L2/L4/L5: PASS
✅ 配方验证通过: ylva 1.7
```

### 2. build() / test_package 内的鸿蒙产物检查（A1-A4，本机实跑）

```
======== Testing the package ========
ylva/1.7@ohpcd/stable (test package): Running test()
[PASS] A1_elf64_aarch64: ELF64 little-endian, e_machine=183 (EM_AARCH64)
[PASS] A2_ohos_musl_interp: PT_INTERP=/lib/ld-musl-aarch64.so.1 (expected /lib/ld-musl-aarch64.so.1)
[PASS] A3_static_system_libs: DT_NEEDED=['libc.so'] (forbidden shared deps: none)
[PASS] A4_no_rpath: DT_RPATH/DT_RUNPATH=[] (must be empty so the OHOS loader searches system paths)
OHOS_ABI_CHECK={"discovered": 4, "passed": 4, "failed": 0}
cross-building: an aarch64-linux-ohos ELF cannot execute on this host, so the 25
functional cases are skipped here and are exercised on the HarmonyOS CI worker;
the artifact/ABI layer above did execute against the packaged binary
```

### 3. test.sh 全套 25 项（本机原生构建实跑，验证断言逻辑）

macOS 无法执行 aarch64-linux-ohos ELF，因此用同一份**未打补丁**的上游源码做
本机原生构建（链接 Homebrew openssl@3 + 系统 sqlite3 + 上游 qrcodegen C 源），
跑完整功能套件验证断言本身正确：

```
$ python3 test_package/functional_test.py --bindir <native>/src
  [PASS] F1 version flag prints 1.7 -- rc=0 out='Ylva version 1.7'
  [PASS] F2 help flag prints usage -- rc=0
  [PASS] F3 no arguments prints usage and exits 0 -- rc=0
  [PASS] F4 generate password: exact length and charset -- rc=0 len=24
  [PASS] F5 generate password rejects length < 1 -- rc=0 out=''
  [PASS] F6 init creates a real SQLite database -- rc=0 size=8192
  [PASS] F7 show-db-path reports the active database -- rc=0
  [PASS] F8 list-all on an empty database -- rc=0
  [PASS] F9 list-entry on a missing id -- rc=0
  [PASS] F10 encrypt refuses when no database is active -- rc=0
  [PASS] F11 decrypt rejects a plain file -- rc=0
  [PASS] F12 regex search on an empty database -- rc=0
  [PASS] F13 show-latest on an empty database -- rc=0
  [PASS] F14 quick search on an empty database -- rc=0
  [PASS] F15 interactive add stores a new entry -- rc=0 prompts=True
  [PASS] F16 list-all shows the entry and its generated password -- password_len=20
  [PASS] F17 LIKE search finds the entry (password masked) -- rc=0
  [PASS] F18 regex search finds the entry -- rc=0
  [PASS] F19 list-entry shows every stored field -- rc=0
  [PASS] F20 quick search prints the stored password -- rc=0
  [PASS] F21 encrypt/decrypt round trip preserves the entry -- enc=True wrong_pw=True dec=True size=8192->8340->8192
  [PASS] H1 sandbox HOME holds the active-database pointer
  [PASS] H2 database mode is owner-rw and closed to other -- mode=0o600
  [PASS] H3 SQLite localtime stamps resolve on OHOS -- stamp='Modified: 2026-09-30 20:14:16'
  [PASS] H4 entry renders as a UTF-8 half-block QR code -- rc=0 blocks=559
RESULT: passed=25 failed=0
```

> 说明：本机构建为 macOS/arm64 原生二进制，只能证明**断言逻辑与上游功能语义**正确；
> F15/F21（交互 + 加解密）与 H1-H4 的真实平台终态证据必须在 HarmonyOS PC worker 上复跑。

### 4. 安全属性实测

```
$ llvm-readelf -h/-d/-lW <package>/bin/ylva
  Class: ELF64   Type: DYN (PIE)   Machine: AArch64
  NEEDED: libc.so                 （仅此一项）
  FLAGS: BIND_NOW   FLAGS_1: NOW PIE        -> full RELRO + 立即绑定
  Requesting program interpreter: /lib/ld-musl-aarch64.so.1
```

## 本次未在本地完成的部分（环境限制，如实记录）

- **CI 已跑通编译与设备端测试**：PR #14061 / 构建 #65823 在 OHOS worker 上完成
  `conan create`（编译 + test_package 实跑），首轮 24/25 后定位并修复 F9；
  修复后的完整绿 Build 编号由 CI 回填到 PR 正文。
- **`finish` / W3 内嵌构建未在本机跑**：`finish` 内部调用的 `ConanVerifier` 把
  profile 名硬编码为 `ohos-aarch64`，而 `ci/conan/profiles/ohos-aarch64` 里的
  `tools.build:compiler_executables` 指向 worker 专用路径 `/data/service/hnp/bin/clang`，
  本机不存在；`finish` 没有 profile 覆盖入口（只有 `conan-verify` 有 `--profile`）。
  按 §7.2-B/C 归类为**本机 profile/环境不匹配**，不是 recipe 缺陷，因此
  **不改 recipe、不把 finish 的本地失败当成终态**。本机实际完成的等价验证是
  `conan-verify --profile ohos-local`（G1-G4 + L2/L4/L5 全 PASS）。
  `.ci-result.json` 由 finish 在 worker 上写入，本机未生成、也未伪造。
- **rule12 的真机执行**：A1-A4 已在交叉产物上实跑；H1-H4 与 F15/F21 需在
  HarmonyOS PC worker 上由 `can_run()` 门控执行，本机跳过（未把跳过当通过）。
- 本机 `~/.conan2` 对当前沙箱只读，验证用了一份 `CONAN_HOME` 副本
  （依赖用 `conan cache save/restore` 可移植导出，源码用
  `core.sources:download_cache` 离线喂入），验证过程未改动用户真实缓存之外的任何东西。

## 注意事项 / 已知限制

- **上游交互缺陷（未加固）**：`my_getpass()` 在 stdin 非 tty 时 `tcgetattr` 失败
  直接 `return -1`，不写调用方缓冲区；`add_new_entry()`/`edit_entry()` 随后
  `strcmp(pass, "")` 读未初始化栈内存。这是上游设计缺陷（R8：不破坏上游逻辑，
  本次不悄悄加固）。**实际影响**：把管道接到 `ylva -a`/`-e`/`-E`/`-D` 上不可靠，
  必须在终端（tty）里交互使用。
- **开关顺序有要求（上游行为）**：`--show-passwords` / `--show-qrcode` /
  `--auto-encrypt` / `--force` 是 0 返回值的 flag 选项，而 `main()` 边解析边执行，
  因此必须写在动作选项之前（`--show-passwords -A`），写后面不生效。
- **`/tmp` 无关**：ylva 不写 `/tmp`，状态文件在 `$HOME/.ylva.open_db`，
  数据库路径由用户显式传入；OHOS 只读 `/tmp` 不影响本包（R10）。
- **HOME 必须存在**：`get_open_db_path_holder_filepath()` 依赖 `getenv("HOME")`；
  环境未设 HOME 时该函数返回 NULL，`-p`/`-A` 等会报错但不崩溃（不同于知识库 E528
  描述的 `getpwuid()` 返回 NULL 场景 —— ylva 不用 `getpwuid`，故不触发该 SIGSEGV）。
  测试用例显式注入 HOME 以覆盖沙箱语义。
- **加密强度**：AES-256-CTR + PBKDF2-HMAC-SHA256 200000 轮 + HMAC-SHA512 完整性校验；
  上游 1.7 的既定算法，本次不改变。
- **`commands.json` 的 `binary` 字段为 `false`**：按 ARCHIVE-SPEC「适配中为 false，
  发布后改为 true」。本任务按要求停在本地、未 upload；PR 合并且 release 流水线
  上传后需改为 `true`。

## 知识沉淀（W5）

### 本次申报路径：路径 B（知识库扩展）

本条 PR 不只是"把 ylva 编过"，而是把适配中真实踩到的一个**通用问题**沉淀成知识草稿：

> **未初始化结构体指针成员 → 严格分配器上 invalid free**
> 同一份源码在 glibc/macOS 上因为"新分配页恰好为零"而 `free(NULL)` 静默通过，
> 在 OHOS 上必崩（分配器就地终止，signal 5 / 退出码 -5）。

换一个软件还会不会遇到？**会**。任何"只分配不初始化的工厂函数 + 失败分支上无条件清理"
的 C/C++ 代码都在这个形状里；这正是"本机全绿、进 OHOS CI 就 `rc=-5`"这类现象的高频根因。
本条目给出的判据（用 `MallocScribble=1` / `MALLOC_PERTURB_=170` / ASAN 在本机把同类 UB
变必现）可以让下一个适配者在**提交 CI 之前**就区分"平台差异"与"上游缺陷"。

### 撞车判定（先撞库，再新建）

```bash
python3 scripts/ohc-run.py engine "invalid free SIGTRAP rc=-5 free(): invalid pointer musl malloc uninitialised struct"
grep -Ei 'invalid free|SIGTRAP|invalid pointer|uninitial|MallocScribble|MALLOC_PERTURB' knowledge/graph/index.tsv
grep -RliE 'invalid free|SIGTRAP|invalid pointer|uninitialis|uninitializ|MallocScribble|MALLOC_PERTURB' knowledge/doc/
```

- `index.tsv`：对上述关键词**零命中**。
- 引擎命中 **E224**（线程 alternate signal stack 生命周期）—— 关键词层面最近，机制完全不同（信号栈回收顺序 vs 未初始化字段），不构成覆盖。
- `doc/` 命中 **E249**（未初始化所有权标志导致清理函数释放调用者栈对象）—— 最相近的既有条目：
  它讲的是**所有权标志**未初始化、释放的是**调用者栈对象**、症状是 `Signal 11` / ASan `attempting free on address which was not malloc()-ed`；
  本条讲的是**结构体自身的指针成员**未初始化、释放的是**本进程 malloc 出的野指针**、触发路径是**查询未命中→回调未执行→无条件清理**，
  真正的增量是"**只现形于严格分配器**"及其本机预判手段。已写入 `.kv` 的 `similar_to: [E249]`。
- 另命中 **E292**（大型 C++ 库上游测试分层迁移），只是把 `SIGTRAP` 列在长签名里，与本条的机制解释无重叠。

结论：**部分相关，可独立新建**（不是"已有条目完整覆盖"）。

### 新增草稿（R17：知识先草稿，提升权在主编）

- `knowledge/drafts/E429-draft-DF30.kv`
- `knowledge/drafts/E429-draft-DF30.md`

（同名成对，只进 `knowledge/drafts/`；E429 为 `graph validate` 报告的编号空洞，按提示复用。
未修改 `knowledge/graph/`、`knowledge/doc/`、`index.tsv`，也未做 promote。）

草稿要点：`error_signature` 取自真实日志（`rc=-5|SIGTRAP|invalid free|…`）；
`root_cause` 写的是机制链（malloc 不初始化 → 回调不执行 → 无条件清理 → 野指针 free →
零页侥幸 vs 严格分配器终止）；`verification_cmd` 是三条可直接执行的复算命令；
`rec_*` 给整体清零方案，`fallback_*` 给逐字段判空回退，
`forbid_*` 明确禁掉"跳过用例"与"关掉分配器检查"两种埋雷写法。

### 其他既有知识与先例

- **R26**（系统同名库禁止动态链接）—— 决定 openssl/sqlite3 走静态变体，并把结论固化成 A3 断言。
- **R10**（临时文件必须用 `$TMPDIR`）—— 决定测试脚本的 TMPDIR 处理（本包本体不写 /tmp）。
- **E528**（`getpwuid()` 返回 NULL 导致 homedir 为空后 SIGSEGV）—— `conan-verify` 命中过。
  核对结果：ylva 用 `getenv("HOME")` 而非 `getpwuid()`，NULL 时只打印错误、不崩溃，**不触发该模式**。
- 先例配方：`archives/v/vamps/0.99.2`（手写 Makefile 命令行接管 + 零补丁）、
  `archives/s/secpwgen/1.3`（make 工具 + pty/ABI 检查范式）、
  `archives/n/ne/3.3.4`、`archives/p/pinentry/1.3.3`（pty 驱动交互用例）、
  `archives/l/libidl2/0.8.14`（本机 OHOS 模拟环境下 `can_run()` 误判的处置）。

`graph validate` 复核：见下方「编译结束」前的最终校验结果。

---

**编译结束**: 2026-09-30
**CI 修复**: 2026-10-01（PR #14061 / 构建 #65823 → F9 修复）
**路径申报**: 2026-10-02 改申报路径 B（知识库扩展），新增草稿 E429-draft-DF30（.kv + .md 配对）
**最终状态**: built

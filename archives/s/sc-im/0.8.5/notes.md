# sc-im 0.8.5 适配笔记

任务：积分赛（任务卡 10412）。上游 sc-im（Andrés Martinelli，`andmarti1424/sc-im`），
终端（ncurses）电子表格，产物为单个 CLI `sc-im` + 助手脚本 `scopen`（application，
无库产物；软件级 `commands.json` 已声明 type=tool）。

## 上游形态

- **版本锚点**：`git ls-remote --tags https://github.com/andmarti1424/sc-im.git` →
  `refs/tags/v0.8.5` → `42d0123564a79ab4935a9e302dcd12b39e9b6a8c`
  （peeled `0d82c0894399fd3254c33ff0e38b35f2311e139a`）。早期别名路径
  `github.com/andmarti64/sc-im` 已 404（curl 实测），不作源锚点。
- 源 tarball（GitHub tag 归档，按需生成、无发行资产 sha256 可交叉核对，取本机下载值）：
  `49adb76fc55bc3e6ea8ee414f41428db4aef947e247718d9210be8d14a6524bd`（1677609 字节）。
- **构建系统：根目录无构建文件，唯一入口 `src/Makefile`（裸 Make，无 configure/CMake/meson）**
  → `manifest.build.system` 显式钉 `makefile`（clean_verify 的 G0 探测链
  CMake > meson > configure > Makefile 对「入口在子目录」的工程必然判错）。
- 需要 bison：`y.tab.c: gram.y` 由 `$(YACC) -d` 生成；设备 HNP 自带 bison 3.8.2，
  配方仍以 `tool_requires("bison/3.8.2")` + `YACC="bison -y"` 钉死（不依赖 worker 是否装 yacc）。
- 上游测试：`tests/run_all_tests.sh`（glob `test*.sh`）+ assert.sh 断言框架；
  **`src/Makefile` 没有 check/test 目标**（CI L1c 的 "no upstream make check" 属预期形态，
  非阻塞），故上游测试在构建树内由驱动脚本执行并留档 `reports/upstream-tests.md`。

## 依赖与 xlsx 禁用（任务卡「领前必补」风险 1）

| 依赖 | 在档（`conan list -r=ohpcd`） | 处置 |
|---|---|---|
| ncurses/6.6（必需，宽字符） | ✅ 3 个版本 | `requires`，实跑 `conan install --build=missing` 组合 rc=0 |
| libxls/1.6.3（xls 导入） | ✅ | `requires`（默认 shared=False 静态） |
| bison/3.8.2（构建工具） | ✅（连带 m4/1.4.19 在档） | `tool_requires` |
| **xlsxio / libxlsxwriter（xlsx 族）** | ❌ **各 0 条** | **缺省禁用**（见下） |

- `conan list "xlsxio*" -r=ohpcd` 与 `conan list "libxlsxwriter*" -r=ohpcd` 均
  `Found 0 pkg/version recipes`；PF4 依赖闸禁止捎带适配依赖 ⇒ xlsx/ods 族不声明。
- **开关机制（不是 configure 开关）**：`src/Makefile` L101–132 四条
  `ifneq ($(shell pkg-config --exists … || echo no), no)` 条件分支——
  `libzip+libxml-2.0` 控 `-DODS -DXLSX`（导入）、`xlsxwriter` 控 `-DXLSX_EXPORT`（导出），
  **均带失败分支 ⇒ 属缺省可选依赖处置，非硬依赖，不触发 W0-2 止损**。
- **禁用方式**：配方不声明对应 requires，且 `build()` 把 `PKG_CONFIG_PATH` 与
  `PKG_CONFIG_LIBDIR` 同时钉到 PkgConfigDeps 生成目录——LIBDIR 排除系统默认 pc
  搜索路径，保证**设备与 worker 探测面一致**（设备系统 pc_path 实测指向不存在的宿主
  目录，裸探测 libxml-2.0/libzip/xlsxwriter 全部 not found；不能依赖这一点）。
- **禁用事实的产物自证**：`sc-im --version` 打印全部编译宏，`-DXLSX/-DODS/-DXLSX_EXPORT`
  三者缺席（test_package 断言 4，CI 每轮复跑）；`-DNCURSES -DXLS` 在（断言 2/3）。
- 受影响的测试项：上游 100 条断言中没有直接跑 xlsx 读写的用例（功能断言覆盖
  GETNUM/UNDO/YANK/DELETE/@replace/@getent 等），因此**禁用本身不新增 NOT_RUN**；
  xls 导入因 libxls 在档保持可用。

## OHOS 适配要点（4 个补丁，全部只改失败路径/环境形态/测试驱动）

1. **`patches/0001-src-main-c-headless-no-tty-portability.patch`（portability，影响二进制）**
   `read_stdin()` 读完管道后无条件 `freopen("/dev/tty","rw",stdin)`，失败即
   `perror + exit(-1)`；nocurses 分支 `fopen("/dev/tty")` 失败时 `sc_error(...)` 且
   下方 `fgetws(…, f)` 会解引用 NULL。**无控制终端时每次非交互运行
   （`--version`/`--help`/管道命令）都 rc=255 且 stderr 多一行 `Bad file descriptor`**：
   后果一，conan-verify L2 与 CI L2 的 `--version`/`--help` 双失败 → 冒烟闸
   （scopen 同时因补丁 0002 失败 ⇒ tested=0 → FAIL）；后果二，上游 assert.sh 是
   整串精确比对，多一行即全部功能断言失配（补丁前实测 11/11 红，归档
   `$TASK_DIR/upstream-tests-result-prepatch-nopty.json`：FAIL 11 / PASS 0 / SKIP 80，
   `tests_dir=w0/applytest`——该树自证 `main.c` 仍含 `exit(-1)`，逐脚本失败原文
   `upstream-test-logs-prepatch-nopty/`；同为未打 0001 但带 pty 驱动时 PASS 11
   = pty 提供控制终端即掩盖该缺陷的交叉证据）。
   处置：freopen 失败改为 `sc_debug + clearerr + put(quit_afterload,1) + return`，
   main() 的 f==NULL 分支同样置 quit_afterload；**消息一律降 sc_debug**（sc_error 在
   nocurses 下写 stderr，会污染输出契约）。有控制终端时行为与上游逐字一致。
2. **`patches/0002-src-scopen-shebang-env-no-S.patch`（portability，安装产物）**
   `src/scopen` shebang `#!/usr/bin/env -S bash -a` → `#!/usr/bin/env bash`。
   设备 `/usr/bin/env` 是 toybox，无 `-S`（实测 rc=125 `Unknown option 'S'`），
   安装后的 `bin/scopen` 直接不可执行；`-a`（allexport）对脚本无作用。
3. **`patches/0003-tests-ohos-valgrind-optional-env-no-S.patch`（test-adaptation）**
   - valgrind 不在设备、`conan list valgrind* -r=ohpcd` 0 条 ⇒ `VALGRIND_CMD` 改为
     `command -v valgrind` 探测、缺席置空；每脚本 8 条 memcheck 断言包进条件，
     缺席打印 `SKIP[<suite>]` 行由驱动计数（**不进 PASS**——`assert_iffound_notcond`
     对不存在的 vallog 恰好静默通过，是假绿面）；
   - `rm *_vallog` 加存在性守卫，否则 `set -e` 在第一条 rm 提前退出、套件连
     `assert_end` 摘要都打不出来（补丁前实测形态）；
   - `run_all_tests.sh` 的 `/usr/bin/env -S bash` → `/usr/bin/env bash`。

4. **`patches/0004-tests-ohos-memcheck-substitute.patch`（test-adaptation，外部审查返修第二轮）**
   valgrind 在本设备**不可运行**（见下节「memcheck 断言替代验证」），补丁 0003 的
   「缺席 ⇒ SKIP」在外部审查 191644925 判为「少测=没测」。本补丁给 10 个测试脚本加
   **条件编译分支** `MEMCHECK_MODE`（`valgrind` / `subst` / `none`），并新增两个文件：
   - `tests/ohos-memcheck-subst`（POSIX sh 执行器）：一次调用里跑两趟——
     ① 原始程序 + `LD_PRELOAD=ohos-leaktrack`（其 stdout/stderr 就是功能断言看到的输出，
     **功能断言仍在原始二进制上原样跑**）；② ASan 版被测程序（取其诊断）；随后把两者
     合成**同款 memcheck 行式**的 `${NAME}_vallog`，使上游断言行**逐字不变**即可执行；
     产物缺失（编译失败/ASan 缺失）时写 `SUBSTITUTE UNAVAILABLE` 并退 127 ⇒ 断言变红，
     **宁可红、不空过**。
   - `tests/ohos-leaktrack.c`：LD_PRELOAD 分配器记账 + LSan 同款保守可达性分析，
     输出 `definitely/indirectly/possibly lost` 与 memcheck 同款行。
   - 断言块改为：`none` ⇒ 8 条整组 SKIP；否则先跑 6 条（泄漏 3 + 越界 3），再
     `valgrind` 分支跑未初始化 2 条 / `subst` 分支打 `SKIP[…]: 2 memcheck assertions`。
     **每脚本断言行总数仍为 8 条**，N 清点命令与数值（100）与上游逐字一致。

## 测试口径（断言调用数，`TOTAL = PASS + FAIL + SKIP + NOT_RUN`）

| 项 | 数 | 取数 |
|---|---|---|
| TOTAL | **100** | `for f in tests/test*.sh tests/test7.sh-temp-disable; do grep -cE '^\s*(assert\|assert_raises\|assert_iffound_notcond)\b' "$f"; done` 逐文件相加（\b 排除 assert_end 汇总行：可运行 10 个=91 + test7=9）。**补丁 0004 后每脚本仍只有 8 条 memcheck 断言行**（未重复），同一条命令复跑仍得 100 |
| PASS | **71** | 分两类逐条标注：**上游原样执行（功能）11** + **上游断言行原样执行·替代日志来源 60**（泄漏 3 族 + 越界 3 族 × 10 脚本；断言代码逐字未改，日志由 ohos-leaktrack / AddressSanitizer 生成，见下节） |
| FAIL | 0 | |
| SKIP | **20** | 未初始化 2 族 × 10 脚本：`SKIP[<suite>]: 2 memcheck assertions (uninit families: OHOS 无等价手段)`——无 MSan 运行时、LSan 不支持、valgrind 不可用（下节有穷尽论证与静态分析对照） |
| NOT_RUN | **9** | `test7.sh-temp-disable`：上游改后缀停用（`tests_to_add` 记载：undo/redo 恢复公式失败） |
| 恒等式 | 100 = 71+0+20+9 | 两驱动模式（`SCIM_TEST_PTY=0/1`）同分，结果 JSON `ok=true`、`vallog_integrity=pass` |

驱动：`$TASK_DIR/run_upstream_tests.py`，两种模式**同分**：
`SCIM_TEST_PTY=0`（纯管道非交互，补丁 0001 后的真实 CI 形态）与
`SCIM_TEST_PTY=1`（pty 交叉核对，对应任务卡「需 pty 模拟 tty」的风险处置）。
沙箱 `HOME=$TASK_DIR/test-home`；单脚本超时用 select+deadline 实现（不用 toybox `timeout`，
见 device-facts §一.25）。原始日志与结果 JSON 在 `$TASK_DIR/upstream-test-logs-*` /
`upstream-tests-result-*.json`，`reports/upstream-tests.md` 有逐字摘录。

`test_package` 消费者断言 7 项（4 项上游功能/依赖复验 + 3 项鸿蒙特有），与
`test_package/MANIFEST.yml` 的 `assertion_count` 一一对应。

## memcheck 断言替代验证（外部审查 191644925 返修：80 条 SKIP → 60 条真实执行）

**为什么不能用 valgrind**（三路勘察 + 本轮独立复核，全部可复跑）：设备无该命令、
`conan list "valgrind*" -r=ohpcd` 0 条（不得自行导入平台依赖）；任务本地用设备
clang/lld 从源码构建 `valgrind-3.23.0` **能建出来、能启动、guest 能翻译执行**，但
**SIGSEGV 永不投递给它的 handler** ⇒ 进程直接 139、退出摘要（HEAP SUMMARY/ERROR
SUMMARY）永远出不来。本轮独立复核把上一轮留在调度器里的诊断性
`kill(self,SIGSEGV)` 探针**摘除后重建**，干净 guest（`malloc/free/printf` 三行）仍
139；`--tool=none`（无 memcheck 影子检查）同样 139；`--main-stacksize=64M` 无效
⇒ 与工具/栈无关，是执行期自然 fault 在内核层被吞（`$TASK_DIR/valgrind-probe/`
`exp-nokill.sh`、`exp2.log`、`A.log`、`B.log` 可复跑）。结论：**memcheck 断言无法由
valgrind 产生日志**，必须替代。

### 逐族替代方案与等价强度论证

上游 8 条断言全是 `assert_iffound_notcond <log> <pattern> [<cond>]` 的**否定断言**
（模式出现即红，被 `<cond>` 过滤的行除外），逐族处置：

| 族 | 条数 | 替代手段 | 等价/更强的论证 | 负向对照（注入缺陷 → 断言红） |
|---|---|---|---|---|
| 泄漏：definitely lost | 30 | `tests/ohos-leaktrack.c`：LD_PRELOAD 记账 + 保守可达性（根集=退出期寄存器 + `/proc/self/maps` 可写区 + 存活块内容，先扫根再从已标记块传播，避免自指/环互证），LSan 同款方法（LSan runtime 在 OHOS 不可用） | 检出面**不小于** memcheck：memcheck 的 definitely lost = 无**已定义**词指向；本工具用保守词扫描，只可能把「垃圾词恰好像指针」算成可达（与 LSan 同款保守性）。平台运行时自有分配点（`CachedParameterCreate`/`getdelim`/`_Znwm`）按**来源符号**抑制并**单独如实打印**——等价于 memcheck 的 `--suppressions`；被测程序自身的 malloc/calloc/realloc/free 全部计数 | 注入「函数返回后指针丢弃」⇒ `definitely lost: 64 bytes` ⇒ 红（5/5 次稳定） |
| 泄漏：indirectly lost | 30 | 同上（lost 图内入边分类） | 与 memcheck 同定义：lost 块被其它 lost 块指向 ⇒ indirectly | 注入 `a=malloc; b=malloc; *a=b; 丢弃 a` ⇒ `definitely 64 + indirectly 64` 双红（5/5 稳定） |
| 泄漏：possibly lost | 30 | 同上（仅被块内偏移指针命中 ⇒ possibly） | 与 memcheck 同定义（interior pointer only） | 注入 `static keep = p+8` ⇒ `possibly lost: 96 bytes` ⇒ 红 |
| 越界：Invalid read/write/Invalid free | 30 | ASan 版被测程序，报告**行式翻译**进同一 vallog（`READ of size`→`Invalid read of size`、`WRITE of size`→`Invalid write of size`、`attempting free…/double-free`→`Invalid free() / delete`）；未映射的 ASan ERROR 一律翻译成红行，绝不静默放过 | ASan 检出面**不小于** memcheck：memcheck 无堆/栈/全局 redzone（只查「不可寻址」），ASan 另有 redzone + use-after-free（quarantine）+ use-after-scope/return；两者对「越界落进另一有效对象」同为盲区。`Invalid free` ↔ ASan `attempting free on address which was not malloc()-ed`/`double-free` 一一同类 | 注入堆越界读 ⇒ `Invalid read of size` 红；越界写 ⇒ `Invalid write of size` 红；`free(p+8)` ⇒ `Invalid free() / delete` 红（各 1 次全中） |
| 未初始化：Uninitialised value / Conditional jump | 20 | **无等价手段 ⇒ 如实 SKIP** | 见下 | — |

**未初始化 2 族为何保持 SKIP（穷尽论证）**：①MSan 运行时缺失——SDK
`llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/` 有 asan/hwasan/gwp_asan、**无 msan**；
②LSan 不可用——`ASAN_OPTIONS=detect_leaks=1` 实测 `detect_leaks is not supported`；
③valgrind 不可用（上文）；④可行替代都**严格更弱**：`-ftrivial-auto-var-init` 差分只在
未初始化值改变可观测输出时才红（分支依赖未初始化但结果巧合一致时漏检，memcheck 会报），
且不覆盖堆来源（族 4 明写 `created by a heap allocation`）；⑤静态分析不等价——实测
`-Wconditional-uninitialized` 只报**栈上**未初始化（`int x; if(x==…)` 有告警），
**堆上** `int *p=malloc(4); if(*p==…)` 无任何告警（`$TASK_DIR/subst/uninit_probe.c`）。
按「判据强度不得降级」，宁留 SKIP 也不换更弱判据。

### 计数纪律与两处必须披露的事实

- **两类执行分开标注**：`上游原样执行（功能断言）11` / `上游断言行原样执行·替代日志来源 60`
  / `SKIP 20（未初始化，无等价手段）` / `NOT_RUN 9`；`TOTAL=100=71+0+20+9` 恒等式两模式闭合，
  驱动另带完整性闸（每脚本 vallog 必须真实存在、含 leaktrack 行、无
  `SUBSTITUTE UNAVAILABLE`，否则非 0 退出、计数不作数）。
- **披露 1（上游断言原本是空过的）**：上游 `VALGRIND_CMD='… --log-file=${NAME}_vallog …'`
  写在**单引号**里，shell 不做二次展开 ⇒ valgrind 实际写文件名字面量 `${NAME}_vallog`，
  而断言读的是展开后的 `test1_vallog` —— 文件不存在、`grep` 返回空、
  `assert_iffound_notcond` **恰好静默通过**。即上游即使装了 valgrind，这 8 条也**恒过**。
  本轮不改这 8 条断言行（保持逐字原样），改由替代执行器把日志生成在**断言真正读取的**
  文件名上，断言从「空过」变成「真查」。
- **披露 2（`0 bytes` 过滤器的位数副作用）**：上游第 1–3 条断言的 `<cond>` 是 `0 bytes`，
  会把 `…100 bytes…` 这类以 0 结尾的数值行一并过滤掉（子串匹配）。这是上游原样语义，
  **本轮未改**；负向对照因此用 64/96 等不含 `0 bytes` 子串的数值演示变红。

### 复跑命令（取数证据）

```bash
# 上游 100 条（两种驱动模式同分）
TASK_DIR=$HOME/tmp/sc-im-0.8.5 SCIM_TESTS_DIR=$HOME/tmp/sc-im-0.8.5/w0/verify4/tests \
  SCIM_TEST_PTY=0 PKG_CONFIG_PATH=$HOME/tmp/sc-im-0.8.5/m1 \
  PKG_CONFIG_LIBDIR=$HOME/tmp/sc-im-0.8.5/m1 SCIM_SUBST_DIR=$HOME/tmp/sc-im-0.8.5/subst/run \
  HOME=$HOME/tmp/sc-im-0.8.5/test-home python3 $HOME/tmp/sc-im-0.8.5/run_upstream_tests.py
# 结果：TOTAL=100 PASS=71 FAIL=0 SKIP=20 NOT_RUN=9 ok=true vallog_integrity=pass
# N 清点（与上游同一条命令）：可运行 10 个=91 + test7=9 ⇒ 100
```

## 构建与验证

```bash
# 配方开发轮（已通过）
conan create archives/s/sc-im/0.8.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 采信轮（清缓存 → conan-verify → 证据副本 → finish 前快照）
sh tools/conan_verify_round.sh sc-im 0.8.5 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
```

编译命令（配方 `build()` 同款）：
`make -C src CC=<tools.build:compiler_executables[c]> YACC="bison -y" prefix=<package_folder> -j1`，
pkg-config 双钉见上；`prefix` 必须在**编译期**传入（`HELP_PATH`/`LIBDIR` 是编译宏，
不传按上游默认 `/usr/local` 编译，安装后 `help` 命令去 `/usr/local/share/sc-im` 找不到文件）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 打印「嵌套源码提升完成: doc/grammar_yacc_tools → .orig」，`.work` 只剩 5 个文件 | sc-im 根目录没有顶层构建文件，`_BUILD_MARKERS` 在子目录 `doc/grammar_yacc_tools/Makefile` 命中 → 被当源码根提升覆盖（与 rtklib DRAFT-E628 同族） | 用 `OHC_INIT_BUILD_TARBALL` 种子 + `--strip-components=1` 重新解包 `.orig`/`.work`，并把 `manifest.build.system` 钉 `makefile` |
| 2 | `make install` 报 `make: install: No such file or directory` | toybox `install` 只在 `/system/bin`，而 dsh 会话与 conan 继承的 PATH 都不含它 | `package()` 内 `os.environ["PATH"] = "/system/bin:" + PATH`（worker 本含 /system/bin，前置幂等） |
| 3 | 无控制终端下 `--version` rc=255 + `Bad file descriptor` | 上游 `freopen("/dev/tty")` 失败即 `exit(-1)` | 补丁 0001（失败路径降级，见上） |
| 4 | `run_all_tests.sh` rc=125 `Unknown option 'S'` | `/usr/bin/env` 是 toybox，无 `-S` | 补丁 0003（入口行）+ 补丁 0002（scopen shebang） |
| 5 | 上游测试套件连摘要都打不出，只剩 `rm: *_vallog: No such file` | valgrind 缺席 → vallog 不存在 → `set -e` 提前退 | 补丁 0003（可选化 + 存在性守卫 + SKIP 计数） |

## 知识沉淀（路径 B）

- `knowledge/drafts/DRAFT-E682-sc-im-0.8.5-headless-tty-test-drive.{md,kv}`
  —— 终端类程序无控制终端的三处测试断点与处置次序；
- `knowledge/drafts/DRAFT-E683-sc-im-0.8.5-pkgconfig-libdir-optional-feature-off.{md,kv}`
  —— 可选依赖不在档时的 pkg-config 双钉「缺省禁用」定式与产物自证。

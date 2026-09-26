# ledmon 0.97 适配记录（hw-5，2026-09-24）

## 任务
平台任务 id=8068（claimer=m0_68260377）；上游 https://github.com/intel/ledmon tag v0.97
（sha256 40ee7e…2d4b，GET 200 实测 99216B）。C / autotools。产物 = ledmon（root 守护进程）+
ledctl（CLI），sbin_PROGRAMS，动态链 libpci/libudev/sgutils2/librt。

## W0 / W0b
- 依赖 eudev/3.2.14、libsgutils/1.46、pciutils/3.13.0 全部 BINARY_OK
  （`conan install --requires=… -pr:h=… --build=never` 实测，设备 2026-09-24）。
- systemd 子目录：OHOS 无 systemd，上游默认关闭（不传 --enable-systemd）。
- librt：设备 OHOS 工具链 `clang t.c -lrt` 链接通过（AC_CHECK_LIB 可过）。
- 无同软件历史 notes（archives 无 ledmon）。任务声明语言 cpp，源码实为纯 C
  （autotools）——按 C 适配，不构成语言不匹配终止条件。

## 构建系统预检与适配点

### 工具链与探测（配方侧，非补丁）
1. **tag tarball 无 configure/Makefile.in**（GitHub tag archive 不含 autotools 生成物）
   → `autoreconf -fi` 自举 + `tool_requires(automake/1.18, pkgconf/3.0.5)`。
   不需要 libtool：configure.ac 无 `LT_INIT`（先按 cliquer 先例加了，实测无用已去掉）。
   E011 的 umask 077→022 修补必须在自举之后做（自举会重新生成 configure）。
   **R6 例外的技术理由**：该修补的对象是 `autoreconf` 在**构建工作区**内生成的 `configure`
   （不入库、不是 patches/ 内容、tag 源包内本就没有受版本管理的 configure），且有
   `if "umask 077" in text` 前置判断因而幂等；上游随包不提供 configure，故没有编辑到受管文件的路径。
2. **CI worker 不执行 shebang 脚本、且 hnp SDK 路径（`/data/service/hnp/bin/perl`）本机不存在**
   → 沿用已合入的 `archives/a/avahi/0.9_rc5` 手法：generate() 内编译一个小型 **ELF C launcher**，
   把 perl 绝对路径与固定参数烤进二进制，用它顶替 `ACLOCAL`/`AUTOMAKE`。
   本机额外一行 `shutil.which("perl")` 回退（CI 行为与 avahi 一致）。
3. **`PKG_PROG_PKG_CONFIG`**：pkg.m4 由 `tool_requires(pkgconf)` 的 `share/aclocal` 经
   `ACLOCAL_PATH` 提供（否则宏留在 configure 里当 shell 命令执行）；该包只发 `pkgconf`
   不发 `pkg-config` 这个名字 → `PKG_CONFIG` 显式指向其绝对路径。
4. **三元组（E007）**：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
   （config.guess 不识 HarmonyOS；两侧同写 ohos 会被 configure 误判）。
5. **`AX_CHECK_PROG([gcc])`**（configure.ac:10 → `AC_CHECK_PROG`；第 6 行是 `AM_INIT_AUTOMAKE`）
   只查 PATH 上有没有名为 `gcc` 的可执行文件，实际编译一律用 `$(CC)`（OHOS clang）。交叉工具链不提供
   `gcc` 这个名字 → 预置其 cache 变量 `ac_cv_prog_PROG_gcc=yes` 跳过探测（与仓内 ac_cv_* 预置同族做法）。
   同文件第 11 行还有 `AX_CHECK_PROG([make])`（找不到即 `AC_MSG_ERROR`）：**有意不预置**
   `ac_cv_prog_PROG_make` —— 本包的 `make` 阶段本身就要用 make，PATH 上没有它在 CI 上也走不到链接，
   预置只会把失败推迟到更难定位的位置。本次 W3 与消费者测试均按 PATH 上的 make 实跑通过。
6. **`AC_CHECK_LIB([sgutils2])`/`AC_CHECK_LIB([rt])` 探绿但链接找不到库**：AutotoolsToolchain
   不把 host 依赖的 cpp_info 路径写进 CFLAGS/LDFLAGS（PkgConfigDeps 只覆盖 pkg-config 分支）
   → generate() 内遍历 `dependencies.host`，把聚合 `includedirs`/`libdirs` 拼成
   `-I`/`-L` 追加进 CFLAGS/CPPFLAGS/LDFLAGS（不点名任何依赖，避开 L0o 的 `"curl"` 字面量静态拦）。
7. **`AC_FUNC_MALLOC` 交叉编译下无法运行探测** → 把 malloc 改写成 gnulib 的 `rpl_malloc`
   （替换件不在本工程源码内）→ 链接期 `undefined symbol: rpl_malloc`。
   预置 `ac_cv_func_malloc_0_nonnull=yes` 跳过替换（malloc(0) 返回非 NULL 本就是 musl 语义）。
8. **libpci.pc 别名**：configure 查 `PKG_CHECK_MODULES([LIBPCI],[libpci])`，而 conan 的
   pciutils 包未设 pkg_config_name → PkgConfigDeps 落盘的是 `pciutils.pc`，generate() 里
   同内容别名一份 `libpci.pc`；eudev 已设 pkg_config_name=libudev，直接命中。
9. **产物布局与签名**：sbin→bin 移动 + commands.json（R38 工具类）+ OHOS ELF 自签
   （binary-sign-tool；工具路径本机与 CI 有差异，用 `_find_tool()` 回退链解决）。
10. **test_package 运行期加载依赖**：musl 加载器忽略 DT_RUNPATH → `ledctl --version` 报
    `Error loading shared library libudev.so.1`。用 `VirtualRunEnv` + `self.run(..., env="conanrun")`
    注入 LD_LIBRARY_PATH（与 a52dec/aa3d 同法，不硬编码路径）。

### 源码补丁（conandata.yml 为 flat list 形态；strip: 1）
| # | 文件 | 根因与修法 |
|---|---|---|
| 0001 | `src/ses.h` | 引 `<asm/types.h>`，OHOS sysroot 无该头；`__u8/__u32` 由 `<linux/types.h>` 提供（sysroot 实测存在）。 |
| 0002 | `Makefile.am` | doc/ 用 pod2man 生成 man 页，CI worker 无 perl 保证 → 从顶层 SUBDIRS 去掉（纯文档产物，不影响功能面）。 |
| 0003 | `configure.ac` | `AM_CFLAGS='-Wall -I../config'` 是**相对**路径：conan 走 out-of-source（VPATH）构建时相对构建目录解析，找不到手写的 `config/config.h` → `fatal error: 'config.h' file not found`。改 `-I$(top_srcdir)/config`。 |
| 0004 | `src/utils.h` | `ssize_t` 在 OHOS musl 仅由 `sys/types.h`/`unistd.h` 声明，utils.h 无该包含链 → `error: unknown type name 'ssize_t'`（glibc 靠传递包含掩盖）。补 `#include <sys/types.h>`。 |
| 0005 | `dellssd.c`/`vmdssd.c`/`amd_ipmi.c`/`npem.c` | 四张 `ibpi2value` 表的 `{IBPI_PATTERN_UNKNOWN}` 哨兵省略尾字段：clang 下 `-Werror=missing-field-initializers` 升级为错误（gcc 不报）。补显式 `, 0`，语义不变且保留上游告警严格度。 |
| 0006 | `src/utils.{c,h}`、`src/ledctl.c` | `on_exit(3)` 是 glibc/BSD 专有接口，OHOS sysroot 全量 grep 零命中 → ledmon/ledctl 链接期 `undefined symbol: on_exit`。以 `atexit` + 记录表补一份兼容实现（`#if !defined(__GLIBC__)` 守卫，glibc 侧零影响），保留 handler 参数与 LIFO 顺序。声明放 utils.h，ledctl.c 补 `#include "utils.h"` 取原型（原先是隐式声明）。 |

补丁一律用 `diff -ruN` 对**干净解包源**生成（0004 之后的 utils.h 按累计态做基线，否则 0006 会重
复 0004 的行导致 patch_ng 拒收）；合入前整链 `patch -p1 --dry-run` 0001→0006 逐个过。

## 五维测试账本
- **N_static = 1**（粒度：**上游测试脚本文件**数）：`test/exercise_ledctl.py`（175 行独立 python
  脚本，硬编码 `/usr/sbin/ledctl`，需 root + 真实 SES enclosure）。该脚本内含 2 个 python 测试函数
  （`test_non_slot_set_path`:127、`test_slot_state_walk`:143），因三重环境前提均不可达，
  `MANIFEST.yml` 的 `assertion_count` 记 0（可执行原子用例数），与本行"静态文件数 1"是两个粒度，
  不冲突：**静态文件 1 / automake 注册 0 / 实际可执行原子用例 0**。
- **N_registered = 0**：test/ 不在 SUBDIRS，无 TESTS/check_PROGRAMS —— 上游无 automake
  测试入口（顶层只有 `make install` 语义）。
- **N_executed = 0**，逐项跳过原因：
  - `exercise_ledctl.py`：①需 root（设备无 root，AGENTS §4）；②需 SES enclosure 硬件
    （鸿蒙 PC 无 SAS 背板，脚本第一路径即失败）；③硬编码 `/usr/sbin/ledctl` 安装位置。
    三重环境性不可执行，非本次适配导致。root daemon 的"编译验证+运行期降级"收口按 E237
    既定手法执行。
- **N_consumer = 5**（test_package/test_ledmon.sh，真实执行打包 ELF + 断言）：
  C1 ledctl --version（rc=0 + 上游产品名字符串 `LED Control Application` + 版本 0.97，
  证 libudev/libpci/sgutils2/librt 符号闭合并可加载）；
  C2 ledctl --help（rc=0 + Usage）；C3 ledmon --version（rc=0）；C4 ledmon --help（rc=0）；
  C5 非 root 特权命令 → rc≠0 且 stderr 含 `Only root can run this application.`
  （ledctl.c:979 逐字；实测 rc=36 = LEDCTL_STATUS_NOT_A_PRIVILEGED_USER）。
  **C5 的 root 分支记 skip 不记 pass**：脚本汇总行输出三值
  `CONSUMER-RESULT pass=N fail=N skip=N`（本机非 root 实测 `pass=5 fail=0 skip=0`），
  整体判定仍按 `fail==0`，但"少跑一条断言"在日志里机器可见，不会静默冒充 5/5。
- 被测二进制资源：ledmon/ledctl 为轻量 CLI/daemon，test_ledmon.sh 用
  `memcap-run.py --probe` 评估后回填 manifest.max_rss_mb。

## 已知限制（逐条技术原因，非本次适配引入的缺陷）
1. **`_ledmon_status` 的退出码日志在 OHOS 上恒记 SUCCESS**：musl 无 `on_exit(3)`，替代实现走
   `atexit`，而 atexit 处理器按标准拿不到 `exit()` 的状态参数（sysroot 全量 grep 亦无该符号可链）。
   影响面仅"退出状态那一行日志文案"；两个真正做收尾的 handler（`_ledmon_fini`/`_ledctl_fini`）
   源码中显式 `__attribute__((unused)) status`，不消费该参数，故资源释放/pidfile 删除/sysfs 复位
   行为与上游一致。不做"改 main 出口"的重写，以免在无法运行期验证的 root 守护进程里引入控制流风险。
2. **上游 `exercise_ledctl.py` 0 执行**：需 root + SAS SES 背板 + 硬编码安装路径（见五维账本）。
3. **守护进程整机运行未验证**：设备无 root、无 SAS 背板；本次交付为编译/链接 + CLI 免特权面验证
   （E237 root 守护进程既定收口手法），不声称守护循环在 OHOS 上跑通。
   **交付等级按 R40 标注为"需人工确认适配完整性"**：真实功能面（守护循环、IBPI 状态机、
   `ledctl set=xxx` 的 SES/SGPIO 命令下发、`amd_sgpio.c` 缓存锁）在 OHOS 上从未执行；
   后续须在"有 root + SAS SES/SGPIO 背板"的环境补做 `ledmon` 守护运行与
   `ledctl set=locate/normal` 实机回归，结果回填本节后再谈 `published`。
4. **`/dev/shm` 上文件锁被拒 ⇒ 上游 AMD SGPIO 缓存互斥静默失效**：`src/amd_sgpio.c:229-241` 在
   自己 `shm_open` 出来的文件 fd 上 `flock(LOCK_EX)` 实测返回 `-1/errno=13(EACCES)`
   （`LOCK_SH` 同），而同序列数据面（`shm_open`/`ftruncate`/`mmap`/读写/`fsync`/`unlink`）完好；
   **上游未检查 `flock` 返回值**，所以表现为"锁根本没生效"而非启动失败。本次不改上游锁语义
   （改动落在无法运行期验证的 root 守护进程里，风险高于收益），机制与处置建议作为路径 B 知识沉淀
   （见下节与 Issue #3328）。
5. **软件级 `archives/l/ledmon/manifest.yaml` 未附带**：本仓归档门禁用 `finalize-archive` 实测只要求
   软件级 `README.md`（补上后 `缺失项: 0 / FIN_RC=0`）；仓内 `commands.json` 型工具包大量不带软件级
   manifest（抽样 400 个中多数缺失，已合入的 `archives/a/avahi` 同样只有 README），故按仓内实况交付。

## 路径 B 判定（登记表留痕：create）
`B判定=create(M10成套配送：/dev/shm 只写虚拟目录——ledmon 在 shm_open 文件上 flock 实测
EACCES(13) 且上游不查返回值⇒静默互斥失效)`。
证据链：grep 命中第 4 处控制面调用（派单只列了 3 处数据面）→ `src/amd_sgpio.c:229-241`
`shm_open("/ledmon_amd_sgpio_cache") + flock(cache_fd, LOCK_EX)`（返回值未检查）→
设备逐字探针 `~/tmp/uc2/hw-5/probe/probe_ledmon_shm.c` 实测
`flock(LOCK_EX|LOCK_NB) r=-1 errno=13`、`flock(LOCK_SH|LOCK_NB) r=-1 errno=13`，同序列数据面
（shm_open/fwrite 写入、读回、unlink 删除）全部 OK；`/dev/shm` 下 `mkdir()`/`mknod()`/`chmod()`
返回 EACCES。mknod 候选证伪：/var/tmp 整机不存在（mkdir errno=2）。
草稿：`knowledge/drafts/DRAFT-ledmon-0.97-dev-shm-write-only-virtual-dir.{kv,md}`，
蓝本 `经验文档/B草稿库/DRAFT-PKG-VER-dev-shm-write-only-virtual-dir`（§12.77 M10 配送表）。
Issue：#3328。

## W4 独立审计处置（逐条：已修 / 已申报）
审计由**独立会话**对 `upstream/main...HEAD` 的 17 个变更文件按仓内 `code_style` + `review_memory`
逐规则复核（输入 87359B，`pre_pr_audit.py generate --base-branch upstream/main` 产出），
结论 `verdict=pass`，0 P0/P1、4 P2、7 P3。处置：

| 项 | 级别 | 处置 |
|---|---|---|
| 软件级 `manifest.yaml` 缺失 | P2 | 已申报：门禁 `finalize-archive` 只要求软件级 README（实测 `缺失项: 0`），仓内 commands.json 型工具包多数不带该层 manifest（见已知限制 5） |
| R40 深度适配面未执行 | P2 | 已申报：manifest + 已知限制 3 标"需人工确认适配完整性"，并写清补做条件（root + SES/SGPIO 背板） |
| `test_ledmon.sh` 未启用安全模式 | P2 | **已修**：`set -u` + `set -o pipefail` + 参数校验；有意不加 `set -e`（要取非零 rc），理由写在脚本头 |
| C5 root 分支空操作 ⇒ 静默少跑断言 | P2 | **已修**：三值 `pass/fail/skip` 汇总，root 下记 skip 不冒充 pass |
| 补丁 0006 引入 libc 宏 | P3 | 保留：属规则 8 明文的"识别 libc/无 POSIX 等价物"例外，理由与不等价点已申报；改 configure 探测留作后续 |
| `llvm-objcopy … \|\| true` 吞错 | P3 | **已修**：补"为何可忽略"的行内注释（占位段可能不存在，把关在签后实测 exec） |
| `build()` 改写自举生成的 configure（R6） | P3 | 已申报：notes「工具链与探测」1 写明技术理由与幂等条件；收窄 glob 会改动 `build()` 而作废本轮 W3 编译证据，故本次不改，留作后续 |
| `test_package/conanfile.py` 缺文件头 | P3 | **已修**：shebang + docstring |
| `conandata.yml` url/sha256 未加引号 | P3 | **已修**：加引号（对齐已合入 `archives/a/avahi` 形态）；`patch_description` 保留含根因写法（仓内 8357 条同类普遍带括注） |
| 草稿"来源 PR/commit"待回填、小节引用错位 | P3 | 引用已对齐（已知限制 4 现真有其条）；PR 号与 commit 建号后在同一 PR 内回填 |
| 账本粒度与 `configure.ac` 行号 | P3 | **已修**：粒度三口径写入 manifest/MANIFEST/notes；行号改 `configure.ac:10`，并说明第 11 行 `AX_CHECK_PROG([make])` 有意不预置 |

## 本机环境侧（不进配方、不进 PR）
- 源码下载：ghfast 镜像在设备侧超时（R41 基建类）→ 已验证官方 tarball 按 sha256 预置到共享
  `~/tmp/ch/dlcache`（`s/<sha256>` + sidecar 同时登记官方与注入 URL），
  任务 CONAN_HOME 的 `global.conf` 增 `core.sources:download_cache`。**conandata.yml 只保留官方
  HTTPS URL**（每次跑完 `git show HEAD:…conandata.yml | grep -Ec 'ghfast|file://'` 必须为 0）。
- automake 的 PERL5LIB（`share/automake-1.18`）在 verify/finish 包装脚本里注入，不写进配方。
- 设备 `ci/conan/profiles/ohos-aarch64` 的 `tools.build:compiler_executables` 指向
  `/data/service/hnp/bin/clang`（**只在 CI worker 上存在**）；本机用影子工程
  `~/tmp/hw-5-shadow/ci/conan/profiles/`（archives 是指向本 worktree 的符号链接，配方字节完全相同）
  指回 `~/usr/local/bin/aarch64-unknown-linux-ohos-clang`。因此本地 finish 必须带
  `OHC_PROJECT_DIR=$HOME/tmp/hw-5-shadow`，否则配方 generate() 里的 ELF launcher 编译步骤报
  `/system/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found`（Error 127，**环境差异不是配方缺陷**）。
- junk_check 基线：本窗 `origin` = 用户 fork，其 `main` 落后 `upstream/main` 328 个提交，
  incremental 模式会把 157 个他人归档算进本 PR 而误报 JC6 原子性违规 → 用 worktree 根的本地
  `pr.diff`（`git diff upstream/main HEAD`，16 文件）把模式锁到 prdiff（不入 PR）。

## 发现与知识
（与 manifest.yaml `knowledge_gained` 一一对应；序号即 ref 标号）

- ✅ 1 **M10 / `/dev/shm` 只写虚拟目录**：`src/amd_sgpio.c:229-241` 在 `shm_open` 出来的文件 fd 上
  `flock(LOCK_EX)` 实测 **EACCES(13)**，而同序列的 shm_open/ftruncate/mmap/写读/fsync/shm_unlink 全部可用
  ⇒ 数据通路完好、唯锁被摘除；且上游**未检查 flock 返回值**，故表现为"静默互斥失效"而非报错。
  已作为路径 B 草稿随本 PR 提交（`DRAFT-ledmon-0.97-dev-shm-write-only-virtual-dir`，Issue #3328）。
- ✅ 2 **OHOS sysroot 无 `asm/types.h`**：aarch64 上 `__u8/__u32` 由 `<linux/types.h>` 承载，
  `ses.h` 换包含即可（0001 补丁）——签名 `fatal error: 'asm/types.h' file not found`。
- ✅ 3 **conan `pciutils` 包未设 `pkg_config_name`**：`PkgConfigDeps` 落盘 `pciutils.pc`，
  而 configure 探测的模块名是 `libpci` ⇒ generate() 同内容别名一份 `libpci.pc`（否则 `PKG_CHECK_MODULES` 报 not found）。
- ✅ 4 **GitHub tag 归档不含 autotools 生成物**：需 `autoreconf -fi` + `tool_requires(automake, pkgconf)`；
  并且 E011 的 umask 077 修补**必须在自举之后**做（自举会重新生成 configure，先补会被覆盖）。
- ✅ 5 **`doc/` 子目录依赖 pod2man**：CI worker 不保证有 perl ⇒ 0002 从顶层 `SUBDIRS` 去掉；
  man 页是文档产物，不影响功能面，属可安全裁剪项。
- ✅ 6 **`/var/tmp` 在 OHOS 整机不存在**（`mkdir` errno=2）：`smp.c` 的 `mknod` 路径不可达
  ⇒ 据此**证伪**了派单提出的 "CAP_MKNOD 被拒" 候选机制，避免把 B 判成一条不成立的结论。
- ✅ 7 **OHOS XPM 与 musl 加载器**：产物 `bin/ledmon`、`bin/ledctl` 为**动态链接** ELF
  （libudev/libpci/sgutils2/librt），`package()` 内须 binary-sign-tool 自签才能执行；
  且 musl 忽略 `DT_RUNPATH` ⇒ test_package 必须 `VirtualRunEnv` + `env="conanrun"` 注入 `LD_LIBRARY_PATH`。

## 对话记录

### 对话 #1（2026-09-24，hw-5，设备直连会话）

- configure 参数：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
  + `ac_cv_prog_PROG_gcc=yes` + `ac_cv_func_malloc_0_nonnull=yes`（原因见上"工具链与探测"第 5、7 条）。
- 编译结果：`conan-verify` G0/G1/G2/G3/G4 全 PASS；`conan create` 导出 `Copied 6 '.patch' files`；
  `test_package` 消费者测试 `CONSUMER-RESULT pass=5 fail=0`；W3 本地 CI 模拟通过。
- 审计后加固（同轮复验，未重编）：消费者脚本改为三值汇总并加 `set -u`/`set -o pipefail`/参数校验后，
  直接对**已签名打包**的 `bin/ledctl`、`bin/ledmon` 重跑一遍（`LD_LIBRARY_PATH` 由依赖包 lib 目录拼出）：
  `CONSUMER-RESULT pass=5 fail=0 skip=0`、`SH_RC=0`，无参数调用按预期 `GUARD_RC=1`；
  `python3 -m py_compile` 两个 conanfile、`yaml.safe_load` 三个 YAML/JSON、`sh -n` 与
  `finalize-archive`（`一致性问题: 0 / 缺失项: 0 / FIN_RC=0`）全通过；
  `conandata.yml` 镜像/`file://` 残留 grep 计数 0。
- 遇到的问题与定位顺序（每轮都先取第一条真实错误再改，未做盲调参）：
  ① 三条补丁被静默跳过（conandata 的 `0.97:` 键被 YAML 解析成 float）→ 改 flat list；
  ② 手写补丁 `patch stream is incomplete!`（`@@` 声明行数与实体不符）→ 一律 `diff -u` 对干净源重生成；
  ③ `ssize_t` 未知类型 → 0004；④ `-Werror=missing-field-initializers` ×4 → 0005（用 `make -k -j1`
  一次枚举全部同类错误，避免四次串行试错）；⑤ `undefined symbol: on_exit` → 0006；
  ⑥ `undefined symbol: rpl_malloc` → cache 预置；⑦ `libudev.so.1` 拒载 → VirtualRunEnv；
  ⑧ C1 断言错把 argv0 当版本串、C5 的 `id -u` 噪声 → 断言改测上游产品串并容错取 uid。
- 资源评估：`memcap-run.py --probe` 实测消费者链峰值 4MB（rc=0，0.2s）→ `max_rss_mb: 64`。

### 编译结束

- 状态: built（W3 本地 CI 模拟通过；`published` 需等 release/upload 流水线，本次不声称）
- 总耗时：≈2.5 小时（含 8 轮"第一条真实错误"定位与 B 侧真机探针）
---

**编译结束**: 2026-09-24 18:17
**最终状态**: built

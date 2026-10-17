# scrub 2.6.1-git20240819.9b4267e 适配笔记

## 基本信息
- 构建系统: autotools（git 快照形态，tarball 无 configure，需 autoreconf 自举）
- 版本形态: Debian 快照 `2.6.1+git20240819.9b4267e`，对应上游
  github.com/chaos/scrub master commit `9b4267e58581e4629c542557d5c58e39a39fa0e2`
  （实核：`git ls-remote` master HEAD == 9b4267e…；Debian pool 存在
  scrub_2.6.1+git20240819.9b4267e.orig.tar.xz，sha256 `a821bd39…c943` 与 .dsc
  Checksums-Sha256 双源一致）。Conan 包版本取 `2.6.1-git20240819.9b4267e`
  （分支门禁逐字符匹配 `archives/s/scrub/2.6.1-git20240819.9b4267e`）。
- 源锚定（R39/PF7 口径）：conandata/manifest 的 source.url 用上游官方仓库
  commit 归档 `https://github.com/chaos/scrub/archive/9b4267e58581e4629c542557d5c58e39a39fa0e2.tar.gz`
  （sha256 `773112501affcb0287f9038801f4476cf1de170fc616993bcb97d2409ed7c194`）；
  该 GitHub 树与 Debian orig.tar.xz 快照经 find 清单 diff + 逐文件 sha256 比对
  **逐字节一致**，W0 版本可得性以 Debian pool 快照归档实核（上游无 2.6.1 发行
  tarball，Debian pool 是该快照形态的权威分发渠道）。
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（OHOS aarch64 原生构建，build == host）
- 状态: built（O5 口径：合并并确认 release upload 前一律 built）

## 编译步骤

1. autoreconf 自举（OHOS 上 `autoreconf` 全链有 autoconf.m4f 加载冲突，按 abiword
   家族先例改直跑链，全部在 conanbuild 环境内执行）：
   `aclocal --force`（configure.ac 已声明 AC_CONFIG_MACRO_DIR([config])，tarball 自带
   libgcrypt.m4/x_ac_*.m4/ac_pkgconfig.m4 全部被扫描）→ 复制 ltmain.sh（经
   `$LIBTOOLIZE` 环境变量定位 libtool 包 build-aux）→ `autoconf -o configure configure.ac`
   → `autoheader`（生成 config/config.h.in）→ `automake --add-missing --copy --no-force`
   （补 install-sh/missing/depcomp/compile/config.guess/config.sub 到 config/ aux 目录）。
2. 对生成的 config.guess/config.sub 打 OHOS 识别补丁（等价
   `scripts/patch-autotools-ohos.pl` 的 5 处变换：config.guess 增 `__OHOS__` LIBC 分支与
   `*:HarmonyOS:*:*` 主机块；config.sub 增 `ohos-linux` 三元、`ohos*` OS 列表、
   `linux-ohos` 内核校验）。CI 侧不设 OHC_SKILL_ROOT，配方内嵌等价逻辑保证 CI 可复现。
3. `configure --prefix=$PREFIX --without-libgcrypt`（不传 --build/--host，铁律 R1/E007 口径；
   打补丁后 config.guess 原生识别 OHOS）。
4. `make -j1` → `make check -j1`（上游测试，见下节）→ `make install`。

## 上游测试清点申报（R51 三步法·第一步）

N = 上游测试总数 = 23，来源 `test/Makefile.am`：
- `TESTS = t01 t02 … t22`（22 项，无条件注册）＋ `t00`（`if LIBGCRYPT` 为假时追加，
  本包显式 `--without-libgcrypt` ⇒ t00 注册）。上游 master(9b4267e) HEAD 注册数与
  tarball 一致（raw.githubusercontent.com 实查 TESTS 段），N 下界 = 23 = 声明 N。
- 口径说明：`check_PROGRAMS`（pad/trand/tprogress/tgetsize/tsig/tsize/pat/aestest，
  8 个）是 `tNN` 用例的辅助程序，不属于用例数；四种口径不混用。
- 驱动方式：automake 内置 test driver（`TESTS_ENVIRONMENT = env`，
  `PATH_SCRUB=$(top_builddir)/src/scrub`），逐脚本 `exit 0`=PASS / `exit 77`=SKIP。
- 预期环境性 SKIP（真机，无 root、无 `id` 命令）：t09/t10（LLNL 专用块设备/主机名
  exp 文件缺失，`test \`id -u\` = 0 || exit 77` 首行即跳）、t18/t19/t20/t21
  （root + tmpfs/loopback 设备，同跳出口）。共 6 项。
- 预期环境性 FAIL（真机）：t13、t14 —— 脚本内 `unset TMPDIR` 强制走
  `${TMPDIR:-/tmp}`，设备 `/tmp` 只读（设备边界 §一.1），mkdir/写入失败即
  `exit 1`。上游硬编码，非 OHOS 缺陷；CI worker `/tmp` 可写不受影响。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | AC_INIT 版本取自 `m4_esyscmd(git describe …)`，tarball 无 .git ⇒ 版本空串，configure 生成即坏 | git 快照形态上游缺陷 | configure.ac 版本字面量化 `[2.6.1-git20240819.9b4267e]`（Debian `no_git_at_build_time.patch` 同型修法，字面量取 Conan 包版本使 `scrub --version` 与 ref 自洽） |
| 2 | `AM_CONFIG_HEADER` 在 automake ≥1.13 已移除，autoconf 2.73 报 possibly undefined | 宏过时 | 改 `AC_CONFIG_HEADERS([config/config.h])` |
| 3 | src/getsize.c 用 `PRIu64`/`strtoull` 格式化但未含 inttypes.h，clang15 报错 | 上游缺 include（Ubuntu #674187） | 补 `#include <inttypes.h>`（Debian `01-Includes` 同型） |
| 4 | tarball 无 configure/Makefile.in，且设备/CI worker 无完整 autotools（worker PATH 无 automake，设备 libtool 缺位） | git 快照 + CI 能力矩阵 | tool_requires `automake/1.18` + `libtool/2.5.4`（制品仓已发布，conan download 实查），直跑链自举（见编译步骤 1） |
| 5 | HMDFS 上 autoreconf 全链 autoconf.m4f 加载冲突、config.status ac_tmp 子进程写文件被拦（E114） | 设备边界 §一.12/abiword 家族实测 | 直跑链绕 autoreconf；配方预建 ac_tmp 目录 + TMPDIR 注入 + 改写生成 configure 的 `ac_tmp=$tmp` 模板与退出 trap |
| 6 | **musl 上默认/随机 pattern 擦写确定性 SIGSEGV**（12/12 复现，-O0/-O2/ASan 同崩；fillff 正常）：refill 线程在 `refill_memcpy` join 成功后未清 `mp->thd`，单块文件路径上 `refill_fini` 对同一句柄二次 `pthread_join` | 上游缺陷（glibc 容忍二次 join，musl 对已回收线程控制块再 join 是确定性 UB） | `patches/0003-src-fillfile.c.patch`：join 成功后 `mp->thd = 0`，`refill_fini` 仅对非零句柄 join 并清零；修后 12/12 通过、NNSA 400K 全流程 rc=0 |
| 7 | t12/t22 因 stdout/stderr 交错顺序与 .exp 不符 FAIL（内容逐行一致，仅 warning/diagnostic 行位置不同） | musl 对管道 stdout 也**行缓冲**（glibc 全缓冲），`2>&1` 管道下 stderr 诊断先于 stdout 批量刷出，与 glibc 捕获的 .exp 顺序相反 | `patches/0004-src-scrub.c.patch`：main 入口 `setvbuf(stdout, NULL, _IOFBF, BUFSIZ)` 统一为全缓冲（POSIX 通用，无平台宏；progress 的 fflush 不受影响）；修后 t12/t22 期望顺序复现 |

## 源码修改（refresh-patch 固化为 patches/）

- `patches/0001-configure.ac.patch`：问题 1+2（AC_INIT 版本字面量化 + AM_CONFIG_HEADER→AC_CONFIG_HEADERS）。
- `patches/0002-src-fillfile.c.patch`：问题 6（src/fillfile.c 三行；POSIX 层修法，无平台宏，R8 合规）。
- `patches/0003-src-getsize.c.patch`：问题 3（src/getsize.c +1 行）。（补丁文件名按 refresh-patch 再生成的字母序编定，与 conandata.yml 引用一致）
- `patches/0004-src-scrub.c.patch`：问题 7（src/scrub.c main 入口 +5 行 setvbuf）。
- patches/ 内不引入 `#ifdef __OHOS__`（铁律 R8）；config.guess/sub 的 OHOS 识别不进
  patches/（它们是 autoreconf 生成物，tarball 内不存在），由配方在自举后打——
  与 E007「config.guess 不识别 HarmonyOS → 自动修复补丁」同机制。

## 依赖版本

- 硬依赖：无（libc + pthread，`X_AC_CHECK_PTHREADS` 探测 -lpthread）。
- 可选依赖（全部显式关闭）：libgcrypt（`--without-libgcrypt`，走自带 aes.c，保证
  N=23 在设备/CI 一致——若依赖探测结果，有无 libgcrypt-config 会使 N 在 22/23 间漂移）；
  openssl（不启）；libprop（NetBSD 专属，探测失败自动置空）；libscrub 共享库
  （上游默认 --disable，保持默认）。
- tool_requires：automake/1.18、libtool/2.5.4（仅构建期）。

## 验证结果

（采信轮后回填：conan create 全绿 + make check 23 项 PASS/SKIP/FAIL 明细，见 reports/）

## 交付物

（采信轮后回填：bin/scrub 单执行文件；man1 页；软件级 commands.json 见 archives/s/scrub/）

## 注意事项

- 测试对 `TMPDIR` 敏感：t01/t02/… 用 `${TMPDIR:-/tmp}`，配方在 make check 前显式
  指向可写目录；仅 t13 上游 `unset TMPDIR` 例外（见上）。
- t01 造 5G 稀疏文件（`pad 5g` + `scrub -T`）：HMDFS 稀疏支持实测见采信轮记录。
- `scrub --version` 输出 `scrub version 2.6.1-git20240819.9b4267e`（来自 AC_INIT 字面量），
  test_package 据此断言。
- 擦写完成后 scrub 默认在**文件头部（偏移 0）**写 13 字节签名块
  `\001\002\003SCRUBBED!` + 结尾 NUL（`src/sig.c` 的 `writesig()`，`checksig()` 比对前
  12 字节；`-S` 关闭写入）。2026-09-24 更正：此前本行误写为"文件尾"——
  逐字节校验内容时必须用 `-S` 或排除**头部**签名块，否则误判。
- test_package 顶层判定 5 项 = A1–A4 四项断言 + E2E-1 完整安全擦除端到端消费者用例
  （6 步：NNSA 多 pass 擦写 → verify 校验 → 签名落盘 → 二次擦写被 `-f` 拦截 →
  `-f` 强制重擦 + `-r` 删除 → `-S` 对照），依据 README.md Examples 与
  man/scrub.1.in 的 EXAMPLES/`-r`/`-f`/`-S` 条目设计。

# Notes — backuppc-rsync 3.1.3.0

## 软件识别
- backuppc-rsync 是 Debian 包名，上游即 BackupPC 的 **rsync-bpc**
  （https://github.com/backuppc/rsync-bpc，tag 3.1.3.0，2020-10-08 发布）。
- AC_INIT([rsync-bpc],[3.1.3.0])；基于 rsync 3.1.3，新增 BackupPC 池文件系统
  shim 层（backuppc/ 子目录 + bpc_sysCalls.c），产物为单一工具 `rsync_bpc`，
  与原生 rsync 协议线级兼容。`--version` 输出 `rsync  version 3.1.3.0 ...`。
- 构建系统 autotools（autoconf 2.69 生成 configure.sh）；tarball 同时带
  `configure`（749 字节 /bin/sh 包装器，exec configure.sh）与 configure.sh。

## 源码获取
- URL: https://github.com/backuppc/rsync-bpc/releases/download/3.1.3.0/rsync-bpc-3.1.3.0.tar.gz
- sha256: 3eeb137319b608512b2d23c54ea8b52b511db806ffbd5fa730a394431d556f3f
  （本地下载实测；体积 883808 字节与 GitHub API 资产元数据一致）

## 上游测试审计（no_tests 判定依据）
结论：**上游发布包不存在任何测试套件**，故 test_package/MANIFEST.yml 写
`upstream_tests_exist: false` + 非空 upstream_test_audit，test_package 每轮
输出 HMBS_UPSTREAM_TEST_RESULT status=no_tests、discovered=0、executed=0。
- tarball 无 testsuite/（上游 rsync 3.1.3 的 Perl 测试被 BackupPC 打包移除）；
- Makefile.in 无 check/test 目标（仅 all/install/gen/clean/cleantests/distclean/
  man/proto/splint/doxygen 等）；
- configure.ac/configure.sh 无 TESTS/check_PROGRAMS/runtests 引用；
- CHECK_PROGS 变量仅服务 clean 目标清理 CHECK_OBJS；
- tls.c/t_unsafe.c/wildtest.c 等为 rsync 辅助源码，未接入任何测试目标。

## 配方要点（对照同族 archives/r/rsync/3.3.0 与知识库）
1. **E007 平台识别**：自带 config.guess(2013-05-16)/config.sub(2013-04-24)
   均为旧式脚本且无 HarmonyOS 支持。按 knowledge/doc/E007.md 打补丁：
   - config.guess：libc 探测 heredoc 增加 `#elif defined(__OHOS__) LIBC=ohos`；
     主 case 在 NetBSD 分支前插入 `*:HarmonyOS:*:*)`。注意 E007 FAQ——2018 年
     前的脚本必须用 `echo ... ; exit ;;` 语法而非 `GUESS=`（scripts/patch-
     autotools-ohos.pl 只生成 GUESS= 形式，对旧版无效，故按文档手工等价移植）。
   - config.sub：`case $maybe_os in` 列表加 `linux-ohos*`、OS 列表加
     `-linux-ohos*`。已本地验证 `config.sub aarch64-linux-ohos` →
     `aarch64-unknown-linux-ohos`，补丁 git apply 干净通过、sh -n 语法通过。
2. **E114 mktemp**：沿用 rsync 3.3.0 的程序化修复路径——configure --no-create
   生成 config.status 后、执行前将三类 tmp 回退模式重定向到 $TMPDIR 固定目录；
   未命中模式则跳过（交由 hmbs 平台 mktemp fallback 能力），不视为错误。
   config.status 是生成文件，不打源码补丁。
3. **E165 shebang**：build() 内仅 OHOS 将源码树 #!/bin/sh → /system/bin/sh、
   #!/bin/bash → /data/service/hnp/bin/bash。
4. **HAVE_GETPASS**：config.h.in 含 HAVE_GETPASS 探测（与 rsync 3.3.0 同因），
   config.status 生成 config.h 后程序化 undef，由 rsync.h 提供本地声明。
5. **依赖策略**：zlib 为 rsync 3.1.x 源码内置实现（configure 无系统 zlib 探测）；
   popt 显式 `--with-included-popt`（OHOS 无 libpopt）。包无外部 Conan 依赖，
   不触发 R36 链式发布检查。
6. **R26/R33**：AutotoolsToolchain 注入 -static；编译参数全部来自 toolchain，
   build() 无裸 shell 变量。
7. proto.h/proto.h-tstamp 已随 tarball 提供，构建期不需要 perl。

## test_package 设计（R34/L0d/L0e）
- test_rsync_bpc.sh：POSIX sh + toybox 兼容命令，8 个内容级用例真实执行包内
  bin/rsync_bpc：--version、单文件同步(-r)、递归目录树、更新传播、校验和模式
  (-rc) 等长变更、--delete、--dry-run、--exclude。末行固定输出
  `RESULT: N passed, M failed`。
- 刻意避开 -a/-p/-o 等属性保留选项：HMDFS 所有权/chmod 操作受限，属性行为
  因平台而异会产生假失败；内容级断言保证确定性（属性行为可在真机手工复核）。
- conanfile.py test()：CONFIG_SHELL→SHELL→/bin/sh 解析解释器（遵循 HMBS 平台
  诊断 [shell_getcwd] 教训，不硬编码 HNP bash）；Environment+apply() 注入
  RSYNC_BPC_BIN/TMPDIR；self.run() 重定向日志后解析 RESULT 行，输出
  HMBS_TEST_PACKAGE_RESULT（discovered=passed+failed）；随后复发 no_tests
  上游标记（防包缓存命中轮次缺证据）。self.run(env=) 只接受 list/None，
  传 dict 会断言失败（autotools-dev 包真机日志教训）。

## 本地配方与测试脚本验证（Windows 侧静态验证，非真机结论）
- 补丁验证：git apply --check 干净通过（core.autocrlf=false，保持 LF）；
  `sh -n` 语法通过；打补丁后 `config.sub aarch64-linux-ohos` →
  `aarch64-unknown-linux-ohos`、`config.sub aarch64-unknown-linux-ohos` 原样输出；
  config.guess 在普通 Linux 下正常产出三元组。
- test_rsync_bpc.sh 用真实 rsync 做了三态证伪：
  1) BIN 指向版本不符的真实 rsync → 7 通过/1 失败，脚本退出码 1；
  2) BIN 指向包装桩（--version 输出 3.1.3.0，其余转发真实 rsync）→
     8/8 全过，退出码 0；3) BIN 不存在 → 0/8，退出码 1。
  结论：harness 计数与退出码可靠，能抓到假二进制/缺二进制。
- 脚本退出状态修复：dash/toybox ash 家族中 `trap <fn> 0` 会以处理函数状态
  覆盖脚本退出码——finish() 先 `trap - 0` 再显式 exit 最终状态。

## 待真机预检确认
- configure/make 在 OHOS clang 下的一次性通过情况（bundled popt 编译告警可忽略）;
- -static 链接 musl 是否如 rsync 3.3.0 一样顺利；
- 8 项功能用例在 HMDFS 上的实际表现。

## 真机预检 Round 1（2026-08-25，failed@compile）→ [shell_getcwd] + E002 修复
现象（真机日志）：
1. `configure.sh: error: working directory cannot be determined`——configure.sh
   （autoconf 2.69）第 1211 行 AC_INIT 目录检查 `ac_pwd=`pwd`` 失败；伴随成串的
   bash `shell-init:` / `job-working-directory:` / `pwd: error retrieving
   current directory` 报错（errno 混乱：ENOTSUP/EINVAL/EFAULT 等）。
2. `preflight.sh[229]: can't create temporary file /tmp/shfoo0wi.tmp: Read-only
   file system`——E002（/tmp erofs 只读），与 addchain/air-quality-sensor 首轮
   日志同款噪声。
根因（HMBS 平台诊断 [shell_getcwd] 同源）：HMDFS 上 getcwd() 的 ".." 向上
遍历失败（向前路径解析正常），而 profile buildenv 的 SHELL/CONFIG_SHELL 指向
HNP bash，其启动即调 getcwd 并失败；autoconf 该探测硬依赖 `pwd` 输出，空值直接
as_fn_error。TMPDIR 注入救不了 getcwd（air-quality-sensor Round 7→8 已证）。
修复（nspr/4.37 + air-quality-sensor/0.1.5 合入先例，三件套）：
1. `_patch_configure_workdir()`：程序化改写生成文件 configure.sh（不打源码补丁，
   E114 同范式）——`ac_pwd=`pwd` && test -n "$ac_pwd" &&` → ``ac_pwd=`pwd`
   2>/dev/null || ac_pwd="$PWD"`` + `test -n "$ac_pwd" &&`；对 tarball 实测恰
   命中 1 处，改写后 `sh -n` 语法通过，ls -di 对比块保持原语义。
2. build() OHOS 下 `os.environ["PWD"]=self.build_folder`（bash/mksh 的 pwd
   信任有效 $PWD、不再调 getcwd）+ `os.chdir(self.build_folder)`。
3. E002 加固：新增 `_writable_tmpdir()`（HMBS_TMPDIR→TMPDIR→TMP→TEMP→
   ~/tmp 回退），generate() 写入工具链环境、build() 写入进程环境；
   _fix_config_status_mktemp 的固定目录随之落到可写区（原先默认 /tmp 会在
   makedirs 时静默 return，使 E114 修复失效）。
本地静态验证：py_compile 双 conanfile 通过；tarball 原件补丁模拟命中 1 处、
`sh -n` 通过、正常路径与 pwd 失败回退路径行为均验证（.hmbs/patch_sim）。
test_package 无需改动（已按 [shell_getcwd] 用 CONFIG_SHELL/SHELL→/bin/sh +
TMPDIR 设计）。

## 真机预检 Round 2（2026-08-25，failed@compile）→ FALLOC_FL_ZERO_RANGE 可见性修复

现象（真机日志）：syscall.c:348 `error: use of undeclared identifier
'FALLOC_FL_ZERO_RANGE'`（全文件仅 1 error），`make` 在 syscall.o 处 Error 2。
同文件 line 341 的 `FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE` 编译通过，
说明平台 libc 头里这两个宏可见、唯独 ZERO_RANGE 不可见。

根因（对照 tarball 原件，sha256 与 conandata 一致）：
1. configure.sh:7785-7802 用 `#include <linux/falloc.h>` 探测
   FALLOC_FL_PUNCH_HOLE / ZERO_RANGE；探测通过 ⇒ 设备上 linux/falloc.h 存在
   且含两个宏 ⇒ config.h 同时定义 HAVE_FALLOC_FL_PUNCH_HOLE /
   HAVE_FALLOC_FL_ZERO_RANGE（否则 #347 的 # ifdef 根本不会进入）。
2. rsync 上游本会在 rsync.h 里 `#ifdef HAVE_LINUX_FALLOC_H #include
   <linux/falloc.h>`（config.h.in:243 也保留模板），但 **rsync-bpc 把整个块
   包进 `#if 0 ... #else`**（rsync.h:715-730，BackupPC 有意关闭 fallocate
   预分配路径，改用 posix_fallocate 分支），于是 syscall.c 编译时拿不到
   linux/falloc.h 的宏。
3. OHOS musl 的 fcntl.h 提供 KEEP_SIZE/PUNCH_HOLE 却无 ZERO_RANGE（musl 旧版
   行为，ZERO_RANGE 后加），⇒ 只有 line 348 报 undeclared identifier。
   即：configure 探测口径（linux/falloc.h）与源码编译可见性（fcntl.h）不一致。

修复（patches/0003-syscall-falloc-macros.patch，最小侵入）：
1. syscall.c 在 sys/syscall.h 条件包含块后新增
   `#ifdef HAVE_LINUX_FALLOC_H #include <linux/falloc.h> #endif`
   ——与上游 rsync >= 3.2 syscall.c 同款做法；宏恢复可见后原代码语义不变。
2. 双保险：do_punch_hole 两处使用点由 `# ifdef HAVE_FALLOC_FL_X` 改为
   `# if defined(HAVE_FALLOC_FL_X) && defined(FALLOC_FL_X)`；若极端环境头缺失/
   宏仍不可见，编译走源码已有的写零回退路径（memset+write 循环），不再硬失败。
   运行期 fallocate(ZERO_RANGE) 若被 HMDFS 拒绝（如 ENOTSUP）也自然落到同一回退。
3. 不动 rsync.h 的 `#if 0`：尊重 BackupPC 关闭预分配的原始意图，
   SUPPORT_PREALLOCATION 维持未定义，do_fallocate 块不参与编译。

本地静态验证（非真机结论）：补丁基于 sha256 校验过的 tarball 原件生成
（difflib 统一 diff、hunk 升序、纯 LF 无 BOM）；git apply --check/-p1 干净通过，
应用结果与预期逐字节一致（Windows 下 git apply 写 CRLF 属本地现象，归一化后比对）；
conandata.yml PyYAML 解析 3 个 patch 条目正常。conan 应用路径沿用 0001/0002
已验证可行的 conandata patches 机制（Round 2 已实证能走到编译阶段）。

test_package / MANIFEST / 上游 no_tests 审计不受本轮影响，无需改动。

## 真机预检 Round 3（2026-08-25，failed@compile）→ lib/sysacls.c 缺 SUPPORT_ACLS 守卫

现象（真机日志）：lib/sysacls.c:2761 `#error No ACL functions defined for this
platform!`（全文件唯一 error），make 在 lib/sysacls.o 处 Error 2。此前
compat.o/hlink.o/hashtable.o 等大量对象已编译通过——Round 2 的 fallocate 修复
有效且构建已推进到更晚的对象；本轮是新的、独立的失败点。

为何上一方案无效：Round 2 只处理 syscall.c 的 FALLOC_FL_* 可见性，与 ACL 检测
完全正交；真机日志证明其生效（syscall.o 已过）。上一策略周期随后两轮因
provider 故障（HTTP 503 / stream 读取失败）中断，仅在工作树遗留了一个未注册
进 conandata.yml 的草稿补丁 0004；本轮不沿用其结论，而是从源码独立重推根因，
再校验该草稿与推导一致后予以采纳并补齐注册。

根因（对照 sha256 一致的 tarball 原件）：
1. Makefile.in:35-36 把 lib/sysacls.o、lib/sysxattrs.o 无条件列入 LIBOBJ——
   无论 configure 是否启用 ACL 都要编译 sysacls.c。
2. configure.sh:8738-8955（ACL 检测）：host_os 不匹配任何已知平台分支时走
   `*)` 默认分支做 POSIX ACL 探测（-lacl + <sys/acl.h> 链接测试）；OHOS 无
   sys/acl.h/libacl ⇒ samba_cv_HAVE_POSIX_ACLS=no ⇒ "No ACL support found"，
   SUPPORT_ACLS 与全部平台宏都不写入 config.h。
3. lib/sysacls.c 是 3.1.x 时代的 Samba 代码，文件体直接是平台分支链：
   #if HAVE_POSIX_ACLS / elif TRU64 / SUNOS / HPUX / IRIX / AIX / OSX /
   #else #error（line 2761）/ #endif——没有任何整体守卫。宏全空 ⇒ 必然撞
   #error。对照上游：rsync >= 3.2 已把整个文件包进 #ifdef SUPPORT_ACLS...
   #endif /* SUPPORT_ACLS */（本地 rsync-3.3.0 tarball 实测 line 27 与末行），
   本包正是缺了这一步。
4. 其余同型文件安全：acls.c 全文在 #ifdef SUPPORT_ACLS 内（line 25/1082）、
   xattrs.c 同理、lib/sysxattrs.c 有 #ifdef SUPPORT_XATTRS 守卫
   （line 25/300）；真机构建顺序（OBJS1→OBJS2→LIBOBJ，-j1 串行）证明 acls.o/
   xattrs.o 已编译通过。sys_acl_*/SMB_ACL_*/no_acl_syscall_error/SAFE_FREE
   在 lib/sysacls.* 之外全树零引用（grep 证据），故守卫生效时本文件为空翻译
   单元不影响链接。

修复（patches/0004-sysacls-support-guard.patch，照搬上游 rsync >= 3.2 范式）：
1. 文件头 include 之后插入 #ifdef SUPPORT_ACLS，文件尾追加
   #endif /* SUPPORT_ACLS */；不改任何函数体、不动 configure 流程
   （保持 auto-detect 语义：若未来 OHOS libc 提供 POSIX ACL，探测通过即自动
   启用，功能不减）。
2. conandata.yml 注册第 4 个 patch 条目（此前草稿未注册，preflight 仅导出
   3 个 .patch 即为佐证）。

本地静态验证（非真机结论）：
- 补丁 LF 纯净无 BOM；git apply --check/-p1 对 tarball 原件干净通过；
  应用结果与手工构造的期望内容逐字节一致（LF 归一化后），真实 #error 指令
  位于条件嵌套深度 2（SUPPORT_ACLS + 平台链）之内，#if/#endif 配平；
  conandata.yml PyYAML 解析出 4 个 patch 条目。
- 守卫位置与上游 3.3.0 完全同构（include 之后、DEBUG define 之前）。

---
## 真机预检 Round 4（2026-08-25，failed@compile）→ VPATH 构建缺 backuppc/ 对象子目录

现象（真机日志）：clang `-c .../backuppc/bpc_attrib.c -o backuppc/bpc_attrib.o`
报 `error: unable to open output file 'backuppc/bpc_attrib.o': 'No such file
or directory'`，make 在 Makefile:65（.c.o 规则）处 Error 1。此前 bpc_sysCalls.o
及全部根目录对象编译通过——Round 3 的 sysacls SUPPORT_ACLS 守卫有效，构建已推进
到 BPCOBJ 阶段；本轮是又一个独立的新失败点。

为何前两轮方案无效说明：Round 2（fallocate 宏可见性）与 Round 3（sysacls 守卫）
针对的是完全不同的错误域，且真机日志均证明其生效（分别越过了 syscall.o 与
lib/sysacls.o）；本次错误指纹（输出文件打不开）与二者无重叠，不存在沿用。

根因（对照 tarball 原件）：
1. conan Autotools 为 VPATH 构建：make 在 <src>/build-release 下执行，
   .c.o 规则（Makefile.in:63-65）以相对路径 -o 输出、无任何 mkdir 步骤；
2. 上游靠 AC_CONFIG_FILES 的 dummy 文件顺带创建对象子目录：
   configure.ac:1120 = `AC_CONFIG_FILES([Makefile lib/dummy zlib/dummy
   popt/dummy shconfig])` ⇒ config.status 只会创建 lib/、zlib/、popt/
   （这正是 lib/*.o 一直能编译的原因）；
3. BackupPC 新增的 backuppc/ 子目录不在该清单里（Makefile.in:185 的
   distclean 却引用了 backuppc/dummy，佐证设计意图），BPCOBJ 的 9 个对象
   全在 backuppc/ 下 ⇒ 源内构建时目录天然存在掩盖问题，VPATH 下必然失败。
   属上游 bug（vanilla rsync 无 backuppc/ 目录）。

修复（conanfile.py 程序化修复，E114 同范式，不打源码补丁）：
新增 _ensure_object_dirs()，在 config.status 生成 Makefile 之后、make 之前
调用：扫描生成的 Makefile 中全部含目录前缀的 *.o 目标（正则要求 .o 结尾词
边界，rounding.out 等不误报），在构建目录逐一幂等创建对应子目录；对
backuppc/ 保底（Makefile 缺失时也补）。lib/zlib/popt 已由 dummy 创建时为
幂等跳过。保留 auto-detect 与上游构建语义不变。

本地静态验证（非真机结论）：py_compile 通过；pristine Makefile.in 扫描恰好
得到 {backuppc(9), lib(22), popt(5), zlib(9)} 四个目录、无误报；从更新后的
conanfile.py 原样提取方法体执行三组用例——合成 Makefile（含 ./dir/x.o 归一化
与 rounding.out 反例）、无 Makefile 回退、pristine Makefile.in 整文——目录
集合全部符合预期且二次运行幂等；build() 调用顺序 getpass → objdirs → make
确认无误。

---
**状态**: 工作树完成（Round 4 修复：vpath_objdirs 对象子目录），等待 hmbs 真机预检（本轮不 commit/push）
---
## 真机预检 Round 6（2026-08-27，failed@test_package）→ options.c(1882) 强制门 → standalone POSIX 透传

现象（真机日志）：configure/compile/install/ELF 全部成功进入 test_package；
8 用例只有用例 1（--version 输出 3.1.3.0）通过，其余 7 个真实传输用例统一
`rsync error: syntax or usage error (code 1) at /storage/.../options.c(1882)
[client=3.1.3.0]` rc=1——包括最简形态 `rsync_bpc -r src/ dst/`。

为何前几轮方案与本问题无关：Round 1-4 解决的是 configure 工作目录 /
fallocate 宏可见性 / sysacls 守卫 / VPATH 对象子目录四个互不重叠的编译期
错误域，本轮真机日志证明构建已整体通过；usage error 是新的独立失败域
（前两轮针对同一指纹的重试并未修改任何代码，working tree 与 Round 4 完成
态一致——git status 仅 archives/b/backuppc-rsync/ 整目录 untracked）。

根因（对照 sha256 一致 tarball 原件，.hmbs/src/tree 本地解包取证）：
1. options.c:1880-1883 是 BackupPC 特有的致命门：
   `if (!bpc_top_dir || !bpc_host_name || !bpc_share_name || bpc_backup_num<0)
   { snprintf(...); exit_cleanup(RERR_SYNTAX); }`——退出码/源码行号/版本串
   与真机输出逐字吻合（err_buf 设了但没走 option_error 打印，故只见通用
   报错，与日志无 "BackupPC options are compulsory" 字样一致）。
2. rsync-bpc 编译期无条件把全部文件系统访问接到 BackupPC 池 VFS 模拟层：
   syscall.c 的 do_unlink/do_open/do_stat/do_mkdir/do_mkstemp/... 一律转调
   bpc_* 包装（SUPPORT_BPC 直链，无条件编译开关）；bpc_stat/bpc_lstat/
   bpc_opendir/bpc_readdir 仅查 attrib cache（内存覆盖 + $topDir/pc 下
   attrib 文件），bpc_open 写入经 poolWrite 进 cpool；grep 全树确认不存在
   任何"真实文件系统透传"分支（attrib 层亦无 real-path fallback）。
   结论：该二进制按上游设计只在携带完整 BackupPC 参数、作为 BackupPC
   backup/restore 服务端引擎运行；独立本地传输属于被设计禁止的场景
   （err_buf 文案明说 "compulsory"），test_package 的用例前提即不成立。
3. 排除"补上 4 个 --bpc-* 参数即可"路线：那样会把测试从真实磁盘语义切换
   成池语义（写入落 cpool/attrib 而非 dst/），需要构造 cpool/attrib fixture
   并解码专有格式才能断言，且子进程仍拿不到这些参数（server_options 不
   转发 bpc 选项），父(VFS)/子(real-fs)混合反而制造新不一致。

修复方案（patches/0005-bpc-standalone-passthrough.patch，portability 补丁，
不影响任何现网可用流程）：上游缺参即死 = 不存在可被破坏的工作流，因此把
"缺参"从未定义错误态升格为显式 standalone POSIX 模式：
1. bpc_sysCalls.c 新增 `static int BPC_Standalone`；bpc_sysCall_init() 在
   topDir/hostName/shareNameUM 为空或 newBkupNum<0 时置位并跳过全部池
   初始化（attribCache/refDelta/conf init 都不再触碰）；cleanup/am_generator
   同步短路，Stats/Delta 结构保持零值不外写。
2. 全部数据面包装在标志下直转 POSIX 调用：open/close/read/write/lseek/
   ftruncate/stat/lstat/fstat/unlink/rmdir/mkdir/rename/symlink/readlink/
   link/lchown/lchmod(#ifdef HAVE_LCHMOD 内引符号,否则 ENOSYS)/fchmod/
   lutimes(#ifdef HAVE_LUTIMES)/utimes(#ifdef HAVE_UTIMES)/lutime/utime
   (utimbuf)/mknod/access/chdir/opendir/readdir/closedir/mktemp(试名不创建,
   保持 O_EXCL 后续 open 语义)/mkstemp(libc mkstemp,0600 与 VFS 缺省一致);
   所有委托符号均已被原翻译单元或同配置探测引用过，未新引入平台链接风险。
3. 池专用查询给中性失败值让 vanilla 路径接管：bpc_file_checksum 返回 -1 →
   checksum.c file_checksum() 落到自带 do_open+map+md5 慢路径（正是原生
   rsync 行为，无需复刻 MD5）；checkFileMatch/poolFileCheck 返回 -1 表示
   "无池匹配"；nlinkSet 恒 0、tmpNameFlagSet no-op、rename_request 防御性
   转真 rename（standalone 双端不会发 MSG_RENAME，仅防混合误用崩溃）。
4. options.c 移除致命门，原位留注释指向本补丁机制。

边界声明（记入 notes，不扩测试口径）：
- 带 --bpc-* 的既有使用方式（BackupPC 服务端角色）行为逐字节不变；
- 混合调用（部分提供 bpc 参数）此前必死，现为未定义支持面，文档标注不建议；
- xattr 五个包装未加透传守卫（tests 未用 -X；若未来 configure 启用
  SUPPORT_XATTRS 再评估），hard-link 计数辅助函数保持原样（-H 由原生
  rsync hlink 路径处理，bpc 增强 stub 留待 BackupPC 场景）。

本地静态验证（Windows 侧，非真机结论）：
- 生成器脚本 .hmbs/build_patch.py 基于 tarball 原件逐锚点插入；38+2 处守卫
  锚点均要求全文唯一命中；difflib unified diff n=4；
- 补丁 512 行 / 14944 字节，CR 计数 0（纯 LF 无 BOM），41 个 hunk；
- git apply --check / git apply -p1 对 pristine 两文件干净应用；
- 应用后括号配平 307→317（各 +9 对守卫块,options 门替换括号中立）、
  'BPC_Standalone' 出现 41 次、守卫行 39 条；关键函数（init/cleanup/
  mktemp/mkstemp/open/close/read/write/opendir/readdir/file_checksum/
  checkFileMatch/poolFileCheck/lchmod/lutimes/utime 族）逐一目检，hunk 无
  窜位。
- test_package 保持 8 用例不动：discovered 口径不变，用例本来就是普通本地
  同步语义，透传生效后即为合法被测行为。

**状态**: 工作树完成（Round 6 修复：standalone passthrough），等待 hmbs 真
机预检（本轮不 commit/push）

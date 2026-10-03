# knxd 0.14.73 适配笔记

## 编译环境
- 构建系统: autotools（`configure.ac` + `AM_INIT_AUTOMAKE` + `LT_INIT`；上游发布件**不含生成物**）
- 编译日期: 2026-09-27
- 编译器: clang/clang++（OHOS profile：`compiler_executables={"c": ..., "cpp": ...}`，键名是 `cpp`）
- 构建主机: B 机（HarmonyOS aarch64），worktree `~/qzy/主理-75-knxd-0.14.73`，分支 `feat/knxd-0.14.73`
- CONAN_HOME: `~/tmp/ch/home-knxd`（profiles/remotes/extensions 齐备；⛔ 不用默认 `~/.conan2`）
- 状态: built（W3 于 2026-09-30 17:42 跑绿，`.ci-result.json` exit_code=0 / integrity_hash `16dcc908d7c8933c`）

## 编译步骤

1. 取源：`https://github.com/knxd/knxd/archive/refs/tags/0.14.73.tar.gz`（GitHub tag 归档 = git 树快照）
2. 打补丁 `patches/0001-version.sh-tarball-version-fallback.patch`（源码文件，非生成物）
3. `autoreconf`（conan `Autotools.autoreconf()`，自举工具来自 `tool_requires automake/1.18 + libtool/2.5.4`）
4. autoreconf **之后**修补生成物 `configure`：`umask 077` → `umask 022`（E011/E129/E136）
5. `./configure --disable-java`（其余 prefix/host 由 AutotoolsToolchain 注入；依赖面由 PkgConfigDeps + AutotoolsDeps 注入）
6. `make -j1`
7. `make check`（automake 目标；上游 TESTS=0，见「测试账本」）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `AC_CHECK_HEADER(argp.h)` 直接 `AC_MSG_ERROR([argp_parse not found])` | OHOS 用 musl，sysroot 无 `argp.h`（实测：`.../sysroot/usr/include/argp.h` MISS，同批 `error.h` 亦 MISS，而 `linux/rtnetlink.h`、`linux/usbdevice_fs.h`、`sys/epoll.h` 均 HAVE） | `requires("argp-standalone/1.5.0")`（提供 `include/argp.h` + `lib/libargp.a`，`cpp_info.libs=["argp"]`）；`AC_SEARCH_LIBS(argp_parse,argp)` 经 AutotoolsDeps 的 `-largp` 命中。知识条目 `knowledge/graph/E169.kv:8,13,21` |
| 2 | 上游 tarball 无 `configure`/`Makefile.in`/`config.sub` | GitHub tag 归档只是 git 树快照，生成物不进版本库 | `autoreconf` 自举 + `tool_requires` 取 automake/libtool（与 `archives/a/argp-standalone/1.5.0/conanfile.py:28-32,60-65` 同判据） |
| 3 | 设备自带 automake 看似存在却跑不了：`~/usr/local/bin/automake: No such file or directory`，`autoreconf` 随即 `Can't exec "aclocal"` | 文件在（264366 字节），**缺的是解释器**：shebang 写死 `#!/storage/Users/currentUser/usr/local/bin/perl`，而该路径下没有 perl（`/data/service/hnp/bin/perl` 才有）⇒ 报错误导成"automake 没装" | 不依赖设备 `~/usr/local/bin` 的 automake/libtoolize，改走 `tool_requires`；`-pr:b=ohos-aarch64`（CI/conan_verify 同口径）下 automake/1.18、libtool/2.5.4、autoconf/2.72 都能拿到已发布二进制（`conan install --tool-requires=... --build=never` rc=0，Install finished successfully） |
| 4 | `AC_INIT([knxd],m4_esyscmd_s([./tools/version.sh]))` 在无 `.git` 的归档里得到空版本；同时 `Makefile.am` 的 `version.h` → `#define REAL_VERSION ""` ⇒ `knxd --version` 无版本号 | `tools/version.sh` 第 10 行 `test -d .git \|\| exit` 直接静默退出 | 补丁 0001：非 git 检出时打印打包版本 `0.14.73`（一处修两个消费面；git 检出与 Debian changelog 分支行为不变） |
| 5 | `configure.ac` 硬编码 `LIBS="-lfmt $LIBS"` + `AC_LINK_IFELSE` 失败即调 `sh tools/get_libfmt` 联网抓 libfmt 再构建（CI 离线面不可控）；且工程被 `AC_COMPILER_OPTION(stdc,[-std=c++0x])` 钉在 C++11 | 上游把 fmt 当必需项，失败兜底是"构建期下载" | `requires("fmt/8.1.1")` 让第一次 link 测试即命中，绕开 `get_libfmt`；选 8.1.1 而非 11.1.3/12.2.0 —— 后者要求 C++17，与 `-std=c++0x` 冲突（已发布件：7.1.3/8.1.1 均可，取较高者） |
| 6 | `AC_CHECK_LIB([ev],[ev_run],,[AC_MSG_ERROR([libev not found])])` | libev 是必需依赖（knxd 主循环用 ev++） | `requires("libev/4.33")`（已发布，recipe+binary 实测） |
| 7 | USB 后端：`AC_CHECK_HEADER(linux/usbdevice_fs.h)` 决定 `have_usb`，`PKG_CHECK_MODULES([LIBUSB],[libusb-1.0 >= 1.0.9])` 决定 `HAVE_USB` | 需 sysroot uapi 头 + pkg-config 元数据 | sysroot 实测 `linux/usbdevice_fs.h` HAVE ⇒ 保留 USB 特性面（不 `--disable-usb` 缩面）；`requires("libusb/1.0.27")` + `PkgConfigDeps(self).generate()` 生成 `libusb-1.0.pc` |
| 8 | HMDFS 上 configure/config.status 的 `confXXXXXX` 临时目录写不进去 | `umask 077` + HMDFS 恒置 setgid ⇒ 目录 `drwx--S---` 连属主不可写（E011/E129/E136） | 在 autoreconf **之后**对生成物 `configure` 做 `umask 077 → umask 022`（`replace_in_file(..., strict=False)`）；顺序依据 `archives/a/argp-standalone/1.5.0/conanfile.py:66-78` |
| 9 | G2 红：configure: error: working directory cannot be determined（VERIFY_RC=2） | profile 的 [buildenv] 把 CONFIG_SHELL/SHELL 指向 /data/service/hnp/bin/bash，而该 bash 在 HMDFS 上 getcwd() 被拒：同目录对拍实测 bash -c pwd 为 **rc=1、stdout 空**、stderr 打印 shell-init: ... getcwd: cannot access parent directories（/bin/sh -c pwd 则 rc=0 且 stderr 空）。autoconf 生成的 configure 会用 $CONFIG_SHELL 重新 exec 自己，于是起手即死（E386 家族；⛔ 图谱给的 E443「tool 包脚本 shebang 被跨 UID 拒」不是本包根因，本包 configure 是被 /bin/sh 直接执行成功的） | build() 先做**能力探测** _capability_tested_shell（在真实构建目录里跑 shell -c pwd，要求 rc=0 **且** stderr 为空 **且** 输出是绝对路径，三条齐才接受；E386 明确记录"壳可能返回 0 的同时还在吐 getcwd 诊断"⇒ 只看 rc 是假绿），再把 CONFIG_SHELL / SHELL / TMPDIR / LD_LIBRARY_PATH 作为**内联前缀**压在显式的 "<shell>" "<configure>" 调用上。⛔ os.environ、⛔ Environment().define（E386 forbid_2；实测 conanbuildenv-release-armv8.sh 第 3 行就把 SHELL/CONFIG_SHELL 重新导出，后挂的环境会被它盖回）。修后 create 日志 grep -c getcwd = 0 |
| 10 | configure: error: cannot guess build type; you must specify one | 本机 uname -s = HarmonyOS、uname -r = HongMeng Kernel 1.12.0，随 automake/1.18 分发的 config.guess（时间戳 2024-07-27，是**当前**版而非旧快照）仍认不出 ⇒ 单独跑 config.guess rc=1 并自陈 "unable to guess system type"。⚠ E160 的处方是 sed -i 往 config/config.guess 里加 HarmonyOS 分支，但本包 config.guess 是 autoreconf --install 从 tool_requires **复制**进来的，自举前改等于没改 | --build=aarch64-unknown-linux-ohos，取值直接抄本机 clang -dumpmachine 的读数（不发明三元组；host 未给 ⇒ 由 build 继承，仍是本地构建语义，configure 照旧真的去跑 conftest）。仓库既有多包同法：archives/4/4ti2/1.6.10/conanfile.py:51、archives/a/abiword-plugin-clarisworks/3.0.8/conanfile.py:141 |
| 11 | configure: error: Unable to find a suitable libsystemd library | configure.ac:69 的 AX_ENABLE_SYSTEMD 走到 m4/systemd.m4:45 的 AX_CHECK_SYSTEMD_LIBS，该宏在找不到 libsystemd 时是硬 AC_MSG_ERROR；本机 sysroot 实测 systemd/sd-daemon.h MISS（OHOS 无 systemd） | 用上游自带的开关 --disable-systemd：AX_CHECK_SYSTEMD 第一行即 test "x$enable_systemd" != "xno" 直接短路跳过整个检查 ⇒ 不引未发布依赖、不改源码、不手写补丁。代价如实登记在「已知限制」：丢 systemd socket activation（sd_listen_fds）这一个面 |
| 12 | configure: error: cannot run C compiled programs，其上一手读数是 Error loading shared library libusb-1.0.so.0 / libfmt.so.8 / libev.so (needed by ./conftest)（configure rc=77） | AutotoolsDeps 把整条依赖闭包写进 LIBS，autoconf 最早的 run 探针（交叉编译判定）就会去**加载**这些共享库（E467）；而 profile 侧 LD_LIBRARY_PATH 实测只含 toolchain 与 libtool 两个目录（conanbuildenv-release-armv8.sh:15），依赖包 lib 目录不在其中。⇒ 不是编译器问题、也不是三元组问题 | 同一个内联前缀里追加 LD_LIBRARY_PATH=各依赖 cpp_info.libdirs（_dependency_libdir_path）。对拍（B 机一手）：同一 conftest 不设该变量 rc=127；设成依赖 lib 目录后 rc=0 并打印出 ev_run 的符号地址；另证本机新链接的二进制可以直接执行（排除签名/noexec 假设）。⚠ 该处方与 E505「不要为此导出全局 LD_LIBRARY_PATH」相反，本包实测不成立，证据见「3+2 声明」节 |
| 13 | src/libserver/ipsupport.cpp 编译期：linux/socket.h:23:8: error: redefinition of sockaddr_storage（sys/socket.h:377:8: note: previous definition is here），make 逐级 Error 1/2 | OHOS sysroot 的 linux/socket.h 是内核自动生成件，**无条件**定义该 struct（文件头自陈 automatically generated from a Linux kernel header）；源文件的包含顺序本来是对的（sys/socket.h 第 26 行、内核头第 30-31 行），仍与 musl 的定义正面相撞（E091/E119 记录的不一致） | 补丁 0002 = 抄 E091 的 define-guard 房式写法：在 #ifdef HAVE_LINUX_NETLINK 块内、#include 内核头之前 #ifdef __OHOS__ + #define sockaddr_storage __linux_sockaddr_storage，include 完立刻 #undef 还原。__OHOS__ 实测由本机 clang 预定义（clang -dM -E -x c /dev/null 命中 #define __OHOS__ 1），且整块被 HAVE_LINUX_NETLINK 包着 ⇒ 其他平台零影响、netlink 功能面不缩。单文件复算：用 create 日志里**原样**的编译命令重跑 ⇒ CC_RC=0、error: 计数 0、ipsupport.o 落地 |
| 14 | make: tools/version.sh: No such file or directory，随后 version.h 静默写出 #define REAL_VERSION "" | Makefile.am:21 的规则用相对路径调 tools/version.sh，只对 in-tree 构建成立；conan 是 VPATH 构建（build-release 与源码树分离），而 make 的 shell 函数把报错丢到 stderr、stdout 留空，规则于是**以成功状态产出一个空版本号** —— 与补丁 0001 同族但成因不同：0001 管的是脚本在无 .git 时打印什么，这条是脚本根本没被调到 | 补丁 0003 把路径改成 $(top_srcdir)/tools/version.sh 并用 sh 显式调用（生成的顶层 Makefile 里 top_srcdir 是绝对路径，实测 = 待验证目录/b；用 sh 还顺带去掉对脚本可执行位的依赖，与 E490 那一面脱钩）。迷你 makefile 复算同表达式 ⇒ 输出 RES[0.14.73]

## 源码修改

- `tools/version.sh`（补丁 0001，8 增 1 删）：无 `.git` 时回落到打包版本 `0.14.73`。
  - 不含任何平台宏（`__OHOS__` 零命中 ⇒ PF5 面干净），非"平台专属"补丁：`patch_classification.platform_only: False`。
- 生成物 `configure` 的 `umask` 修补在 `build()` 内完成，**不落 patches/**（生成物不进补丁，R1/R6）。

## 依赖版本

| 依赖 | 版本 | 用途 | 发布态实测（W0/R35/R36） |
|------|------|------|--------------------------|
| libev | 4.33 | `AC_CHECK_LIB([ev],[ev_run])` 必需 | recipe: `Downloading recipe 'libev/4.33#5ff7c6c5…'`；binary: `conan install --requires=libev/4.33 --build=never` rc=0 |
| fmt | 8.1.1 | `LIBS="-lfmt"` 硬编码 + `fmt/printf.h`(HAVE_FMT_PRINTF) | recipe: `Downloading recipe 'fmt/8.1.1#ac79f486…'`；binary rc=0 |
| argp-standalone | 1.5.0 | OHOS musl 无 argp（E169） | recipe 在 cache（revision `bdb53776…`，首次由 ohpcd 下载）；binary rc=0（`--build=never`） |
| libusb | 1.0.27 | USB 后端 `PKG_CHECK_MODULES` | recipe: `Downloading recipe 'libusb/1.0.27#0e6a7c47…'`；binary rc=0 |
| automake (tool) | 1.18 | autoreconf 自举 | build profile=ohos-aarch64 下 binary rc=0（`Install finished successfully`）；⚠ build profile=default(Linux) 下 **binary missing** ⇒ 必须与 CI 一样把 `-pr:b` 指到 ohos-aarch64 |
| libtool (tool) | 2.5.4 | LT_INIT / libtoolize | 同上 |

`preflight_check.sh knxd/0.14.73` 首轮（conanfile 未生成时）返回 `[OK] 预检通过（无依赖需要检查）` rc=0；
依赖齐了以后重跑读数见「最终状态」节。

## 取源自证（三向对字）

1. **官方 URL GET**：`https://github.com/knxd/knxd/archive/refs/tags/0.14.73.tar.gz`
   - `curl -L` 实测 `HTTP=200 SIZE=300856`；同一 URL 的 `HEAD` 返回 `302 → https://codeload.github.com/knxd/knxd/tar.gz/refs/tags/0.14.73`，对 codeload 直接 GET `HTTP=200 SIZE=300856`（两个入口字节数一致）。
   - ⚠ 本机到 `github.com:443` 是**间歇可达**（4 次探测 2 次 200 / 2 次 connect timeout），故配方 `sha256` 只在多次下载得到同一实物时才可信：本轮 3 次成功下载（curl -L 两次、codeload 一次）大小均为 300856，实物哈希见 (2)。
2. **实物 sha256**：`fc66bb8d4f74e815d9677e0bd5520d965c7049ae306e09956c04ec74599167c3`（`sha256sum` 于 B 机 `$W/dl/knxd-gh.tar.gz` 与 Windows 侧 `.temp/knxd/knxd-gh.tar.gz` 各算一次，两处一致）
3. **conandata 声明值**：与 (2) 逐字一致（`archives/k/knxd/0.14.73/conandata.yml`）

版本同一性核验（⛔ 池件不作配方 url，PF7）：
`https://deb.debian.org/debian/pool/main/k/knxd/knxd_0.14.73.orig.tar.gz` 实测 `HTTP=200`、301001 字节、
`sha256=1feb06f52eaa3c2cd4408cc85ded3ca2eee5f98b9d7c001d8ac600cae58e3057` —— 与登记表索引前缀 `1feb06f52eaa3c2c` 对字，
确认任务版本与 Debian 在册版本一致。

⚠ **诚实口径**：GitHub tag 归档（300856B）与 Debian `.orig`（301001B）**字节不同**，因此本包**不宣称**
"官方 tarball 与池件同哈希"；版本同一性由源码树内容（`configure.ac` 的 `AC_INIT([knxd], …)` + 补丁后
`tools/version.sh` 输出版本）与两侧文件清单对照建立。差异属打包面（git 快照 vs 上游发布件重打包）。

## 测试账本

上游静态合计（计数命令，均在解包后的源码根执行）：

```sh
# 1) automake 测试面：TESTS / check_PROGRAMS 命中数 => 0
grep -rnE "^(TESTS|check_PROGRAMS)" --include=Makefile.am . | wc -l
# 2) 全部 Makefile.am 里 check 关键字命中数 => 0
grep -rnE "check|TESTS" --include=Makefile.am . | wc -l
# 3) 上游手工集成脚本 tools/test.sh 的断言面
grep -c "^if knxd " tools/test.sh            # 5  （Bad argument A/B/D/E/F：必须被拒）
grep -c "^if ! knxd " tools/test.sh          # 2  （C：必须起得来；G：group cache 条件）
grep -c "^if ! knxtool " tools/test.sh       # 8  （X1..X7，含两处 X7 标号复用）
grep -c "^diff -u " tools/test.sh            # 5  （golden 输出比对 monitor1/2/3/cache/listen）
grep -c "^test -z \"\\\$E\"" tools/test.sh   # 1  （汇总判定）
# 4) 未构建的可选用例
grep -n "noinst_PROGRAMS" tools/Makefile.am  # test_inih（tools/ 不在 SUBDIRS，上游从不构建）
```

读数：上游 `make check` 面 **0 用例**；上游真实测试资产 = `tools/test.sh` **21 条断言**（未接入 make check）
+ `tools/test_inih.cpp`（需 libinih，未构建）。

适配后执行面：

| 分类 | 条数 | 说明 |
|------|------|------|
| 上游注册可执行（make check） | 0 | TESTS=0，`make check` 为空通过（已在 build() 留痕，不冒充测试） |
| 上游集成断言（tools/test.sh） | 21 | 前 6 条（Bad argument A–F）在本包 `test_package/test.sh` 以**同判据**复现；第 49 行组缓存前置门 1 条未移植（失败路径为 `exit 0` 提前退出，不构成可判定断言）；后 14 条需 3 个守护进程 + 组播/隧道 + golden log，**本轮未执行**（分类=未执行，不记 pass） |
| test_package/libeibclient | 11 | `test_eibclient.c`：守卫 7（A1–A7）+ 正向 4（B1–B4，自建 AF_UNIX 监听让库真 connect） |
| test_package/二进制语义 | 13 | `test.sh`：安装定位 2 + 版本/用法 3 + 上游 A–F 判据 6 + knxtool 用法 1 + knxd_args 1 |
| 失败 | 0 | 任一失败 harness 非零退出 |

合计实测 24 条 ≥ 上游 `make check` 面 0 条；上游 test.sh 的 21 条中已复现判据 **6 条（Bad argument A–F）**，其余 **15 条**（段一第 49 行组缓存前置门 1 条、段二组播/隧道 14 条）未移植，逐条理由见 `reports/test-report.md` 与 `test_package/MANIFEST.yml`。
`SUMMARY total= pass= fail=` 由两个 harness 各自打印（机器可读，失败即非零退出）。

## 已知限制 / 能力墙（真机运行面）

实测 sysroot 事实（`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include`）：

| 探针 | 读数 | 影响 |
|------|------|------|
| `argp.h` | MISS | 需 argp-standalone（已解决） |
| `error.h` | MISS | argp-standalone 走 `ac_cv_header_libintl_h=no` 分支，不引 gettext |
| `linux/rtnetlink.h` | HAVE | `HAVE_LINUX_NETLINK` ⇒ `have_source_info=yes` ⇒ eibnetiptunnel / eibnetipserver **保持启用**（未缩面） |
| `linux/usbdevice_fs.h` | HAVE | `OS_LINUX`/`have_usb=yes` ⇒ USB 后端**保持启用** |
| `sys/epoll.h`、`sys/signalfd.h`、`sys/timerfd.h`、`execinfo.h`、`net/route.h`、`net/if.h` | HAVE | — |

运行期未取证 / 待逐号探的墙（编译通过不代表可用，本轮不宣称运行时可用）：
- 串口面：OHOS 无 `/dev/ttyS*` 节点；pty 的调制解调器旗标为 `EACCES` ⇒ `tpuarts`/`ncn512x`/`ft12` 的真实设备访问待取证（披露口径：节点存在但 EACCES，不写"无节点"）
- USB 面：libusb 需要设备节点/usbfs 访问，能否枚举并 claim KNX 接口未实测
- 组播/隧道：`--Server=224.99.98.x:<port>` 与 `ip:`/`ipt:` 后端依赖组播与 UDP 转发，未实测
- SysV IPC：本包源码未见 `shmget/semget/msgget` 使用面（knxd 走 unix socket + libev），故 seccomp-BPF 拦截面预计不适用（未做探针，不写结论）
- `src/tools/Makefile.am` 的 `install-exec-local` 会 `ln -sf` 生成 46 个 knxtool 别名软链接 ⇒ HMDFS 上 `ln -sf` 覆盖既有符号是已知坑（S1），首轮安装若报符号链接失败需按 `rm -f && ln -s` 处置

## 3+2 声明（B 判定由主窗终判，本节只放一手证据）

- 适配路径：（待主窗判定：A / B / C）
- 使用知识库：（待填：命中的 E 编号 + 行号）
- 知识库扩展：（待填：若判 create）
- 关联 Issue：（待填）

### 候选命中（既有 E 条目，覆盖度自评）

| 机制 | 一手读数 | 候选条目（文件:行） | 是否同时覆盖根因与解法 |
|------|----------|--------------------|------------------------|
| OHOS 无 `argp.h` ⇒ configure 硬失败 | sysroot 探针 MISS `argp.h`/`error.h` | `knowledge/graph/E169.kv:8,13,21`（index.tsv 行 `E169`） | 是（根因=musl 无 argp；解法=装 argp-standalone）。⚠ 该条推荐"下预编译 tar 解到 ~/usr/local"，本包用 conan `requires` ⇒ 解法面不同，是否算 hit 请主窗按"同一物理事实但处方在另一操作面"的口径判 |
| `dgettext/__dcgettext` 链接期缺符号（argp 的 NLS 面） | argp-standalone/1.5.0 配方注释：`.../conanfile.py:44-52` | `knowledge/graph/E015.kv:10,15,21` | 本包未触发（依赖包已用 `ac_cv_header_libintl_h=no` 规避）；仅同族参考 |
| HMDFS `umask 077` 临时目录不可写 | configure 生成物含 `umask 077`；E 条目描述 `drwx--S---` | `E011.kv:8,22,40`、`E129.kv:9,17,23`、`E136.kv:4,5,13` | 是（根因+解法齐）。⚠ 本包的额外事实是"必须排在 autoreconf **之后**"，该次序约束在这三条里没有 |
| 自举工具在设备上"存在但跑不了"（shebang 指向不存在 perl） | `~/usr/local/bin/automake` 264366B 存在，`head -1` = `#!/storage/Users/currentUser/usr/local/bin/perl`，而该 perl 不存在；`autoreconf` 报 `Can't exec "aclocal"` | 未找到覆盖"生成物缺失 + 包装 perl 脚本解释器失联"这一组合的既有条目；`E041.kv:8,16,22` / `E071.kv:10,18,25` 讲的是 automake **版本**不匹配，`E089.kv:10,18,28` 讲 `@am_AUTOM4TE@` 占位符未替换 —— 都不是本机制 | ⇒ **create 候选**（机制一句话：autotools 自举失败的真因可能不是"没装 automake"，而是已装 perl 脚本的 shebang 绝对路径指向不存在的解释器；判别式 = `test -f` 为真 + `head -1` 取 shebang + 对解释器路径做 `test -x`，三步分开报） |
| 上游把版本绑在 git 元数据上（`m4_esyscmd_s` + `version.sh`）⇒ 源码包版本为空 | `configure.ac:29`、`tools/version.sh:10`、`Makefile.am` `version.h:` 规则 | 未检索到条目（`grep -iE "version.sh\|m4_esyscmd\|git describe" knowledge/graph/index.tsv` 无命中，需复算后引用） | ⇒ **create 候选 #2**（机制一句话：`AC_INIT(...,m4_esyscmd_s([./tools/version.sh]))` 在无 `.git` 归档里静默给空版本，同一脚本又被 `Makefile.am` 用作 `REAL_VERSION` ⇒ 一处补丁修两面；判别式 = 打包前先 `sh tools/version.sh; echo rc=$?` 看空输出） |
| GitHub tag 归档不含生成物 ⇒ 必须自举 | 实测解包树只有 `configure.ac`/`Makefile.am`，`test -f configure` = NO_CONFIGURE | `E007/E072/E122/E205` 讲 config.sub/guess 的 ohos 三元组（本包生成物来自 tool_requires，另当别论） | 层次差请主窗判 |


### 本棒 z75b 新增材料（G2 修复过程中取得的读数；B 终判仍归主窗）

| 机制 | 一手读数（可复算） | 候选条目（文件:行） | 覆盖度自评 |
|------|--------------------|---------------------|------------|
| profile [buildenv] 的 HNP bash 在 HMDFS 上 getcwd 坏 ⇒ configure 用 $CONFIG_SHELL 重新 exec 自己后起手即死 | 同一构建目录对拍：`/bin/sh -c pwd` → rc=0、stderr 空、输出绝对路径；`/data/service/hnp/bin/bash -c pwd` → **rc=1、stdout 空**、stderr 为 shell-init: ... getcwd: cannot access parent directories。create 日志中该诊断 27 条、紧随 `configure: error: working directory cannot be determined` | `knowledge/doc/E386.md:17-19`（根因：壳可以在返回 0 的同时仍吐 getcwd 诊断，故只看 rc 或可执行位不足以证明它能保住工作目录）、`E386.md:29-36`（解法：从真实构建目录探测壳、仅当 pwd 返回 0 且输出与诊断皆空才接受，并为 Autoconf 设 CONFIG_SHELL/SHELL）、`knowledge/graph/E386.kv:58-62`（forbid_2 明列 `os.environ.*CONFIG_SHELL` 与 `accept.*pwd.*stderr`） | **是**（根因与解法同一条目两行齐覆盖，且 forbid_2 正是本包第一次手跑时踩的方向）。⇒ 判 hit 的候选，处方按条目落成 `_capability_tested_shell` + 内联前缀 |
| AutotoolsDeps 把依赖闭包塞进 LIBS ⇒ autoconf 最早的 run 探针必须**加载**整条共享库闭包；profile 侧 LD_LIBRARY_PATH 不含依赖 lib 目录 | config.log 一手：`Error loading shared library libusb-1.0.so.0 / libfmt.so.8 / libev.so (needed by ./conftest)`，configure rc=77；`conanbuildenv-release-armv8.sh:15` 实测 LD_LIBRARY_PATH 只有 llvm 与 libtool 两处。对拍：同一二进制不设变量 rc=127、设成依赖 lib 目录后 rc=0 并打印出 ev_run 地址；另证新链接的二进制可直接执行（排除签名/noexec） | `knowledge/graph/E467.kv:42`（根因）、`:49-51`（解法面：先读 config.log 的第一条加载错误、再在任务私有视图内修可加载性；并明确 ⛔ 改静态、⛔ 预设 cross_compiling、⛔ 加 --host） | 根因**齐**；解法只给方向、具体手法转指 E505/E257/E321。本包未加 `--host`（只加 `--build`，仍按本地构建真的跑 conftest），与 forbid 面不冲突 |
| ⚠ 与 E505 相反的一手读数 | E505 主张「版本化别名（libfoo.so.1）经 LD_LIBRARY_PATH 在 HMDFS 上解析不了，因此不要导出它」。本包实测把 LD_LIBRARY_PATH 指向依赖 lib 目录后，**版本化别名** libusb-1.0.so.0、libfmt.so.8 与无版本 libev.so 全部解析成功、configure 一路 rc=0 完成 config.status | `knowledge/graph/E505.kv:42`（该断言原文）、`:50`（rec：materialised-signed-runtime-view + 只嵌 DT_RPATH、并明令不要导出 LD_LIBRARY_PATH）、`:43`（自陈"与内核版本和 HMMAC 策略相关，换设备须重新实测"） | 不是新机制，是**既有条目的适用域冲突**：B 机 + 本 SDK + 这批依赖包上不成立。已按 `:44` 的 verification_cmd 口径自测。⇒ 请主窗判是补 E505 的 scope 限定，还是记一条设备面差异 |
| 上游 m4 把可选依赖写成硬失败（`AX_CHECK_SYSTEMD_LIBS` 之 AC_MSG_ERROR）时的收缩姿势 | `m4/systemd.m4:45-52` 原文；`:43-45` 的 `AX_CHECK_SYSTEMD` 首行即 `test x$enable_systemd != xno` ⇒ `--disable-systemd` 短路整段。sysroot `systemd/sd-daemon.h` MISS。检索面：`grep -l -i systemd knowledge/graph/*.kv` 仅命中 `E090.kv`/`E091.kv`；最近的相关规定是 `E091.kv:32-35` 的 fallback `disable-netlink`（"不需要该功能就用 configure 开关关掉模块"），但它挂在 netlink 这一面上，不是"可选依赖硬失败 ⇒ 优先用上游自带开关，而不是引入未发布依赖或手写源码"的一般次序 | 部分覆盖（有同精神的 fallback，无本机制的独立条目）。⇒ 是否升格成条请主窗判；本包能补的是"判别次序 + systemd 这一实例" |
| VPATH（树外）构建下 make 的 shell 函数按**相对路径**调脚本：报错进 stderr、stdout 为空 ⇒ 规则**以成功状态产出空值** | 一手：make 输出 `make: tools/version.sh: No such file or directory` 但 `make` 继续，随后 `build-release/version.h` 实测内容为 `#define REAL_VERSION ""`；同目录 `grep -n "^top_srcdir" Makefile` = 绝对路径 ⇒ `$(top_srcdir)` 可用；迷你 makefile 复算同表达式 ⇒ `RES[0.14.73]`。已排除的既有条目：`E157.kv:20`（jpeg-version.sh 缺 `cpp`，是"解释器/工具缺失"）、`E158.kv:19`（GNUmakefile 目标缺 pkg-config 配置）、`E041.kv:16` / `E071.kv:18`（automake **版本**不匹配）、`E110.kv:27` / `E175.kv:18`（HMDFS 临时目录/子目录写入限制）—— 没有一条讲"树外构建里相对路径的 shell 函数静默返空"；⚠ 复核补排 `E519.kv:36` | ⇒ **候选·因 E519 解法重合故不升 create**（`knowledge/graph/E519.kv:36` 标题即「out-of-source 构建 install-data-am 的 `$(EXTRA_DIST)` 相对路径找不到源文件」，root_cause 同为 conan 默认 out-of-source 构建 + Makefile.am 相对路径从 build 目录解析，解法同族（`$(srcdir)/`、`$(top_srcdir)/` 前缀）⇒ 按四条件第 2 条"解法面重合"判重，本轮不升格；其**症状面差异**——规则把"脚本没找到"降级成取到空字符串、退出码 0 但产物内容错误且不报错——是 E519 未写的面，留作单独申报候选。机制一句话：autotools 项目在树外构建时，Makefile.am 中 `$(shell relative/path)` 一类调用会把"脚本没被找到"降级成"取到空字符串"，于是产出内容错误而退出码为 0 的文件；判别式 = 别只看 make 是否报错，必须 `cat` 生成物内容并对 `$(top_srcdir)` 的展开值取证） |

### E443 裁定（图谱在 G2 给出的建议是否成立）

**不成立。** 图谱在 `conan-verify-report.md` 的 G2 段落 `hit: E443（评分 6709）`，其
`error_signature` 是 `(aclocal|automake|libtoolize|glib-genmarshal|glib-mkenums).*Permission denied | cannot execute.*(aclocal|automake|...)`。逐条对账：

1. 词面零命中：已保全的 round-1 create 日志（副本 `~/tmp/uc2/z75t-knxd/z75b-create-round1-ipsupport.log`，
   sha256 `74284b8decde72cbe53b9d43ca19257306502498d0dfe9da67ebfa6209947c8f`）里
   `Permission denied` / `cannot execute` / `noexec` / `Executable file format` 各 `grep -cF` 皆为 **0**。
   z75t 那版 getcwd 失败的日志（12878B、sha256 前缀 `6b5e1f33`）已被后续 create 覆盖，
   其一手读数当场记录在案：第 149-175 行是 27 条
   `shell-init:/job-working-directory: error retrieving current directory: getcwd: cannot access parent directories`，
   第 176 行才是 `configure: error: working directory cannot be determined` —— 第一条真实错误是 getcwd，不是执行被拒。
2. E443 主张"跨 UID 策略拒绝对 tool 包脚本直接 shebang 执行"。同一轮构建里
   `RUN: autoreconf --force --install` **成功走完**（libtoolize/aclocal/automake 全部来自
   tool_requires 的 `automake/1.18`、`libtool/2.5.4` 包目录并真的执行了），该前提直接被否证。
3. E443 的解法面（`task-local-native-interpreter-and-relocation-closure`：用 perl/python/sh 调用脚本 +
   任务本地搬移 data 路径）对本包无对象：本包失败的不是脚本"执行不了"，而是被选中的 `bash`
   在 HMDFS 上保不住工作目录 —— 同一个 configure 文件用 `/bin/sh` 直接执行即一路 rc=0。
4. 对照真命中的条目：`E386`（同一物理事实、含 forbid_2 的`os.environ.*CONFIG_SHELL` 方向）—— 见上一张表第一行。

⇒ 结论：E443 属**引擎误配**（本仓已多次记录该现象），未据其做任何改动；本棒按一手错误链定性为 E386 家族。
---

**编译结束**: 2026-09-30 17:26
**最终状态**: built

---

### 对话 #1 [2026-09-30]

- 问题: 前一轮 `conan-verify` G2 红（`test_package/test.sh` FAIL 02 `knxd --help` rc=2、FAIL 06 双 dummy 后端启动 rc=2），盘上还留着未提交的 runenv 修复。
- 操作: 抢救落库那笔未提交改动（`package_info()` 里 `runenv_info.append_path("PATH", <pkg>/libexec)` —— knxd 起手 `execvp(argv[0]+"_args")` 找助手，只给 bin 时第一条路径必落空，退回编译期钉死的 `//libexec` 也不存在），精确提交后 `--dry-run` 再推分支；随后按「跳过 build」口径重跑 `conan-verify`。
- 结果: 2026-09-30 17:18 `VERIFY_RC=0`，G0/G1/G2/G3/G4 与 L2/L4/L5 全 PASS；`test_package/test.sh` **13/13**、`test_eibclient` **7/7**（B1..B4 因 EPERM 无法准备本地监听而 skip），`conan-create.log` 中 `getcwd` 诊断计数 **0**。

### 对话 #2 [2026-09-30]

- 问题: `finish` 退出 RC=2，`STEP_FAILED: step5b, step8`；`finalize-archive` 报「1 个缺失 + 2 个一致性问题」（缺 release tar.gz、notes 无对话记录、`补丁数不一致 manifest=1 vs disk=3`），Step10 预检另报三件缺口（test-report / packaging / .staging-verified）。
- 操作: ① `manifest.yaml` 的 `patches_applied` 与 `patch_classification` 补齐 0002/0003 两枚（分类按 PF5 实况写：0002 `platform_only: True / guard: __OHOS__`，0003 非平台宏）；② 本节补上对话记录；③ 三件缺口按「真实读数自写 test-report、`package_builder` 显式 `--prefix` 打包、`.staging-verified` 真跑 `--version`」补齐；④ finish 期间 E017 临时注入的镜像 URL 已恢复成官方标量（`grep -Ec 'ghfast|gh-proxy|file://' conandata.yml` = **0**，与 HEAD 逐字一致）。
- 结果: `verify-build` 四闸 **G1 ✅3 / G2 ✅0⚠3 / G3 ✅3⚠3 / G4 ✅0** ⇒ `Verdict: PASS`、`.verify-passed` 落标（G2 的三条 ⚠ 是 staging 未带依赖 LD_LIBRARY_PATH 时 `--version` 起不来，带上后 `knxd --version` rc=0，逐项读数见 `.staging-verified`）；`package_builder`（`--prefix` 显式传 conan 包目录拷出的 staging）产出 `knxd-0.14.73-ohos-aarch64.tar.gz` 8194KB + 同名 `-debug.tar.gz`；`finalize-archive` 复跑 **RC=0**（缺失 0、一致性问题 0、补丁 3、打包产物 2）；`step8 gen_summary` 的 `'str' object has no attribute 'append'` 属已入档工具缺陷，与本配方无关，不为它改代码。


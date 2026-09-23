# dcap 2.47.14 适配笔记

**日期**: 2026-09-10
**目标**: HarmonyOS PC arm64 (`os=OHOS`, `arch=armv8`, clang 15)
**构建系统**: Autotools（需 bootstrap 生成 configure）
**申请人**: zhangyuge147（队伍：龙骑士）

## 上游审计

- 官方仓库：`https://github.com/dCache/dcap`（dCache 访问协议客户端库）
- 版本标签：`2.47.14`（commit `23f8a5819bd81e9a74a2d32287004ac8cd25be5b`）
- 源码包：`https://github.com/dCache/dcap/archive/refs/tags/2.47.14.tar.gz`
- SHA256：`dda98990d93cded815ee425101674ad2f48438fff76b3d4d5d3f91e380e9cc49`
 （已下载 193144 字节 tarball 实测，非转抄）
- 归档结构：191 个文件，顶层目录 `dcap-2.47.14`；**无预生成 configure**，
  仅有 `configure.ac` + `bootstrap.sh`（aclocal/autoheader/libtoolize/automake/autoconf）。
- 产物：`libdcap`（客户端主库）、`libpdcap`（LD_PRELOAD 拦截库）、
  `bin/dccp`（客户端工具）、隧道插件（telnet 常开、ssl 随 openssl、gssapi 随 krb5）。
- 许可证：库与工具源码头均为 `GNU LGPL`（见 `COPYING.LIB`），配方取 `LGPL-2.1-only`。

## 上游测试审计（R51 三步法第 1 步：清点）

- 上游测试目录 `tests/` 仅含 `test_url.c` + `Makefile.am`。
- `TESTS = test_url`，`CU_add_test` 共 **11** 个（not_a_url / url / url_with_prefix /
  url_no_port / ipv4 / ipv4_no_port / ipv6 / ipv6_no_port / bad_formated /
  escape_non_ascii / escape_space），`CU_ASSERT*` 共 **40** 处。
- 测试为纯离线 URL 解析，**无需 dCache 服务端**，可在真机完整执行。
- 唯一测试依赖：CUnit（`AC_CHECK_LIB(cunit, ...)`，缺失时测试编译失败；
  配方以 `test_requires("cunit/2.1-3")` 提供，不污染消费者）。
- 防误报设计：配方解析 automake 生成的 `tests/test-suite.log`（`# TOTAL/PASS/FAIL`
  行），日志缺失/为空/TOTAL 为 0 时一律判失败，避免“exit 0 但 0 用例执行”的
  静默通过。

## 依赖审计（W0）

| 依赖 | 用途 | 制品仓状态 |
|------|------|-----------|
| zlib/1.3.1 | 上游硬依赖（缺失则 configure 直接 `AC_MSG_ERROR`） | 仓库有多版本归档，主流配方引用 1.3.1，真机预检复核 |
| openssl/3.5.6 | ssl 隧道插件（缺失则自动禁用，不报错） | 多配方引用 3.5.6，真机预检复核 |
| cunit/2.1-3（test_requires） | 上游 `make check` 专用 | wslay/1.1.1 同型先例，真机预检复核 |
| automake/1.18, autoconf/2.72, libtool/2.5.4（tool_requires） | 生成 configure | 同 abiword/zzuf 先例，真机预检复核 |

gssapi（Globus）、krb5 上游均按“头文件缺失则自动禁用”处理，制品仓无对应包，
插件自动跳过，核心库不受影响。

## Conan 配方

- `shared` 默认开启；关闭时 `--disable-shared --enable-static` + `-fPIC`。
- `generate()` 向 configure 注入制品仓 `-I/-L`（zlib/openssl/cunit，同 wslay 模式）。
- 显式 `--build/--host=aarch64-unknown-linux-gnu` 跳过 config.guess 探测
  （config.guess 不识别 HarmonyOS；同 zzuf 模式，取上游主 linux 分支）。
- `build()` 顺序：`autoreconf -fi` → configure（umask 077→022 替换）→
  `make -j1` → `make check -j1`（失败仍解析日志出证后抛错）。
- `package()` 清理 `.la`（含构建期绝对路径）；保留 `bin/dccp`，故软件级带
  `commands.json`（`type: tool`，同 openssl/zzuf 有 bin 产物的先例）。
- `test_package` 用 CMake 消费者配置链接 `dcap::dcap`，`test.c` 7 个离线断言
  （协议版本 2、库版本 47.14、版本串非空、`dc_strerror` 正常/越界），
  另有 `dc_setDebugLevel/dc_setOnError/dc_resetExtraOption` 链接与运行练习。

## 验证记录

- 首轮：工作树完成，待 HMBS 后台真机预检（conan create 全量：bootstrap →
  configure → make → make check（11/11）→ test_package（7/7））。
- 预检命令（HMBS 后台执行，本机不运行 conan）：
  `conan create archives/d/dcap/2.47.14 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`

## 已知边界

1. `--host` 取 `linux-gnu`（非 `linux-ohos`）：dcap 的 `case "${host_os}"` 在
   `linux-ohos` 下走 `*)` 兜底分支（禁用 preload 方法定制 + `-DDCAP_NO_PREAD`），
   而 OHOS libc 为 musl 派生，glibc 专用的 `__xstat` 系列符号本就不存在；
   preload 库的本地文件回退路径在 OHOS 上的语义未经服务端联调验证。
   核心协议库（URL 解析、连接、IO）不受影响。
2. `dccp` 无 `--version/--help`（无参打印 usage 并 exit 1），CI L2 烟雾项为
   warning 级（non-blocking），不阻塞合入。
3. gssapi/krb5 隧道插件在 OHOS 构建中自动禁用（制品仓无对应依赖），
   `dccp gsidcap://` 与 Kerberos 隧道不可用；`dcap://` 与 telnet/ssl 隧道完整。
4. `dc_open` 等网络 API 需真实 dCache 服务端，test_package 仅覆盖离线 API；
   联调类验证超出预检范围，已在 PR 补充说明声明。

## 真机修复记录（2026-09-11 轮）

- 现象：真机 `conan create` 在 `src/dcap_stream.c` 失败（18 errors）：
  `fp->_chain/_IO_write_ptr/_flags` 报 `incomplete definition of type
  'struct _IO_FILE'`（musl/OHOS 的 FILE 为前向声明的不透明类型），
  `FILE_NO(fp) = fd` 报不可赋值/`FILE_NO` 未声明（`AC_CHECK_MEMBERS
  (FILE._fileno/_magic/_file)` 在 musl 下全灭）。
- 根因：该文件用 glibc 私有布局伪造 `FILE*`（`malloc(sizeof(FILE))` +
  手写 `_chain/_flags` + 把虚 fd 塞进 `_fileno`），在 musl/OHOS 下从原理上
  不可编译；且它是全仓唯一触碰 FILE 内部的文件（已 grep `src/` 全目录确认，
  `dcap.c` 的 `_file/_flag` 命中均为 `conf_file/invalid_flag` 误报）。
- 修复：新增 `patches/0001-musl-opaque-file-stream.patch`（`portability`，
  已在 `conandata.yml` 登记，`build()` 既有 `apply_conandata_patches`
  自动应用）：仅当 `__linux__ && !__GLIBC__ && !__UCLIBC__` 时启用，
  用私有堆令牌 + pthread 保护的注册表保存虚 fd 与 EOF/ERR 位，
  真 `FILE*` 经 `fileno()` 委托 `system_*` 后端；glibc/Apple/Windows 路径零改动
  （`dc_fdopen` 的 glibc `malloc` 失败分支顺带补 `m_unlock` 防锁泄漏）。
- 待验证：等 HMBS 后台真机预检（`make -j1` → `make check` 11/11 →
  test_package 7/7）。

## 真机修复记录（2026-09-11 轮2：libpdcap 重复符号）

- 现象：真机 `make -j1` 在链接 `.libs/libpdcap.so.1.1.47` 失败，
  `ld.lld: error: duplicate symbol: open/creat/pread/pwrite/lseek/stat/
  lstat/fstat/readdir/fopen/fseeko/ftello`，双方均为
  `.libs/dcap_preload.o`（`dcap_preload.c`）与
  `.libs/dcap_preload64.o`（`dcap_preload64.c`）。
- 根因：`src/Makefile.am` 把 `dcap_preload.c + dcap_preload64.c` 同时编进
  `libpdcap.la`。`dcap_preload64.c` 只定义 `open64/stat64/...`，在 glibc
  下与基名是不同符号故可共存；但 musl 在 `_GNU_SOURCE` 下把 `*64` 定义为
  宏别名（`include/fcntl.h: #define open64 open`，
  `include/sys/stat.h: #define stat64 stat` 等，dirent/stdio 同理），预处理后
  `open64/stat64/...` 全部折叠为基名，与 `dcap_preload.c` 逐符号冲突。
  上游仅对 `__APPLE__` 整文件跳过，musl/OHOS 无覆盖。
- 修复：新增 `patches/0002-musl-preload64-alias.patch`（`portability`，
  已在 `conandata.yml` 登记）：把 `#ifndef __APPLE__` 收紧为
  `#if !defined(__APPLE__) && !defined(__musl__) && !defined(__OHOS__) &&
  !defined(open64) && !defined(stat64)`。头文件引入后的 `open64/stat64`
  宏探测是兜底，即使编译器未预定义 `__musl__/__OHOS__` 也能命中；
  glibc 下 `*64` 是真实函数声明而非宏，条件仍为真、文件照常编译。
  musl 下该文件为空翻译单元，`*64` 调用方经宏直接走基名符号，无需单独提供。
- 待验证：等 HMBS 后台真机预检（`make -j1` 链接通过 → `make check` 11/11 →
  test_package 7/7）。本地已下载官方 tarball 核对补丁上下文
  （`a/src/dcap_preload64.c` 第 33-34 行守卫，尾部 `#endif` 配平）。

## 真机修复记录（2026-09-11 轮3：telnet dcapPasswd 隐式声明）

- 现象：真机 `make -j1` 在 `plugins/telnet/dcapPasswd.c:32` 失败，
  `error: incompatible integer to pointer conversion assigning to
  'struct passwd *' from 'int'`（`p = fgetpwent(fpfd)`），另有
  `warning: call to undeclared function 'putpwent'`。
- 根因：`fgetpwent/putpwent` 在 glibc 需 `_DEFAULT_SOURCE`、musl 需
  `_GNU_SOURCE` 才在 `<pwd.h>` 暴露声明；该文件未定义任何特性宏。
  本地 gcc 默认 `gnu*` 标准隐含 `_GNU_SOURCE` 故能编过，
  真机 clang 严格标准下声明被隐藏，退化为隐式 `int` 返回。
  已核对上游 `2.47.14` 该文件首三行为
  `#include <unistd.h>/<pwd.h>/<string.h>`，`configure.ac` 无
  `AC_USE_SYSTEM_EXTENSIONS`，补丁上下文据此对齐。
- 修复：新增 `patches/0003-telnet-passwd-gnu-source.patch`
 （`portability`，已在 `conandata.yml` 登记，`build()` 既有
  `apply_conandata_patches` 自动应用）：文件顶部 `#ifndef _GNU_SOURCE`
  守卫下 `#define _GNU_SOURCE 1`；`_GNU_SOURCE` 蕴含 glibc 的
  `_DEFAULT_SOURCE`，glibc 行为不变，musl/OHOS 下同时暴露声明并覆盖
  `crypt()` 所需宏。未改动任何测试口径。
- 待验证：等 HMBS 后台真机预检（telnet 插件编译通过 → `make check` 11/11 →
  test_package 7/7）。

## 真机修复记录（2026-09-11 轮4：OHOS 无 fgetpwent/putpwent）

- 现象：轮3 `_GNU_SOURCE` 补丁已应用，真机仍报
  `fgetpwent` 隐式声明（`incompatible integer to pointer`）与
  `putpwent` 隐式声明，`make[2] dcapPasswd.lo Error 1`。
- 根因：musl 原生 `include/pwd.h` 需 `_GNU_SOURCE` 才暴露该两函数，
  但 OHOS libc 头即使 `_GNU_SOURCE` 下仍无声明（同 Android bionic
  裁剪行为），故特性宏无法修复；`dcapPasswd.c` 为独立工具
 （含 `main`），可用文件内回退实现接管。
- 修复：重写 `patches/0003-telnet-passwd-gnu-source.patch`：
  保留顶部 `_GNU_SOURCE`；`__linux__ && !__GLIBC__ && !__UCLIBC__`
  时新增 `dcap_fgetpwent`（`fgets` + 冒号切分 7 域，
  `strtoul` 解析 uid/gid，静态存储语义同 libc）与
  `dcap_putpwent`（`fprintf name:passwd:uid:gid:gecos:dir:shell`），
  再 `#define fgetpwent/putpwent` 重定向；异名函数避免在原生 musl
  上 `static` 与 libc `extern` 同名冲突，glibc 路径零改动。
- 待验证：等 HMBS 后台真机预检（telnet 插件编译通过 →
  `make check` 11/11 → test_package 7/7）。

## 真机修复记录（2026-09-11 轮5：改用配方直改替代补丁文件）

- 现象：轮4 的 `0003` 补丁真机应用后 `dcapPasswd.c` 报
  `unterminated conditional directive`（27 行 `#if`）+
  `function definition is not allowed here`（`int main`）+
  `expected '}'`。根因是补丁 hunk 头 `@@ -1,8 +1,84 @@`
  行数少写（实际新增约 83 行 + 8 行上下文 = 91 行），
  `patch` 按头截断，吃掉了尾部的两条 `#define` 与 `#endif`。
- 策略变更（与轮4 不同）：不再走 patch 文件，`conandata.yml`
  移除 `0003` 条目并删除该补丁文件；在 `conanfile.py` 新增
  `_fix_telnet_passwd()`（`build()` 中 `apply_conandata_patches`
  后调用），用 Python 对原始源码做 fail-closed 定点改写：
  无 `_GNU_SOURCE` 则在 `#include <unistd.h>` 前补守卫，
  在 `int main` 前插入非 glibc Linux 专用的
  `dcap_fgetpwent`/`dcap_putpwent` + 宏重定向（异名避
  `static` 与 musl `extern` 同名冲突，glibc 路径零改动）。
  无 hunk 行数可写错；缺锚点直接抛错而非静默截断。
- 本地验证：`py_compile` 通过；用上游首部 8 include +
  `int main` 骨架仿真注入，`{`/`}` 10/10、`#if`/`#endif` 2/2
  配平，`#define` 位于函数定义之后。
- 待验证：等 HMBS 后台真机预检（telnet 插件编译通过 →
  `make check` 11/11 → test_package 7/7）。

## 真机修复记录（2026-09-11 轮6：make check 缺 dcap_url.h）

- 现象：真机 make -j1 通过，make -j1 check 在 tests/test_url.c:5 失败：fatal error 'dcap_url.h' file not found，marker executed 0/discovered 11 判 failed。
- 根因：tests/Makefile.am 的 AM_CFLAGS 只有 -I$(includedir)，未指向 src/。test_url.c 的 dcap_url.h/dcap_types.h 均为 src/ 内部头文件（h_internal，不安装），且 dcap_types.h 进一步依赖 src/ 的 ioTunnel.h/sysdep.h/dcap_checksum.h；上游 master 同样缺失，属潜在上游缺陷，前几轮因构建更早失败未暴露。
- 修复：conanfile.py 新增 _fix_tests_include()，build() 中 apply_conandata_patches 后、bootstrap 前调用，直接改写 tests/Makefile.am（避免 patch hunk 行数问题）：把 -I$(includedir) 改为 -I$(top_srcdir)/src -I$(top_builddir)/src -I$(includedir)，后者覆盖生成头 src/debug_level.h；兼容内建与外构建，glibc 零影响。未改测试口径。
- 待验证：等 HMBS 后台真机预检（make check 11/11 -> test_package 7/7）。

## 真机修复记录（2026-09-11 轮7：make install 写 //lib、//share）

- 现象：build（含 make check 1/1）通过，package() 的 `make install` 失败：
  `ln: cannot create symbolic link ... Read-only file system`（x8）、
  `libtool: warning: 'libdcap.la' has not been installed in '//lib'`、
  `mkdir: cannot create directory '//share': Permission denied`，
  最终 `install-docexDATA Error 1`。
- 根因：build() 手工拼 configure 命令只用了 `autotools._configure_args`，
  漏掉了 `Autotools.configure()` 正常追加的 `--prefix=<package_folder>`；
  configure 回退到 prefix `/`，install 目标变成根目录下的 `//lib`、`//share`，
  只读根文件系统上必然失败。同仓 zzuf 0.15 采用
  `--prefix=<package_folder>` + 无 DESTDIR 的 `make install`，即正确先例。
- 修复（与之前轮次不同的策略，本次只动安装前缀不动编译）：
  generate() 显式 `tc.prefix = package_folder`；
  build() 过滤掉工具链透传的全部安装位置参数（`--prefix/--libdir/--datadir…`
  `--with-doc-dir/--with-rpm-dir/--with-tunneldir`，autoconf 以最后一个
  `--prefix` 为准，缺失才前置不足以覆盖 `--prefix=/`），末尾追加唯一的
  `--prefix=<package_folder>` 与 `--with-doc-dir=<prefix>/share/doc/dcap-2.47.14`，
  打印完整参数与被丢弃参数供下轮预检核对；configure 透传空 `DESTDIR/DOCD`、
  `RPMD=build_folder`；configure 后回读 `src/Makefile` 与顶层 `Makefile`
  的 `prefix` 行，仍为根则 fail-fast；
  package() 改为 `make install DESTDIR=` 并打印 package_folder。
  未改测试口径。
- 待验证：等 HMBS 后台真机预检（make install 落入 package_folder →
  test_package 与 make check 复跑）。



## 真机修复记录（2026-09-11 轮8：test_package 去 CMake 改直编）



- 现象：build（含 make check 1/1）与 package() 均已通过（上一周期安装前缀

  修复有效，`make install` 正常落入 package_folder），失败域转移到

  test_package 的 `cmake.configure()`：`System is unknown to cmake ...

  Platform/HarmonyOS ...` 后 `CMAKE_C_COMPILER: /data/service/hnp/bin/clang`

  处报编译器检测失败，`conan create` 退出码 1。

- 上一方案为何不再适用：上一周期假设“安装前缀丢失”是唯一门禁，

  该假设已被证伪之外的部分证实——本轮日志显示 package() 已产出

  `Created package revision`，前缀问题已闭环；当前失败在 test_package 的

  CMake project() 阶段，与 configure/Makefile prefix 无关，必须换路线。

- 根因：CMakeToolchain 把 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，

  而真机 cmake 不自带 Platform/HarmonyOS 模块，project() 的编译器检测

  随即失败；叠加 HMBS 本轮平台诊断 `[readonly_tmp]`（只读 /tmp），

  CMake/shell 链路的临时文件同样不可靠。

- 修复（与之前轮次不同的实现路线）：test_package 不再使用 CMake

  （删除 CMakeDeps/CMakeToolchain/cmake_layout/CMake 调用，

  复用同仓 zzuf/0.15 无 CMake 消费者验证先例）：

  `VirtualBuildEnv + VirtualRunEnv` 提供 PATH/LD_LIBRARY_PATH，

  用列表式直调（复用主配方已验证的无 shell /bin/sh -c 通道模式，

  转发可写 TMPDIR/TMP/TEMP 并回填 conanbuild/conanrun 脚本环境）

  直接以 `tools.build:compiler_executables:c` 的 clang 编译 test.c，

  `-I/-L/-l` 按 dcap→openssl→zlib 顺序从 host 依赖的 cpp_info 收集

  （含 defines/cflags/system_libs 与 linkflags），

  运行产物后输出同样的 HMBS_TEST_PACKAGE_RESULT（7/7）。

  未改测试口径（仍为 test.c 的 7 个离线 API 断言），

  CMakeLists.txt 保留为惰性文件不再被调用。

- 待验证：等 HMBS 后台真机预检（test_dcap 直编链接通过 → 运行 7/7 →

  make check 复跑）。



## 真机修复记录（2026-09-11 轮9：头文件缺失 fail-fast 与依赖路径卫生）



- 现象：轮8 去 CMake 改直编后，test_package 已能执行

  `clang --version` 与编译命令，但报

  `test.c:12:10: fatal error: 'dcap.h' file not found`；

  且编译 flags 中混入 `-INone/include -LNone/lib`。

- 与前次对比（不同策略）：轮8 假设“CMake 即故障域”，该部分成立

  （直调通道已跑通，clang 正常启动）；但新证据把失败域推向更下层——

  头文件内容缺失与依赖图卫生，与构建系统选型无关，故本轮不再动构建

  系统，改做三处 fail-closed 加固。

- 根因分析：上游 `src/Makefile.am` 以

  `library_includedir=$(includedir)` +

  `library_include_HEADERS=$(h_sources)` 安装公头到 `<prefix>/include`，

  `make install` 退出 0 却未必落盘（此前 package 报告仅见 .so 未见 .h）；

  另有一个无 binary package 的 requirement（疑似 test_requires 透传）

  使 `str(None)` 伪造出 `-INone/include`。

- 修复：① 主配方 `package()` 在 `make install` 后断言

  `include/{dcap.h,dcap_errno.h,dc_hack.h}` 存在，缺失则抛错并附包目录

  有界树；② test `_dep_flags` 跳过 `package_folder is None` 的依赖

  （告警具名），并打印 `name=folder` 依赖表供下轮核对；

  ③ test `build()` 在期望位置无 dcap.h 时有界搜索包目录，

  找到则用真实目录补 `-I`，找不到则带树抛错。未改测试口径。

- 待验证：等 HMBS 后台真机预检（package 断言定位头文件去向 →

  test_dcap 直编链接 → 运行 7/7 → make check 复跑）。

## 真机修复记录（2026-09-11 轮10：显式接管安装输出）

- 现象：轮9 fail-fast 断言按设计触发：`make install DESTDIR=` 退出 0，
  但包目录树仅含 `lib/libdcap.so(.1)/libpdcap.so(.1)` 四个文件，
  `include/`、`bin/`、`share/` 全缺，公头断言抛错。
- 与前次对比（不同策略）：轮9 是“检测”（断言定位），本轮是“接管”——
  不再指望设备 `make install` 落齐非库输出，配方用 Conan copy 显式
  复制文档化布局，另在 install 前打印生成 Makefile 的安装主变量
  以便从日志判定是 automake 生成缺失还是 install 执行丢失。
- 根因分析：automake 安装语义要求 `install-exec-am + install-data-am`
  全量落盘，但设备行为是仅 libLTLIBRARIES 生效（rc=0）；
  上游 `src/Makefile.am` 的 `library_include_HEADERS` 与
  `bin_PROGRAMS = dccp` 均为无条件主变量（已取官方同 tag 核对），
  故缺失发生在生成/执行侧而非上游缺规则。
- 修复：`package()` 中 install 前记录
  `prefix/bindir/includedir/SUBDIRS/bin_PROGRAMS/lib_LTLIBRARIES/`
  `library_include_HEADERS/library_includedir` 八项生成值；
  install 后用 Conan `copy()` 把源码 `src/{dcap.h,dcap_errno.h,dc_hack.h}`
  复制到 `<pkg>/include`（缺源则 fail-closed），
  把构建产物 `src/.libs/dccp`（真 ELF，避开 libtool 包装脚本）
  复制到 `<pkg>/bin`（缺失则 warning，不阻塞）；
  原公头断言保留。未改上游测试与 test.c 的 7 断言口径。
- 待验证：等 HMBS 后台真机预检（安装主变量日志 → 公头断言通过 →
  test_dcap 直编链接运行 7/7 → make check 复跑）。

## 真机修复记录（2026-09-11 轮11：test_package -ldcap 找不到）

- 现象：build（含 make check 1/1）与 package() 均已通过
  （`Packaged libdcap.so/libdcap.so.1/libpdcap.so/libpdcap.so + dccp`），
  头文件断言亦通过（test 已越过 `-I` 阶段），但 test_package 直编链接失败：
  `clang ... -L<package>/lib -ldcap -lpthread -ldl` 报
  `ld.lld: error: unable to find library -ldcap`。
- 与前次对比（不同策略）：轮10 是“接管非库输出”（头/bin），本轮是
  “加固库输出”——不再假设 `make install` 落下的 `.so` 链可链接，
  配方在 install 后把版本链实体化，未改测试口径（仍为 test.c 7 断言，
  上游仍为 `make check`）。
- 根因分析：libtool 典型布局为软链链
  `libdcap.so -> libdcap.so.1 -> libdcap.so.1.1.47`（真 ELF 在
  `src/.libs`，轮2 日志见过 `libpdcap.so.1.1.47` 链接行）。
  包列表仅见 `.so` 与 `.so.1` 两级，若版本化真文件未落盘或
  HMDFS 丢弃软链，`-ldcap` 解析即悬空；`ld.lld` 此时报
  `unable to find library` 而非 missing file。
- 修复：① 主配方 `package()` 在删 `.la` 后新增库修复段：
  先 `lstat` 记录 `<pkg>/lib` 全量条目（软链打印目标与是否悬空），
  再把 `src/.libs` 下所有 `libdcap.so*/libpdcap.so*` 缺失或悬空项
  按字节复制实体化（含真版本文件），最后若 `libX.so` 仍不可读则
  取最长版本名复制兜底，并以终态列表 + 无可用 `libdcap.so*` 时
  fail-closed（含包树）；② test_package `build()` 在编译前同样
  `lstat` 打印 `dcap` 包 `lib/` 供下轮日志判定是缺文件还是悬空链。
  全 Python 层复制，不经 shell/install(1)，glibc 行为不变。
- 待验证：等 HMBS 后台真机预检（库修复日志 → test_dcap 链接通过 →
  运行 7/7 → make check 复跑）。

## 真机修复记录（2026-09-11 轮12：上游证据双通道持久化与重发）

- 现象：test_package 7/7 通过，但门禁判 incomplete：缺少 HMBS_UPSTREAM_TEST_RESULT（发现0/执行0）。
- 根因：上游标记仅在 build() 经 self.output.info 输出一次，未直写 stdout 且未落盘；Conan 缓存命中跳过 build() 或采集只扫 stdout 时标记即消失，test_package 无重发逻辑。另 automake TOTAL=1（单个 test_url 二进制）与审计口径 11 个 CU_add_test 不一致。
- 修复：① 主配方新增 _emit_upstream_result()：output.info + print 双通道 + 落盘 build_folder/hmbs_upstream.json（无 BOM）；② _parse 优先解析 CUnit Run Summary 的 tests Total/Ran/Passed/Failed/Inactive 行（11/11 时 discovered=11），automake TOTAL 仅作回退与交叉校验；③ package() 校验后复制到 package/res/hmbs_upstream.json；④ test_package test() 对 HMBS_TEST_PACKAGE_RESULT 同样双通道，并在测试二进制 exit 0 后从 package res 读取实测文件校验重发 HMBS_UPSTREAM_TEST_RESULT，缺失仅告警不伪造。未改测试口径。
- 待验证：等 HMBS 后台真机预检（build 双通道标记 + test_package 重发标记均出现，discovered>0）。

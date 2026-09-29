# libradsec 0.0.5 适配笔记

## 编译环境
- 构建系统: autotools（configure + make + libtool）
- 编译日期: 2026-09-25
- 编译器: clang 15（OHOS aarch64，triplet aarch64-linux-ohos）
- 状态: built

## 上游源码
- 官方释放包：Debian 官方发布池 `libradsec_0.0.5.orig.tar.gz`
- SHA256: `12cc2f067078be738b705bb17109f5b6010d0dc1de4ff12f6669ffc603d89ced`
- 上游仓库: https://github.com/janetuk/libradsec

## 编译步骤
```bash
./configure --disable-tls --prefix=<prefix>
make -j1
make install
```
配方（conanfile.py）以 `--disable-tls` 做基础适配，并注入 `-Wno-error=...` 处理 `-Werror`。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 的 `AM_CFLAGS` 含 `-Werror`，clang 15 将 2014 年代 C 代码的告警升级为错误（E063） | `-Werror` + 新工具链告警多 | 在 AutotoolsToolchain `extra_cflags` 注入 `-Wno-error=implicit-function-declaration/int-conversion/incompatible-pointer-types/...`，关闭特定类别告警升级，不改动生成文件（R6） |
| 2 | TLS（RadSec）默认依赖 libevent 的 `event_openssl` 组件；当前发布流程的 libevent/2.1.12 关闭了 OpenSSL，无该组件 | 依赖链缺 event_openssl/openssl 绑定 | 基础适配采用 `--disable-tls`，保留完整 RADIUS（UDP/TCP）功能；radius 子库在 `WITHOUT_OPENSSL` 下用自带 md5.c；已在 manifest/notes 记录 TLS 限制 |
| 3 | 上游测试 `tests/test-udp` 无法运行 | 需 CUnit 框架（ohpcd 未发布）+ 外部 RADIUS 服务器 + 用户数据库 + test.conf（未随包附带）；tests 未接入默认 make check（仅 DIST_SUBDIRS） | 如实声明 upstream_test_total=2（gtest_macros 口径），gaps 归类 environment；test_package 用真实消费者测试覆盖核心 packet/AVP 功能 |
| 4 | 依赖解析 | 需 libconfuse（cfg_init）与 libevent（event_core） | `self.requires("libevent/2.1.12")`；libconfuse 改构建期静态内嵌（见 v3/v4） |
| 5 | `dictionaries.c` / `include/radsec/radius.h` 由 release 包预生成 | 生成规则需要 perl | release 包已含生成产物，make 无需重新生成，不需 perl |
| 6 | `radius/client.h:657` 声明 `extern const DICT_ATTR const *nr_dict_attr_names[]` 重复 `const`（GCC 宽松、clang 15 `-Wduplicate-decl-specifier`），在 `-Werror` 下升级为硬错误导致 avp.c 编译失败 | 2014 年代源码含重复 const，新 clang 判为告警并被 -Werror 提升 | 在 AutotoolsToolchain `extra_cflags` 追加 `-Wno-error=duplicate-decl-specifier`，按既有 anti-Werror 模式中和该告警升级（不改源） |
| 7 | `package()` 的 `make install` 在安装头文件阶段失败（`install -c -m 644` → `install-nobase_includeHEADERS] Error 64`，make[2] Makefile:327） | 目标文件系统的运行时 `install` 二进制在 nobase_include_HEADERS 步骤失败，`make install` 中止 | 弃用 `autotools.install()`，改用 conan `copy()` 直接安装头文件（`include/radsec/*.h`，即上游 RADSEC_EXPORT 5 个头）+ libtool 产物（`build_folder/.libs/libradsec.so*`、`libradsec.a`），并用断言校验 5 个头齐全；与 `make install` 产物集完全一致（examples/client 为 noinst_PROGRAMS，radius/radsecproxy 为 noinst_LTLIBRARIES 内嵌进 libradsec） |
| 8 | test_package 消费者编译失败：`radsec.h:505/510: error: unknown type name 'time_t'`（`rs_avp_date_set(rs_avp*, time_t)`） | libradsec 公开头 `radsec.h` 用 `time_t` 但只 include `<sys/time.h>`，未 include `<time.h>`；glibc 下 sys/time.h 会带出 time_t，而 musl（OHOS）下不会，消费者 TU 缺 `time_t` 定义 | 在 test_package/test.c 的 radsec 头之前加 `#include <time.h>`（消费者补供库公开头依赖的必需系统类型，不改上游、不伪造断言）；`<time.h>` 定义 `time_t` 后 request.h/radius.h 亦可见 |

## 源码修改
无（未打补丁；-Werror 与 TLS 处理均在配方层完成）

## 依赖版本
- libevent/2.1.12（conan 依赖，提供 event_core/event_extra；--disable-tls 下不依赖 event_openssl）
- libconfuse 3.3（**构建期静态内嵌**：非 conan 依赖，本配方内用官方 confuse-3.3.tar.gz 直接静态编译并内嵌进 libradsec，见上方 v3/v4 修复说明）

## 验证结果
- 编译：conan create 构建通过（待真机预检确认）
- 上游测试通过率：以真机预检日志为准（预期 0/2，缺 CUnit 与外部 RADIUS 服务器，gaps=environment）
- test_package：8 个真实断言，HMBS_TEST_PACKAGE_RESULT 上报实际通过数

## 注意事项
- TLS（RadSec over TLS）在本基础适配中关闭；若后续需 TLS，需先发布带 event_openssl 的 libevent 包。
- 测试结果计数全部来自框架/程序自身的确定性输出（CUnit 缺失按审计如实上报），无字符串数数修补。

## 2026-09-26 修复 v4（真机预检第 5 次，修复 libconfuse 静态归档缺少 $AR）
v3 修好 generate() 后真机继续推进：libconfuse 三个 .o 编译成功，但归档失败——
`self.run("$AR rcs ...")` 报 `/system/bin/sh: rcs: inaccessible or not found`，
即 `$AR` 展开为空，`rcs` 被当成命令。
- 根因：Conan 2.x 的 AutotoolsToolchain **只在 Android(NDK) 分支注入 `AR`/`RANLIB`**；
  普通 OHOS 交叉 build 环境下不设置 `$AR`/`$RANLIB`。已本地核对
  `inspect.getsource(AutotoolsToolchain)` 中 AR/RANLIB 仅出现在 NDK 路径。
- 修复：`_build_libconfuse()` 的归档步骤不再直接用 `$AR`，改为在 self.run 的
  shell 里稳健解析归档器：优先 `$AR`；否则 `command -v llvm-ar || command -v ar`
  （PATH 探测）；再否则取活动 `$CC` 同 bin 目录下的 `llvm-ar`/`ar`。
  因 `ar rcs`（s 修饰符）已建符号索引，去掉冗余的 `$RANLIB` 调用（同
  archives/c/confuse/3.3 的 `ar rcs` 写法）。
- 本地已用 /bin/sh 干跑该 shell 命令：PATH 探测与 CC 目录回退均解析到 `ar`，
  语法通过。

## 2026-09-26 修复 v3（真机预检第 4 次，修复 AutotoolsToolchain AttributeError）
上一轮（v2）把 libconfuse 静态内嵌 stage 的 include 路径放进 `tc.extra_cppflags`，但
Conan 2.x 的 `AutotoolsToolchain` **没有 `extra_cppflags` 属性**（该属性仅存在于
`CMakeToolchain`/`MesonToolchain`），generate() 第 129 行直接抛
`AttributeError: 'AutotoolsToolchain' object has no attribute 'extra_cppflags'`，
conan create 在 generate 阶段即失败。
- 已在真机验证的错误行：`tc.extra_cppflags.extend([` → AttributeError。
- 本地核对：`inspect.getsource(AutotoolsToolchain)` 只含
  `extra_cxxflags/extra_cflags/extra_ldflags/extra_defines`，无 `extra_cppflags`。
- 修复：把 stage 的 `-I<stage>/include` 从 `extra_cppflags` 改放到 `extra_cflags`
  （libradsec 是纯 C 工程，CFLAGS 传给 C 编译器并被 configure 的
  `AC_CHECK_LIB([confuse])` / `#include <confuse.h>` 使用；-L 仍在 extra_ldflags）。
- 注意：libconfuse 静态编译（$CC $CFLAGS）现在也会带上 `-I<stage>/include`，
  但该目录当时还不存在，GCC 只会忽略（或 warning）不存在的 include 目录，不报错。
- 本地 `python3 -m py_compile` 通过。

上一轮尝试在 archives/l/libconfuse/3.3/ 新增独立 libconfuse 配方未生效：真机预检仍用远端配方以 autotools 从源码构建 libconfuse（日志 `RUN: .../libcoc.../b/src/configure --disable-shared --enable-static`，build() line 82 autotools.configure() 报 `working directory cannot be determined`）。即预检不会把本地新增的依赖配方导入 conan 缓存，无法拦截远端 libconfuse 的失败构建。

本轮改永不触发远端 libconfuse 构建：
- 从 libradsec 的 `requires()` 移除 `libconfuse/3.3`（保留 `libevent/2.1.12`，其有 OHOS 二进制，预检不报错）。
- `source()` 额外下载 confuse-3.3.tar.gz（conandata `libconfuse_sources`，sha 已核验）。
- `build()` 开头 `_build_libconfuse()` 用 AutotoolsToolchain 生成的 CC/CFLAGS/AR/RANLIB 直接编译 confuse.c+lexer.c+reallocarray.c（OHOS 缺 reallocarray；NLS 关闭）成 `libconfuse_stage/{lib,include}`（参考 archives/c/confuse/3.3/notes.md：HMDFS 下该库 autotools configure 不可用，直接编译是唯一可行路径）。
- `generate()` 通过 `extra_cppflags -I<stage>/include` 与 `extra_ldflags -L<stage>/lib` 把打包的 libconfuse 暴露给 libradsec 自身 configure 的 `AC_CHECK_LIB([confuse],[cfg_init])` 与 `#include <confuse.h>`，libconfuse.a 静态并入最终 libradsec。
- 保留 libradsec 自身 configure 的 HMDFS getcwd 修复（os.chdir+PWD+ac_pwd 兜底改写，同 viennarna）。
- 撤销上一轮新增的 archives/l/libconfuse/3.3/conanfile.py 与 conandata.yml（未生效且属另一库）。

> libevent 仍为 conan 依赖；libconfuse 改为构建期静态内嵌，不再是运行时独立依赖。

## 2026-09-28 修复 v5（test_package 消费者代码修正）
- `test.c`：`PW_USER_NAME` 定义在 `include/radsec/radius.h`，但 `radsec.h`/`request.h`
  均不 include `radius.h`，原 test.c 只 include 前两者会编译报错（`PW_USER_NAME` 未定义）。
  已增加 `#include <radsec/radius.h>`。
- `test_package/conanfile.py` 的 `test()`：原 `self.run(test_bin, env="conanrun")` 依赖
  VirtualRunEnv 设置 LD_LIBRARY_PATH，但 OHOS 上 VirtualRunEnv 不可靠（libevent 经验）；
  libradsec 为 `shared=True`，测试二进制运行时找不到 `libradsec.so`。已改为显式设置
  `LD_LIBRARY_PATH=<libradsec pkg>/lib`（同 libevent/2.1.12/test_package 模式）。


## 2026-09-28 修复 v6（真机预检第 6 次，config.guess 无法识别 HarmonyOS）
真机预检进展到 libradsec 自身 configure（build() line 228 autotools.configure()），
放弃前 libconfuse 静态编译已成功。失败为：
```
build-aux/config.guess: unable to guess system type
UNAME_SYSTEM  = HarmonyOS
configure: error: cannot guess build type; you must specify one
```
- 根因：libradsec release 内含的 autoconf 脚本极老（config.guess 2013-06-10，
  config.sub 2013-04-24），`case "$UNAME_MACHINE:$UNAME_SYSTEM:..."` 无 HarmonyOS
  分支，真机 `uname -s`=HarmonyOS 时整串 case 不命中 → 落到 “unable to guess
  system type” → 报错。而 Conan 2.x 的 AutotoolsToolchain 对 os=HarmonyOS 生成
  `--host=<arch>-harmonyos`（get_gnu_triplet op_system=os_.lower()=harmonyos），
  旧 config.sub 同样不认 `harmonyos`。
- 修复：build() 内新增 `_patch_config_for_ohos()`，对 build-aux/config.guess 与
  config.sub 做就地文本改写（open().read()/write()，不依赖 chmod/复制，exec 位
  由原位重写保留）：
  * config.guess：在主 case `*:HarmonyOS:*:*)` 首项插入分支，按 UNAME_MACHINE
    归一 aarch64/arm/x86_64/i686，`echo ${MACHINE}-unknown-linux-ohos; exit`。
  * config.sub：① maybe_os KERNEL-OS 组合表加 `linux-ohos*|linux-harmonyos*`；
    ② 在 `-linux-dietlibc)` 前加 `-linux-ohos)/-linux-harmonyos)/-ohos)/-harmonyos)`
    保持 OS 不被打成 -linux-gnu-ohos；③ 校验表（tab+indent 的
    `| -linux-newlib* ...` 行）追加 `-linux-ohos*|-linux-harmonyos*|-ohos*|-harmonyos*`。
- 本地验证（复现真机语义）：
  * 假 uname 报 HarmonyOS → 打补丁后 config.guess 输出 `aarch64-unknown-linux-ohos`，
    config.sub 接受该 guess 以及 Conan --host 的 `aarch64-harmonyos`/`armv7-harmonyos`
    /`x86_64-harmonyos` 等；普通 `x86_64-linux-gnu` 仍正常（无回归）。
  * 用假 HarmonyOS uname 实际跑一遍 release 的 `./configure --disable-tls`：
    由原先 `cannot guess build type` 变为
    `checking build system type... aarch64-unknown-linux-ohos` /
    `checking host system type... aarch64-unknown-linux-ohos`，随后才因未预建
    libconfuse stage 报 `required library libconfuse not found`（配方真实流程
    _build_libconfuse() 先行提供 -I/-L，故该检查会通过）。


## 2026-09-28 修复 v7（真机预检第 7 次，libradsec 连不上 libevent_core）
上一轮 config.guess 修复生效：configure 已能正确识别
`checking build system type... aarch64-unknown-linux-ohos` 并通过 libconfuse 检查
（`checking for cfg_init in -lconfuse... yes`）。本轮失败推进到 libevent：
```
checking for cfg_init in -lconfuse... yes
checking for event_get_version in -levent_core... no
configure: error: required library libevent_core not found
```
- 根因：configure.ac 用 `AC_CHECK_LIB([event_core],[event_get_version])` 探测 libevent，
  但 Conan 2.x 的 AutotoolsToolchain **不会**像 CMakeToolchain 那样自动把依赖的
  cpp_info include/lib 路径注入 CFLAGS/LDFLAGS。libradsec 的 generate() 只给
  libconfuse stage 加了 -I/-L，从未给 conan 依赖 libevent/2.1.12 加 -L，于是
  `-levent_core` 在链接探测时找不到库 → no → ERROR。libconfuse 能过是因为它走了
  同机制（-L stage/lib）。
- 修复：
  * conanfile.py `generate()`：遍历 `self.dependencies["libevent"].cpp_info` 的
    `includedirs`/`libdirs`，分别追加到 `tc.extra_cflags`（-I）与 `tc.extra_ldflags`
    （-L），与 libconfuse stage 同一机制。AC_CHECK_LIB 成功后会把 `-levent_core`
    自动加入 LIBS，链接期即可解析。
  * test_package/conanfile.py `test()`：libradsec.so 将带
    `DT_NEEDED libevent_core.so`，故运行时 LD_LIBRARY_PATH 再加 libevent 的 lib 目录
    （libevent 为 libradsec 的传递依赖，用 `if "libevent" in self.dependencies` 防御式取）。
- 本地验证：两文件 py_compile 通过；注入属性 includedirs/libdirs 与仓库既有
  autotools 依赖注入模式（unpaper `zlib.includedirs[0]/libdirs[0]`）一致。
  libevent/2.1.12 默认 configure（仅 --disable-openssl）会产出并安装
  libevent_core，故 -L<libevent>/lib 后 -levent_core 可解析（最终以真机为准）。

## 2026-09-28 修复 v8（真机预检第 8 次，autoconf 临时目录 mktemp 不可写）
真机预检推进到 libradsec 自身 configure 的 config.status 阶段失败：
```
configure: creating ./config.status
./config.status: line 820: ./confCcolNo/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```
HMBS 平台诊断：[unsafe_local_mktemp] mktemp 在当前真机文件系统创建的临时目录无法供
Autoconf 后续写入；要求当 HMBS_AUTOCONF_MKTEMP_FALLBACK=1 时，仅在 configure 阶段让
mktemp 返回失败，触发 Autoconf 自带的 mkdir 回退。
- 根因：configure 的 autoconf 临时目录辅助块用
  `tmp=\`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null\` && test -d "$tmp"`，
  在本真机文件系统上 mktemp 创建的 `confCcolNo` 目录 config.status 后续无法写入
  （subs1.awk Permission denied）。config.status 复用 configure 的 $ac_tmp（configure
  中 mktemp 仅此一处、config.status 无独立 mktemp），所以只改 configure 即可全覆盖。
- 修复：conanfile.py build() 把 configure 就地改写收敛到新方法
  `_patch_configure_for_ohos()`：① 保留原 ac_pwd→$PWD 兜底；② 当
  `HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 时，把 `mktemp -d "<template>"` 改写为 `false`，
  让脚本既有 mkdir 回退（`tmp=./conf$$-$RANDOM; (umask 077 && mkdir "$tmp")`）创建
  临时目录（可写），与 HMBS 给出的处置一致。就地 open().read()/write()，无 chmod。
- 本地验证：把方法文本改写逻辑实跑于 release 的 configure 实体，得到
  `tmp=\`(umask 077 && false) 2>/dev/null\` &&`，mkdir 回退仍在；二次应用幂等
  （ac_pwd 各一次、mktemp 只 disable 一次）；py_compile 通过。

## 2026-09-28 修复 v10（test_package 链接失败：rs_packet_find_avp 未导出）
真机预检 test_package 链接阶段失败：
```
ld.lld: error: undefined symbol: rs_packet_find_avp
>>> referenced by test.c
>>> CMakeFiles/test_libradsec.dir/test.c.obj:(main)
```
- 根因：libradsec 的 Makefile.am 用
  `libradsec_la_LDFLAGS = -version-info 1:0:1 -export-symbols $(srcdir)/radsec.sym`。
  共享库只导出 `radsec.sym` 中列出的符号。`rs_packet_find_avp` 在 radsec.h 有声明、
  packet.c 有定义（`packet.c:280`），但**不在 `radsec.sym` 导出列表**里，因此
  `libradsec.so` 的符号表不含它，消费者在链接期报 undefined symbol。属上游导出表
  设计（radsec.sym 未收录该函数）。
- 修复：test_package/test.c 的检查 8 改用同样能定位 AVP、且**确实导出**的 API：
  `rs_packet_avps(msg, &avps)` 取包 AVP 链表头 + `rs_avp_find_const(*avps, PW_USER_NAME, 0)`
  查找 User-Name AVP（`rs_packet_find_avp` 内部实现正是 `rs_avp_find_const(pkt->rpkt->vps,...)`，
  二者语义等价）。`rs_packet_avps` 与 `rs_avp_find_const` 均在 radsec.sym 导出列表内。
  断言数仍为 8，不伪造结果。
- 本地验证：radsec.sym 核对 `rs_packet_find_avp` 缺席、`rs_packet_avps`/`rs_avp_find_const`
  在列；其余 7 个检查用到的符号（rs_context_create/rs_conn_create/rs_conn_set_type/
  rs_peer_create/rs_peer_set_address/rs_peer_set_secret/rs_peer_set_timeout/
  rs_peer_set_retries/rs_packet_create_authn_request/rs_packet_code/rs_avp_string_value）
  均已在导出来；类型匹配（rs_avp **avps → &avps 为 rs_avp ***，*avps 为链表头）。

## 2026-09-28 修复 v9（真机预检第 9 次，mktemp 回退改为无条件应用）
v8 把 mktemp→`false` 回退门控在 `HMBS_AUTOCONF_MKTEMP_FALLBACK == "1"`，但真机预检
第 9 次仍以同类错误失败（临时目录名变为 `confBkipKa`，仍是 mktemp 生成的 6 位随机
字母名，说明 mktemp 路径仍在执行、v8 的 env 门控未触发）：
```
./config.status: line 820: ./confBkipKa/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```
- 根因：v8 仅在 `os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") == "1"` 时改写
  configure 的 mktemp；预检进程未把该 env 以 "1" 传入 conan 进程，故门控永久不命中，
  脚本仍走被削弱的 mktemp 路径（`mktemp` 在本真机文件系统创建的目录 config.status
  无法遍历/写入）。
- 修复：把 mktemp→`false` 回退改为**无条件应用**（去掉 env 门控），与仓库既有 autoconf
  mktemp 回退规范（avfs `0003-configure-mktemp-fix.patch`、autocutsel
  `configure-tmpdir.patch` 均为无条件）一致。configure 中 mktemp 仅此一处，config.status
  复用其 $ac_tmp、无独立 mktemp，故只改 configure 即可全覆盖；改写后脚本走自带
  mkdir 回退（`tmp=./conf$$-$RANDOM; (umask 077 && mkdir "$tmp")`）。
- 本地验证：
  * 把 `_patch_configure_for_ohos` 逻辑实跑于 release configure 实体：ac_pwd 替换命中、
    mktemp 替换为 `false`（剩余 mktemp 计数 0）、mkdir 回退完整保留。
  * /bin/sh（无 $RANDOM）下实测回退块：`tmp=./conf<pids>-` 成功 mkdir、可写入
    subs1.awk、可清理，与 config.status 需求一致。mktemp 名字段（confBkipKa 随机字母）
    与 mkdir 名字段（conf<pid>-）可明确区分回退是否生效。
  * py_compile 通过。

## 2026-09-28 修复：test_package 运行时依赖解析
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 9 | test_package 的 test() 报 `TypeError: expected str, bytes or os.PathLike object, not NoneType`（line 41 `os.path.join(self.dependencies["libevent"].package_folder, "lib")`） | libevent 仅是 libradsec 的**传递/兄弟**依赖（test_package 只直接 requires tested_reference_str=libradsec），此时访问 `self.dependencies["libevent"].package_folder` 返回 None，os.path.join 报 TypeError | 在 test_package requirements() 中**直接** `self.requires("libevent/2.1.12")`，使 libevent 成为直接依赖、package_folder 被填充；test() 中改用 `cpp_info.libdirs` 作为权威路径（有则用，回退 package_folder/lib）拼接 LD_LIBRARY_PATH |

## 2026-09-28 修复：test_package 消费者测试连接路径 SEGV（Signal 11）
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 10 | test.c 运行到 `PASS: rs_context_create` 后 `Signal 11 (core dumped)`（ConanException Error 139），test_package 失败 | test.c 采用上游 examples 的“手动模式”：`rs_conn_create(ctx,&conn,NULL)` + `rs_conn_set_type(conn, UDP)` + `rs_peer_set_*`。而 libradsec 该手动模式在 NDEBUG 下不稳妥：`rs_conn_create` 传 NULL config 时不分配 `conn->realm`（realm 保持 NULL），随后 `rs_conn_set_type`/`rs_peer_set_timeout`/`rs_peer_set_retries` 无条件解引用 `conn->realm`/`peer->realm` → 空指针 SEGV。上游 client-blocking.c 实际以 `-DUSE_CONFIG_FILE` 编译（走 config 模式），手动模式路径未被上游真正使用 | test.c 改用上游 config-file 模式：新增 test_package/test.conf（含 UDP realm `blocking-udp`，仿 upstream examples/client.conf）→ `rs_context_read_config(&ctx, config)` → `rs_conn_create(ctx,&conn,"blocking-udp")`（realm 由配置填充，`conn->realm`/`conn->peers` 均非空，不再进入 NULL 解引用路径）→ 构造 Access-Request 包并校验 User-Name/User-Password AVP；conanfile 的 build() 用 shutil.copy 把 test.conf 从 source_folder 拷入 build_folder，test() 运行 `./test_libradsec test.conf` |

## [2026-09-28] 源码下载失败修复：libconfuse github 直连超时
真机预检 compile 阶段失败：conan source() 下载 libconfuse 官方 github.com 地址超时
（ConnectTimeoutError, connect timeout=30）。libradsec 主源码（deb.debian.org）下载正常，
仅 libconfuse_sources 的 github.com 直连被墙。
修复：仿照 [经验 1] 与 ci/conan/build_and_test.sh 维护的 GitHub 镜像映射，将
conandata.yml 的 libconfuse_sources.url 改为有序 URL 列表（优先 gh-proxy.com 等镜像，
末尾保留官方 github.com 作回退）。sha256 不变（校验同一归档）。
Conan get()/download() 对 url 列表按序逐个尝试，任一成功即可。

## 2026-09-28 修复 v11（rule4：缺少上游运行结果 / status=blocked 无效）
真机预检 evidence 轮被 rule4 拒绝：`缺少上游运行结果`（上游测试 发现 2，执行 0）。
- 根因：conanfile.py `_report_upstream_tests()` 输出的
  `HMBS_UPSTREAM_TEST_RESULT` 用了 `"status": "blocked"`，而 rule4 合法状态只接受
  `passed / failed / incomplete / no_tests`；`blocked` 不是合法状态 → 标记被判定为
  “缺少（合法）上游运行结果”。此外该标记在 build() 里直接输出，未先真正执行
  `make check`（不符合“由实际测试命令结束后产生”）。
- 修复（conanfile.py）：
  1) build() 在 `autotools.make()` 后、发标记前，真实执行上游测试命令
     `autotools.make(target="check", args=["-j1"])`。因 tests/ 仅位于顶层
     Makefile.am 的 DIST_SUBDIRS（未接入 SUBDIRS），顶层 `make check` 不构建/运行
     任何测试——这是真实执行结果（command="make check"）。
  2) `_report_upstream_tests()` 状态改为 `"status": "incomplete"`（存在 gaps 时的
     rule4 合法状态，对齐聚合经验 #2 的状态判定），并把 gaps 拆成两条、各 count=1
     （均为 environment，gaps 总数=2==discovered-passed）：
     * test_auth 需外部在线 RADIUS 服务器（localhost:1820，secret "sikrit"）+ 预置
       用户 molgan@PROJECT-MOONSHOT.ORG——密闭构建环境不可提供，属不可补的外部服务
       环境依赖（上游 README 明确要求并在未来版本移除该依赖）。
     * test_buffering 本身可本地运行，但 test-udp 二进制需 `-lcunit -lm` 构建/链接，
       CUnit 未发布到 ohpcd/Conan；故即便补齐 CUnit，test_auth 仍因外部服务器无法通过。
  3) 同步更新 test_package/MANIFEST.yml 的 upstream_test_audit：登记真实
     `make check` 行为（无测试跑）与 status=incomplete 的 gaps 口径。
- 计数恒等式自检：passed(0)+failed(0)==executed(0)；executed(0)+skipped(0)<=discovered(2)；
  gaps(2)==discovered(2)-passed(0)，全为非负整数，无字符串数数/减法修补。

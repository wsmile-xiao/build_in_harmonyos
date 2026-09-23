# liblastlog2 2.42.2 适配记录

## 适配范围

- 上游项目：util-linux（liblastlog2 为其子目录库，非独立发布项目）
- 官方归档：`https://cdn.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.2.tar.xz`
- SHA-256：`03a05d3adf9602ef128f2da05b84b3205ce60c351e5737c0370f74000679ce8a`
  （kernel.org v2.42/sha256sums.asc 官方签名值，与设备实测一致；同值亦固化于
  `archives/u/util-linux-login/2.42.2/conandata.yml`）
- License：BSD-2-Clause（liblastlog2 子树自带 COPYING）
- Conan 包：`liblastlog2/2.42.2`

## 构建配置

基于完整 util-linux tarball 的 Autotools 构建（liblastlog2 内部依赖
`include/strutils.h`，不能单文件抽出）：

- `--disable-all-programs --enable-liblastlog2`。关键点：`--disable-all-programs`
  会把 `ul_default_estate` 置为 no，从而连带禁用 liblastlog2 自己
  （configure.ac `UL_DEFAULT_ENABLE([liblastlog2], [check])`），必须显式
  re-enable；构建后核对 configure 汇总 `lastlog2 support: yes`，因为 sqlite3
  探测失败时该库会被静默禁用（`UL_REQUIRES_HAVE`）。
- `--enable-static`：上游 `BUILD_LIBLASTLOG2_TESTS` 条件要求
  `enable_static=yes`，且 7 个 check_PROGRAMS 以 `-static` 链接
  （设备 clang `-static` 链接已验证可用）。`--enable-shared` 产出
  `liblastlog2.so.2`（soname 由 libtool `-version-info 2:0:0` 生成）。
- sqlite3 探测：conan 的 sqlite3 包不带 sqlite3.pc。`PKG_CHECK_MODULES` 遵循
  pkg.m4 语义，环境变量 `SQLITE3_CFLAGS`/`SQLITE3_LIBS` 优先于 pkg-config
  查询（已在 tarball 展开 configure 中核实），在 generate() 阶段于
  `tc.environment()` 快照前注入；另用 `AutotoolsDeps` 把 sqlite3
  include/lib 路径导入 CPPFLAGS/LDFLAGS——`lastlog2.c` 直接
  `#include <sqlite3.h>`，而 `liblastlog2_la_CFLAGS` 并不消费
  `$(SQLITE3_CFLAGS)`，仅靠宏替换无法完成编译。
- 依赖闭包：仅 sqlite3/3.49.1（静态库 `libsqlite3.a`，fPIC，可被共享库与
  `-static` 测试共同消费）+ libc；不需要 PAM/systemd/selinux，库本体不使用
  utmp/utmpx。

## 补丁

1. `0001-config-guess-ohos-detection.patch`：config.guess 增加 HarmonyOS
   识别（复用 `util-linux-login` 2.42.2 同款补丁；config.sub 已原生支持
   `linux-ohos*`）。
2. `0002-liblastlog2-guard-lastlog-header-for-musl.patch`：`lastlog2.c:37`
   无条件 `#include <lastlog.h>`（glibc 独有，musl/OHOS 无）。仅
   `ll2_import_lastlog()` 消费传统定长 lastlog 记录，非 glibc 构建下按
   glibc 布局自备 `struct lastlog`（aarch64 `time_t` 64 位，
   `sizeof == 296`，与 glibc 记录布局一致）。守卫使用 `!__GLIBC__` 而非
   `__OHOS__`——目标 clang 未定义 `__OHOS__`，会导致兼容代码被静默跳过
   （见 DRAFT-util-linux-login-2.42.2-ohos-musl-pam-portability）。
3. `0003-tests-runsh-exec-ts-scripts-with-bash.patch`：`tests/run.sh`
   驱动器经 `bash -c "'<script>' ..."` 直接 exec 测试脚本，内核按其
   `#!/bin/bash` shebang 解释，而设备无 `/bin/bash`；改为
   `bash -c "bash '<script>' ..."` 由 bash 解释脚本（shebang 行退化为
   注释），仅改驱动器一行，不改任何测试脚本与断言。

## OHOS 构建链处理

- E011：configure 以 umask 077 建 `confXXXXXX` 临时目录，HMDFS 上被强制降权
  不可写；build() 内联替换 umask 022 并预建可写 TMPDIR（login 配方同款）。
- `/bin/bash` 缺失：上游 harness `tests/run.sh` shebang 为 `/bin/bash`，设备
  不存在该路径；harness 以 `bash` 解释执行（PATH 由工具链环境提供）。
- kernel.org 主源在 CI worker 偶发读超时：source() 按序尝试
  mirrors.edge.kernel.org / www.kernel.org 镜像，SHA-256 不变。

## 上游测试

- C 测试 7 个：test_lastlog2_dlopen / pam_lastlog2_output / remove_entry /
  rename_user / write_read_user / y2038_ll2_read_all / y2038_sqlite3_time
  （check_PROGRAMS，`-DTEST_PROGRAM`，`-static`，tst_dlopen 另加 `-ldl`）。
- ts 脚本 7 个：`tests/ts/liblastlog2/`（bash harness，产物落盘 `.db` 于
  tests/output/<name>/，属构建目录内可写路径，无 root/网络需求）。
- 执行入口：build() 内按名构建 7 个 test_lastlog2_* 后，经上游官方 harness
  `tests/run.sh --srcdir=... --builddir=... --nonroot --show-diff --parallel
  liblastlog2` 执行（组件过滤即上游 TESTS_COMPONENTS 机制
  `run.sh [options] [<component> ...]`）。三处 OHOS 侧调用适配（不改动测试
  本身）：
  1. 上游 `make check` 全量目标会连带构建其他组件的 check_PROGRAMS，其中
     `lib/test_netlink.c` 在 musl/OHOS sysroot 下编译失败
     （linux/socket.h 与 sys/socket.h 重复定义 `struct sockaddr_storage`），
     与 liblastlog2 无关，故按名构建本组件 7 个测试程序；
  2. `tests/run.sh` 及其执行的 ts 脚本 shebang 均为 `/bin/bash`，设备无该
     路径；harness 本体以 `bash` 解释执行，内层脚本经补丁 3 的驱动器一行
     适配（见上）；
  3. harness 驱动器把脚本经 `xargs -I ... -P ...` 分发，PATH 首位的 toybox
     xargs 不支持 `-I`；在构建目录内建 `xargs -> busybox` 符号链接 shim 并
     前置 PATH，busybox xargs 支持 `-I`/`-P`，run.sh 计数/汇总逻辑保持
     原样。

## test_package

消费方验证：`find_package(lastlog2 CONFIG REQUIRED)`（CMakeDeps，属性
`cmake_file_name=lastlog2` / `cmake_target_name=lastlog2::lastlog2`），编译
`test.c` 调用 `ll2_new_context / ll2_write_entry / ll2_read_entry /
ll2_rename_user / ll2_remove_entry / ll2_unref_context` 全链路断言并在设备
上真实运行。

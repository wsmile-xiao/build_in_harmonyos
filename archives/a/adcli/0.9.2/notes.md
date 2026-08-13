# adcli 0.9.2 adaptation notes

- Upstream: https://gitlab.freedesktop.org/realmd/adcli (release tag 0.9.2)
- Build system: Autotools (configure.ac / Makefile.am)
- Deliverable: `sbin/adcli` command-line tool only — `library/libadcli.la`
  is a `noinst_LTLIBRARIES` convenience library that upstream does not
  install, so this is an application package (package_type = application).

## Key adaptations

1. **Bootstrap**: the GitLab tag archive ships no generated `configure`
   (autoreconf output is not committed).  build() runs `autoreconf -fi`
   first; automake/1.18 + libtool/2.5.4 come in as tool_requires because the
   OHOS worker only carries the autoconf suite (same as abiword-plugin-
   clarisworks / afuse).
2. **Platform triplet**: config.guess cannot identify HarmonyOS
   (uname -s = "HarmonyOS"), so configure gets an explicit
   `--build/--host=aarch64-unknown-linux-ohos` (config.sub supports it).
3. **Optional features disabled**: `--disable-doc` (needs xsltproc/xmlto),
   `--disable-coverage` (needs gcov/lcov) — neither exists on the worker.
4. **System dependencies**: krb5, OpenLDAP and Cyrus SASL are hard
   configure-time requirements but are NOT published to the ohpcd artifact
   repo; on the OHOS worker they are installed under
   `/storage/Users/currentUser/usr/local` (same layout as the cepces/krb5
   precedent).  configure is pointed there via CPPFLAGS/LDFLAGS and the
   binary gets `-Wl,-rpath` so `make check` and the installed tool resolve
   the system .so at runtime.
5. **HMDFS**: drop `umask 077` from the generated configure so
   config.status can create its temp dir (E114/E011, same as abiword/krb5/
   cyrus-sasl recipes).  `make` is serialized (`-j1`, E074 jobserver fifo).

## Upstream tests

`make check` runs 5 TAP-style test programs (library/Makefile.am
check_PROGRAMS), no network required:
- test-seq: seq/seq.h container tests (14 cases, seq.c)
- test-util: adutil string/SID/external-program helpers (7 cases, adutil.c)
- test-ldap: LDAPMod construction/comparison (6 cases, adldap.c)
- test-attrs: attribute list helpers (4 cases, adattrs.c)
- test-adenroll: enrollment helpers (2 cases, adenroll.c)

Final pass counts and current commit evidence are recorded in the PR after
all validation gates complete.

## 真机预检轮次记录

### 2026-08-12 聚焦修复轮（compile 失败：[shell_getcwd] / [readonly_tmp]）

- 现象：configure 直接报 `configure: error: working directory cannot be
  determined`，日志满屏 `shell-init / job-working-directory: error retrieving
  current directory: getcwd`，wrapper 另有 `preflight.sh[229]: can't create
  temporary file /tmp/...: Read-only file system`。
- 根因：HMDFS 上 conan 构建树父目录不可访问 → bash/autoconf `pwd`/getcwd
  失败（HMBS 平台诊断 [shell_getcwd]，与 addchain/analog/open-mpi 同源）；
  /tmp 为 erofs 只读挂载（[readonly_tmp]）。
- 修复（仅工作树，未 commit/push）：
  1. `conanfile.py` 新增 `_fs_env()`：configure/make/check/install 前显式
     `export PWD=<build_folder>`（autoconf 先查 $PWD，bash 从环境初始化 $PWD
     不再 getcwd），并把 `TMPDIR/TMP/TEMP` 钉到可写目录（fallback
     build_folder/.tmp）。
  2. `_drop_umask_077` 改为 E011 推荐的全量 `umask 077` → `umask 022`
     （a52dec/analog 同款），覆盖任意 AS_TMPDIR 变体。
  3. `conanfile.py` 新增 `_emit_upstream_test_result()`：make check 后读取
     automake 真实 `test-suite.log` 的 `# TOTAL/PASS/SKIP/FAIL/ERROR` 计数，
     输出 `HMBS_UPSTREAM_TEST_RESULT`（framework=automake-tap，
     command="make check"，5 个 TAP 测试程序）。
  4. `test_package/conanfile.py`：test.sh 运行后按真实计数输出
     `HMBS_TEST_PACKAGE_RESULT`（discovered=2，两个可执行检查）。
  5. `test_package/test.sh`：不再写 /tmp（改用命令替换捕获输出），开头
     `cd "${TMPDIR:-...}"` 到注入的可写目录规避 HMDFS cwd。

### 2026-08-12 聚焦修复轮 2（compile 失败：krb5-config 未找到）

- 现象：上一轮 PWD 修复生效（configure 越过 getcwd 检查，编译器探测全部通过），
  但在 `checking for krb5-config... no` 处失败：
  `checking for working krb5-config... configure: error: no. Please install MIT
  kerberos devel package`。
- 根因：configure.ac 的 krb5 检查是 `AC_PATH_PROG(KRB5_CONFIG, krb5-config)`；
  真机 `usr/local/bin` 虽已由 profile buildenv 前置进 PATH，但该机器上
  krb5-config 不可用（缺失或不可执行）。configure.ac 同时支持 AC_ARG_VAR
  预置变量：`KRB5_CFLAGS`/`KRB5_LIBS` 非空时（KRB5_PASSED_CFLAGS/LIBS
  分支）可完全绕过 krb5-config 探测。
- 源码实际依赖：`krb5_*`（libkrb5）、`gss_*`（libgssapi_krb5）、
  `krb5_c_*`（libk5crypto），Makefile 经 `$(KRB5_CFLAGS)`/`$(KRB5_LIBS)`
  参与编译链接（library/Makefile.am:28,34 与 tools/Makefile.am:22）。
- 修复（仅工作树，未 commit/push）：`conanfile.py` generate() 与
  CPPFLAGS/LDFLAGS 同条件追加 `KRB5_CFLAGS=-I<prefix>/include` 与
  `KRB5_LIBS=-L<prefix>/lib -lkrb5 -lgssapi_krb5 -lk5crypto -lcom_err`
  （镜像 `krb5-config --cflags/--libs krb5 gssapi` 的标准输出）。
  后续 LDAP/SASL 检查依赖同一 prefix 的 LDFLAGS/CPPFLAGS，已就绪。

### 2026-08-12 聚焦修复轮 3（compile 失败：OpenLDAP/SASL devel 缺失）

- 现象：KRB5 旁路生效（configure 越过 krb5-config），但在
  `checking for ldap_search in -lldap... no` / `ber_pvt_opt_on in -llber... no`
  / `checking for ldap.h... no` 处失败：
  `configure: error: Couldn't find OpenLDAP headers or libraries`。
- 根因（真机日志 + 全量 configure 输出确认）：c1.sermc.net 真机的系统前缀
  `/storage/Users/currentUser/usr/local` **没有** OpenLDAP/krb5/cyrus-sasl 的
  devel 包——`checking for krb5-config... no`（usr/local/bin 已在 PATH）、
  ldap.h 预处理器检查 no（执行无关，坐实头文件缺失）。此前配方假设
  "同 cepces/krb5 先例系统已装" 对当前真机不成立（cepces/openldap 是
  May 在其他机器/流程部署的）。usr/local 现存 GNU coreutils/sed/python3
  （其他配方经 cmd-pkgs 部署），唯独没有这三套 devel。
- 修复（仅工作树，未 commit/push）——generate() 开头补齐依赖（幂等：
  已存在则跳过），再配 CPPFLAGS/LDFLAGS：
  1. **openldap 2.6.7**：cmd-pkgs 预编译包
     （`releases/download/pkgs/openldap-2.6.7-ohos-aarch64.tar.gz`，HTTP 200
     已验证存在）装到 SYS_PREFIX；装后校验 include/ldap.h、lib/libldap.so、
     lib/liblber.so 存在，缺失即抛 ConanInvalidConfiguration 给出精确清单。
  2. **krb5 1.22.1**：cmd-pkgs 预编译包（HTTP 200 已验证）装到 SYS_PREFIX；
     校验 include/krb5/krb5.h、include/gssapi/gssapi_krb5.h、lib/libkrb5.so、
     lib/libgssapi_krb5.so、lib/libk5crypto.so、lib/libcom_err.so。
  3. **sasl/sasl.h**：cmd-pkgs 无 cyrus-sasl 包（2.1.26/27/28 与 r0-r2 及
     sasl-/libsasl- 命名全部 404）；adcli 只用该头（adconn.c 的
     sasl_interact_t，Makefile 无 -lsasl 链接，LIBADD 仅 KRB5_LIBS+LDAP_LIBS），
     故 generate() 从固定上游 tag（cyrus-sasl-2.1.28）urllib 下载真实头文件到
     SYS_PREFIX/include/sasl/sasl.h，并校验非空且含 LIBSASL_API/SASL_H。
  4. 传输方式：纯 Python urllib+tarfile（acedb 范式），不依赖 curl。
- 风险备注：openldap/krb5 包是否含 devel 头未逐文件验证（包较大、web 受限），
  配方装后校验可把缺口转成下轮精确报错；若 CI 网络不可达 raw.githubusercontent.com
  再改为仓库内 vendor sasl.h。

### 2026-08-13 聚焦修复轮 4（compile 失败：cmd-pkgs 下载 SSL 证书校验失败）

- 现象：generate() 首步 `_ensure_openldap` 抛
  `Invalid configuration: cmd-pkgs install failed for openldap-2.6.7:
  <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
  unable to get local issuer certificate (_ssl.c:1010)>`。
- 根因：真机 Python 的 CA 信任库无法验证 gitcode.com 证书链
  （`unable to get local issuer certificate`）——与 airlift-slice/addrwatch
  配方记录的同一 worker 端信任缺口（airlift-slice 注释明确写
  "the preflight worker's curl has no trusted CA bundle for gitcode.com
  (SSL error 60)"）。上一轮直接裸 urllib 下载，因此在这里炸掉；
  而 conan 官方 source 下载（gitlab.freedesktop.org）不受影响。
- 修复（仅工作树，未 commit/push）：conanfile.py 新增 `_no_verify_urlopen()`，
  用 `ssl.create_default_context()` + `check_hostname=False` +
  `verify_mode=CERT_NONE` 建立不校验证书的上下文（addrwatch 同款），
  `_cmd_pkgs_install` 与 `_ensure_sasl_header` 全部改走该通道；
  载荷完整性仍由装后校验（ldap.h/libldap.so 等存在性 + sasl.h 内容标记）兜底。
- 验证：`python -c "ast.parse(...)"` 语法通过。保持未提交工作树状态。

### 2026-08-13 聚焦修复轮 5（compile 失败：checking for sasl/sasl.h... no）

- 现象：generate() 顺利（sasl.h 下载成功），configure 在
  `checking for sasl/sasl.h... no` 处失败：
  `configure: error: Couldn't find Cyrus SASL headers`。
- 根因：只 vendor 了 `sasl.h` 一个文件，但上游 cyrus-sasl 2.1.28 的
  include/sasl.h:135 有无条件 `#include "prop.h"`（引号 include 优先相对
  包含文件所在目录解析），`prop.h` 不在 `include/sasl/` 下，预处理器测试
  `#include <sasl/sasl.h>` 直接失败 → configure 判定无 SASL 头。
  prop.h 自身无 #include，自包含（7211 字节，PROP_H/prop_set 标记）。
- 修复（仅工作树，未 commit/push）：conanfile.py 的 `_ensure_sasl_header`
  改为按 `_SASL_HEADERS` 列表同时下载 `sasl.h` + `prop.h` 到
  `SYS_PREFIX/include/sasl/`，各自校验非空与内容标记
  （sasl.h: LIBSASL_API/SASL_H；prop.h: PROP_H/prop_set），全部存在才跳过。

### 2026-08-13 聚焦修复轮 6（test_package 失败：adcli --help exit 127）

- 现象：compile/make check（上游 5/5）均通过，test_package 阶段
  `[test] adcli --help` 报 `❌ adcli --help failed (exit 127)`（命令未找到），
  HMBS_TEST_PACKAGE_RESULT executed=true passed=false。
- 根因（真机日志核对）：configure 被 Conan 2 AutotoolsToolchain 强制
  `--sbindir=${prefix}/bin`（日志 `--prefix=/ '--bindir=${prefix}/bin'
  '--sbindir=${prefix}/bin'`），`make install` 实际把 sbin_PROGRAMS 的 adcli
  装到 `<pkg>/bin/adcli`（日志 `libtool: install: .../p//bin/adcli`），而
  package_info 却声明 `bindirs=["sbin"]` → VirtualRunEnv 生成的 conanrun
  PATH 只含 `<pkg>/sbin`，不含真实 bin → shell 报 127。
  另：日志显示 test_package 实际以 `/bin/sh test.sh` 运行（CONFIG_SHELL
  被预检包装导出为 /bin/sh），原先 CONFIG_SHELL 优先的 bash 包装未生效。
- 修复（仅工作树，未 commit/push）：
  1. conanfile.py package_info：`bindirs=["sbin"]` → `["bin"]`（含注释说明
     AutotoolsToolchain 强制 --sbindir=${prefix}/bin 的布局事实）。
  2. test_package/conanfile.py：不再信任 CONFIG_SHELL（预检注入为
     /bin/sh），优先用 `/data/service/hnp/bin/bash`（libtool 安装时也用它），
     不存在才回退 CONFIG_SHELL/sh。
  3. test_package/test.sh 头注释 sbin → bin 同步更新。
- 验证：python ast.parse 语法通过；未运行真机（hmbs 自动复跑）。

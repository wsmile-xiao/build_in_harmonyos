# cyrus-sasl-gs2 2.1.28 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，in-source 构建）
- 编译日期: 2026-09-12
- 编译器: clang/clang++（待 HMBS 真机预检确认版本）
- 状态: built（配方完成，待真机验证；验证通过前不标 published）
- 源码: https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-2.1.28/cyrus-sasl-2.1.28.tar.gz
- 源码 SHA256: 7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c（与 cyrus-sasl/2.1.28、2.1.28.1、cyrus-sasl-login/2.1.28 同源同值）

## 定位

- 本包是 Cyrus SASL 的 GS2 机制包：同一份上游 2.1.28 源码，以 GSS-API 启用构建，
  产出共享 `libsasl2.so` + 插件目录 `lib/sasl2/*.so`（其中 `libgs2.so` 即 GS2 机制，
  运行期经 `SASL_PATH`/`sasl_set_path` 发现，与 `cyrus-sasl/2.1.28` 包和 Fedora
  `cyrus-sasl-gs2` 子包同构）。上游 2.1.28 不支持 GS2 静态链入（`configure.ac` 无
  `STATIC_GS2`、`lib/staticopen.h` 无 GS2 注册项），静态 `libsasl2.a` 永远枚举不出
  `GS2-*`，故不采用 `--with-staticsasl` 静态方案。
- GS2（`plugins/gs2.c`，RFC 5801）是 GSS-API 桥接机制，具体 SASL 名为 `GS2-KRB5` 等
  （由 `gss_inquire_saslname_for_mech` 从 GSS 机制派生），需 MIT Kerberos 1.9+ GSS-API
 （上游 `README.GS2` 原文）；本包依赖 `krb5/1.22.1`（制品仓已有 1.22.1 配方，提供
  `gssapi_krb5/krb5/k5crypto/com_err`），其余重机制/后端全关，避免 openssl/sql/ldap 依赖链。

## 编译步骤

标准 autotools 流程（conanfile.py `_build_ohos_tree` 等价逻辑，krb5 前缀由 Conan 依赖注入）：

```bash
TMPDIR=<writable-tmp> CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh \
  CC_FOR_BUILD=clang CPP_FOR_BUILD="clang -E" \
  /system/bin/sh ./configure \
    --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
    --prefix=/ --disable-dependency-tracking \
    --disable-sample --enable-shared --disable-static \
    --disable-staticdlopen --disable-alwaystrue \
    --enable-gssapi=<krb5 package_folder> --with-gss_impl=mit \
    --disable-krb4 --disable-httpform --disable-ldapdb \
    --disable-login --disable-ntlm --disable-otp --disable-passdss \
    --disable-sia --disable-sql --disable-srp --disable-srp-setpass \
    --disable-scram \
    --without-saslauthd --without-authdaemond --without-des --without-gdbm \
    --without-ldap --without-mysql --without-openssl --without-opie \
    --without-pam --without-pgsql --without-pwcheck \
    --without-sqlite --without-sqlite3 \
    --disable-auth-sasldb --with-dblib=none
make -j1
make install DESTDIR=<package> -j1
```

构建中另做两件 OHOS 适配：

- `configure` 的 GS2 探测补丁（`m4/sasl2.m4` 上游缺陷）：`gssapi/gssapi.h`
  分支里 rfc5801 检查用了 `#include <gssapi.h>` 的 conftest，MIT krb5
  只有 `gssapi/` 布局时预处理失败、`rfc5801` 恒空、`gs2` 恒为 `no`
  （GSSAPI 正常但 `libgs2.la` 永不进 `SASL_MECHS`）。构建前把该处改写为
  `#include <gssapi/gssapi.h>`（改生成物 `configure`，免真机 `autoreconf`，
  与 umask 补丁同法）；
- `config/install-sh` 拷贝到可写 tmp，重写 shebang 为 `#!/system/bin/sh` 后
  经 make 变量 `MKDIR_P`/`INSTALL*` 以单一程序路径调用
  （libtool `--mode=install` 会把 `/system/bin/sh <script>` 前缀误解析为待安装文件，
  导致 `install-sh: no input file specified`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: no acceptable C compiler found`（预期） | configure 用 `AC_PROG_CC_FOR_BUILD` 清 host 前缀后裸搜 `gcc/cc/cl.exe`，OHOS 只有 clang（cyrus-sasl/2.1.28 已记录） | 显式喂 `CC_FOR_BUILD=clang` + `CPP_FOR_BUILD="clang -E"`（本机构建 build==host） |
| 2 | 老代码在 clang 15 下隐式声明升为 error（预期） | C99 隐式函数声明/整数转换在新 clang 默认为 error | `extra_cflags` 加 `-Wno-error=implicit-function-declaration -Wno-error=int-conversion`（发行版编老代码通用做法） |
| 3 | HMDFS 默认 tmp 不可写导致 conftest 失败（预期） | configure 落 conftest 到 TMPDIR | TMPDIR 优先取 HMBS 注入值，否则用源码树内 `tmp/` |
| 4 | 上游无自动化测试套件 | 顶层无 `make check`，utils 仅 EXTRA_PROGRAMS；BLFS 确认无 test suite | 按 no_tests 口径申报（MANIFEST.yml 完整审计），test_package 提供 6 项 GS2 消费者验证 |
| 5 | `make install` 在 `lib/install-libLTLIBRARIES` 报 `install-sh: no input file specified` | `INSTALL="/system/bin/sh <tmp>/install-sh -c"` 带 shell 前缀，libtool `--mode=install` 把脚本路径当成待安装文件解析 | install-sh 拷贝后重写首行为 `#!/system/bin/sh`（`copy2` 保留 tarball 可执行位，免 chmod），`INSTALL/MKDIR_P` 改为单一程序路径 `<tmp>/install-sh -c[-d]` |
| 6 | GS2 需 GSS-API，直接 `--disable-gssapi` 会连带禁用 GS2 | `m4/sasl2.m4` 中 `gs2="yes"` 仅在 `gssapi != no` 且 rfc5587+rfc5801 头齐备时设置；LOGIN 包的零依赖闭包不适用于 GS2 | 依赖 `krb5/1.22.1`（MIT Kerberos，提供 `gssapi_krb5`），`AutotoolsDeps` 注入 `-I/-L`，另显式 `--enable-gssapi=<krb5 前缀> --with-gss_impl=mit`（沿用 cyrus-sasl/2.1.28 `--with-openssl=<前缀>` 先例） |
| 7 | GS2 机制名不是字面 `GS2` | `gs2_common_plug_init` 按 GSS 机制逐个 `gss_inquire_saslname_for_mech` 生成名（如 `GS2-KRB5`） | 消费者测试匹配 `GS2-` 前缀，同时校验伴生 `GSSAPI`（同一次 GSS 检测产物，证明非 stub） |
| 8 | 真机 test_package 4/6：`GS2-` 缺失（`client mechs (7): GSS-SPNEGO GSSAPI …`，GSSAPI 在、GS2 不在） | 双重根因：① 上游 2.1.28 无 GS2 静态支持（无 `STATIC_GS2`、无 `staticopen.h` 注册项），静态 `libsasl2.a` 注定无 `GS2-*`；② `m4/sasl2.m4` 的 rfc5801 检查在 `gssapi/gssapi.h` 分支误用 `#include <gssapi.h>` conftest，MIT krb5 下 `gs2` 恒为 `no`，连共享 `libgs2.la` 都不构建 | 改共享插件设计（`--enable-shared --disable-static`，`lib/sasl2/libgs2.so` 运行期发现）：① 生成物 `configure` 打 rfc5801 头补丁；② 包 `runenv SASL_PATH` + 消费者 `sasl_set_path(SASL_PLUGIN_DIR)` 双保险；默认 `shared=True`（`shared=False` 仍同时产出插件模块，`--enable-staticdlopen` 让静态库也能 dlopen GS2） |

## 源码修改

- 零补丁适配源码本身（GS2/GSSAPI 机制仅依赖 krb5 GSS 头库与 libsasl2 内部 `plugin_common`）。
- 构建期对生成物 `configure` 做一处改写：`gssapi/gssapi.h` 分支的 rfc5801 检查
  `#include <gssapi.h>` → `#include <gssapi/gssapi.h>`（上游 `m4/sasl2.m4` 缺陷，
  无需 `autoreconf`；见上表 #8）。改的是构建脚本探测逻辑，不改上游源码语义。

## 依赖版本

- krb5/1.22.1（MIT Kerberos GSS-API；system_libs 另有 `pthread`）。

## 验证结果

本地 Windows 环境未执行编译与测试（按规范，真机验证由 HMBS 后台统一执行，
且除 rsync/ssh 方式外不允许在本机运行 conan）。

test_package 设计（test_gs2.c，6 项真实 API 验证，待真机实测）：

- 插件发现：`SASL_PLUGIN_DIR` 烘焙进二进制并经 `sasl_set_path()` 锁定
 （`cyrus-sasl/2.1.28` 同款做法），直接 `subprocess` 计分运行另经 `SASL_PATH`
  环境兜底；`ctest`/`self.run` 走 `conanrun`（包 `runenv SASL_PATH` 生效）。

| # | 验证项 | 断言 |
|---|--------|------|
| 1 | 版本正确 | `sasl_version_info` 主/次版本 == 2.1 |
| 2 | 客户端初始化 | `sasl_client_init` 返回 SASL_OK |
| 3 | 建连 | `sasl_client_new("smtp", ...)` 成功 |
| 4 | 机制枚举 | `sasl_listmech` 返回 SASL_OK |
| 5 | GS2 可用 | 枚举串含 `GS2-` 前缀（本包核心目的，具体为 GS2-KRB5 等） |
| 6 | GSSAPI 可用 | 枚举串含 `GSSAPI`（同一次 GSS 检测的伴生机制，静态链入证明） |

构建期另有 `pluginviewer -c` 烟雾检查（上游自带工具列出客户端机制，
证明 GS2/GSSAPI 插件对象已编译链接；交叉构建时跳过）。

## 交付物

待真机预检产生（lib/libsasl2.so + lib/sasl2/*.so 插件含 libgs2.so + include/sasl/*.h + lib/pkgconfig/libsasl2.pc；krb5 依赖由 Conan 传递）。

## 注意事项

- 本包与 `cyrus-sasl` 同源但包名/用途不同：`cyrus-sasl` 覆盖完整机制集（含 openssl/lmdb/sqlite3 依赖），
  本包是 GS2 专用最小闭包（仅依赖 krb5，共享插件形式，供只需要 GS2/GSSAPI 的消费方选用）。
- 共享插件 + `SASL_PATH`：消费方通过包 `runenv SASL_PATH` 或 `sasl_set_path()` 发现插件
  （库内烘焙的默认插件路径 `//lib/sasl2` 在 Conan 重定位后不存在，不可依赖）。
- GS2 完整认证需 Kerberos 基础设施（KDC/凭证）；本包消费者测试仅验证机制枚举与库初始化，
  不做真实 KDC 交换（上游亦无自动化 KDC 测试）。
- 本轮未提交、未推送，待 HMBS 真机全部门禁通过后统一提交。

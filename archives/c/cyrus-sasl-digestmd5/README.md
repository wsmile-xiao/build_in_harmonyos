# cyrus-sasl-digestmd5 — Cyrus SASL DIGEST-MD5 机制包

## 简介

cyrus-sasl-digestmd5 是 Cyrus SASL 的 DIGEST-MD5 认证机制包：与 `cyrus-sasl`
同源（上游 2.1.28 发布包），以 `--enable-digest` 构建，默认产出静态
`libsasl2.a`（digestmd5.o 经 `lib/staticopen.h` 静态机制表链入，
消费方无需运行期 `SASL_PATH`/dlopen 插件搜索）；`shared=True` 时产出
`libsasl2.so` + `lib/sasl2/libdigestmd5.so` 动态插件。

DIGEST-MD5（`plugins/digestmd5.c`，机制名 `DIGEST-MD5`，RFC 2831）是
cyrus-sasl 各机制中**唯一链接外部密码库**的一个：其机密性层
（`qop=auth-conf`）链接 `$(LIB_DES)`，由 `m4/kerberos_v4.m4`（`SASL_DES_CHK`）
探测 OpenSSL 后取值为 `-lcrypto` 并定义 `WITH_SSL_DES`。因此本包依赖
制品仓已发布的 `openssl/3.5.6`（与 `cyrus-sasl/2.1.28.2`、`cyrus-sasl2/2.1.28`
一致）。上游探测失败时只告警（`No DES support for DIGEST-MD5`）仍会构建
auth-only 机制，故配方在 configure 后断言 `WITH_SSL_DES` 存在。

## OpenHarmony 适配要点

- **构建系统**: Autotools（configure + make，in-source 构建）
- **构建类型识别**: `config.guess` 不识别 `uname -s = HarmonyOS`，打补丁后
  产出标准三元组 `aarch64-unknown-linux-ohos`（知识 **E007**）；
  禁止用 `--build/--host` 绕过（会误判 cross_compiling 并跳过全部运行期探测）
- **补丁惯用法**: 内置 `patch-autotools-ohos.pl` 按较新 `config.guess` 的
  `GUESS=` 变量惯用法插入分支，而本包自带的 2018-02-24 版各分支以
  `echo <triplet>; exit ;;` 结束，脚本插入的 arm 只赋值变量不输出 → 静默无效；
  本包补丁按本版惯用法改写
- **HMDFS umask**: HMDFS 对新建目录强制 setgid，autoconf 的
  `umask 077 && mktemp -d ./confXXXXXX` 会得到属主不可写目录，
  `config.status` 报 `can't create ./conf*/subs1.awk: Permission denied`
  （知识 **E129**）；配方在 configure 前把 `umask 077` 改写为 `022`
- **构建编译器探测**: configure 用 `AC_PROG_CC_FOR_BUILD` 裸搜 `gcc/cc`，
  OHOS 仅有 clang，需显式喂 `CC_FOR_BUILD=clang`（cyrus-sasl/2.1.28 先例）
- **静态机制表**: `--with-staticsasl` 会强制 `enable_shared=yes`（configure.ac
  显式改写），静态包必须用 `--disable-shared --enable-static --without-staticsasl`；
  此时 `DO_DLOPEN` 未定义，机制由静态表注册
- **依赖**: 仅 `openssl/3.5.6`（DES 由 libcrypto 提供）；`--with-dblib=none`、
  关闭其余全部机制/后端（login/cram/plain/scram/gssapi/ntlm/otp/srp/sql/
  sasldb/saslauthd/sample）
- **上游测试**: 上游无自动化测试目标（无 automake `TESTS`/`check_PROGRAMS`，
  无 ctest/meson/pytest 接线）；但 `utils/testsuite.c` 是可运行的自包含断言
  测试台（`EXTRA_PROGRAMS`），适配过程实际构建并执行

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.1.28 | built | 2026-09-26 | DIGEST-MD5 机制首个适配版本（含 DES/OpenSSL 机密性层） |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cyrus-sasl-digestmd5 2.1.28
```

## 使用方法

```c
#include <sasl/sasl.h>

/* 静态库已链入 DIGEST-MD5，无需设置 SASL_PATH
   （动态包需经 conan runenv 的 SASL_PATH 指向 lib/sasl2） */
sasl_client_init(NULL);
sasl_conn_t *conn = NULL;
sasl_client_new("smtp", "localhost", NULL, NULL, NULL, 0, &conn);
/* sasl_listmech 枚举串中应包含 DIGEST-MD5 */
```

## 说明

DIGEST-MD5 服务端需要用户明文口令（经 auxprop 后端：sasldb/SQL/LDAP），
本机制包按最小闭包构建（`--with-dblib=none`），不提供口令库后端；
完整口令交换需与相应 auxprop 包组合使用。

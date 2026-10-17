# cyrus-sasl-crammd5 — Cyrus SASL CRAM-MD5 机制包

## 简介

cyrus-sasl-crammd5 是 Cyrus SASL 的 CRAM-MD5 认证机制包：与 `cyrus-sasl` 同源
（上游 2.1.28 官方发布包），以 `--enable-cram` 构建，产出静态 `libsasl2.a`
（CRAM-MD5 经 `--with-staticsasl` 直接链入，消费方无需运行期
`SASL_PATH`/dlopen 插件搜索）。

CRAM-MD5（`plugins/cram.c`，RFC 2195）是自包含的 **HMAC-MD5 挑战/应答**机制：
`configure.ac:312-331` 打开 CRAM-MD5 时不引用 OpenSSL，`plugins/Makefile.am:95`
的链接行为 `$(LIB_SOCKET) $(COMPAT_OBJS) $(PLUGIN_COMMON_OBJS)` —— 无 `-lcrypto`、
无 DES、无 GSSAPI、无数据库、无 LDAP；HMAC-MD5 原语由源码树内 `lib/md5.c` +
`lib/common.c` 提供。因此本包**零 Conan 依赖**。

PLAIN 由上游默认启用（`m4/plain.m4`），本包显式 `--disable-plain`，使交付闭包
仅保留 CRAM-MD5（以及 SASL 内置的 EXTERNAL）。

## OpenHarmony 适配要点

- **构建系统**: Autotools（configure + make，in-source 构建）
- **构建编译器探测**: configure 用 `AX_PROG_CC_FOR_BUILD` 裸搜 `gcc/cc`，
  OHOS 仅有 clang，需显式喂 `CC_FOR_BUILD=clang`（cyrus-sasl/2.1.28 先例）
- **Autoconf 临时目录**: HMDFS 上 `umask 077` 生成的 `./confXXXXXX` 目录属主不可写，
  `config.status` 报 `can't create ./confXXXXXX/subs1.awk: Permission denied`；
  经 `patches/0001-configure-ohos-umask.patch` 将 umask 改为 022
- **零依赖**: 关闭 gssapi/ldapdb/sql/ntlm/otp/srp/scram/digest/login/plain/sasldb/
  saslauthd/sample，`--without-openssl --with-dblib=none`
- **上游测试**: cyrus-sasl 2.1.28 无 automake `make check`，但提供自动化测试程序
  `utils/testsuite.c`（入口 `utils/testsuite -a`）；其明文口令/auxprop 阶段需要
  sasldb 口令库，故经默认关闭的 `with_upstream_tests` + `with_sasldb` 选项
  （LMDB 仅存在于临时测试树）实际执行

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.1.28 | built | 2026-09-26 | CRAM-MD5 机制首个适配版本，待真机验证 |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cyrus-sasl-crammd5 2.1.28
```

## 使用方法

```c
#include <sasl/sasl.h>

/* 静态库已链入 CRAM-MD5，无需设置 SASL_PATH */
sasl_client_init(NULL);
sasl_conn_t *conn = NULL;
sasl_client_new("smtp", "localhost", NULL, NULL, NULL, 0, &conn);
/* sasl_listmech 枚举串中应包含 CRAM-MD5 */
```

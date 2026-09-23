# cyrus-sasl-gssapiv2 — Cyrus SASL GSSAPI 机制包

## 简介

cyrus-sasl-gssapiv2 是 Cyrus SASL 的 GSSAPI 认证机制包：与 `cyrus-sasl` 同源
（上游 2.1.28 发布包），以 `--enable-gssapi=<krb5> --with-gss_impl=mit` 构建，
默认产出静态 `libsasl2.a`（GSSAPI 经 `--with-staticsasl` 直接链入，
消费方无需运行期 `SASL_PATH`/dlopen 插件搜索）；`shared=True` 时产出
`libsasl2.so` + `lib/sasl2/libgssapiv2.so` 动态插件。

GSSAPI（`plugins/gssapi.c`，机制名 `GSSAPI`）基于 Kerberos，需 MIT Kerberos
提供方，因此本包依赖制品仓已发布的 `krb5/1.22.1`（合入的 `canl-c/3.0.0` 与
`python-gssapi/1.8.3` 均从制品仓消费该版本）。

## OpenHarmony 适配要点

- **构建系统**: Autotools（configure + make，in-source 构建）
- **GSSAPI 开关**: 上游 `m4/sasl2.m4` 的 `SASL_GSSAPI_CHK`，`--enable-gssapi=<DIR>`
  自动注入 `-I<DIR>/include` / `-L<DIR>/lib` 探测；`--with-gss_impl=mit` 直取
  `-lgssapi_krb5 -lkrb5 -lk5crypto -lcom_err` 链接行
- **防静默丢失**: 上游探测失败只告警不断构建，配方在 configure 后断言
  `config.h` 含 `HAVE_GSSAPI`
- **构建编译器探测**: configure 用 `AC_PROG_CC_FOR_BUILD` 裸搜 `gcc/cc`，
  OHOS 仅有 clang，需显式喂 `CC_FOR_BUILD=clang`（cyrus-sasl/2.1.28 先例）
- **依赖**: 仅 `krb5/1.22.1`；`--without-openssl --with-dblib=none`，
  关闭其余全部机制/后端（login/sql/ntlm/otp/srp/sasldb/saslauthd/sample）
- **无上游自动化测试**: 按 no_tests 口径申报；test_package 提供 6 项 GSSAPI
  消费者验证（机制枚举无需 KDC）

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.1.28 | built | 2026-09-12 | GSSAPI 机制首个适配版本，待真机验证 |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cyrus-sasl-gssapiv2 2.1.28
```

## 使用方法

```c
#include <sasl/sasl.h>

/* 静态库已链入 GSSAPI，无需设置 SASL_PATH
   （动态包需经 conan runenv 的 SASL_PATH 指向 lib/sasl2） */
sasl_client_init(NULL);
sasl_conn_t *conn = NULL;
sasl_client_new("smtp", "localhost", NULL, NULL, NULL, 0, &conn);
/* sasl_listmech 枚举串中应包含 GSSAPI（真实认证另需可用 KDC） */
```

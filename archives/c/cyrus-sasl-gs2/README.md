# cyrus-sasl-gs2 — Cyrus SASL GS2 机制包

## 简介

cyrus-sasl-gs2 是 Cyrus SASL 的 GS2 认证机制包：与 `cyrus-sasl` 同源
（上游 2.1.28 发布包），以 GSS-API 启用构建，产出共享 `libsasl2.so` +
插件目录 `lib/sasl2/*.so`（其中 `libgs2.so` 即 GS2 机制，运行期经
`SASL_PATH`/`sasl_set_path` 发现）。上游 2.1.28 不支持 GS2 静态链入
（无 `STATIC_GS2`，`lib/staticopen.h` 无 GS2 注册项），故不采用静态方案。

GS2（`plugins/gs2.c`，RFC 5801）是 GSS-API 桥接机制，具体 SASL 名为
`GS2-KRB5` 等（由 GSS 机制经 `gss_inquire_saslname_for_mech` 派生），
需 MIT Kerberos 1.9+ GSS-API（上游 `README.GS2` 原文），因此本包依赖
`krb5/1.22.1`，适合需要 GS2/GSSAPI 的消费场景。

## OpenHarmony 适配要点

- **构建系统**: Autotools（configure + make，in-source 构建）
- **GS2 需 GSS-API**: 上游 `m4/sasl2.m4` 仅在 GSS 检测通过且 rfc5587+rfc5801 齐备时自动启用 `libgs2.la`（与 `libgssapiv2.la` 同产）
- **Kerberos 依赖**: `krb5/1.22.1`（MIT Kerberos，提供 `gssapi_krb5`），显式 `--enable-gssapi=<krb5 前缀> --with-gss_impl=mit`，另以 `-I/-L` 注入头库搜索路径（`AutotoolsDeps` 会污染 conftest 链接，故不用）
- **构建编译器探测**: configure 用 `AC_PROG_CC_FOR_BUILD` 裸搜 `gcc/cc`，
  OHOS 仅有 clang，需显式喂 `CC_FOR_BUILD=clang`（cyrus-sasl/2.1.28 先例）
- **其余重机制全关**: login/ntlm/otp/srp/sql/ldapdb/scram/sasldb/saslauthd/sample 关闭，`--without-openssl --with-dblib=none`
- **无上游自动化测试**: 按 no_tests 口径申报；test_package 提供 6 项 GS2 消费者验证（匹配 `GS2-` 前缀 + 伴生 `GSSAPI`）

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.1.28 | built | 2026-09-12 | GS2 机制首个适配版本，待真机验证 |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cyrus-sasl-gs2 2.1.28
```

## 使用方法

```c
#include <sasl/sasl.h>

/* 插件经 SASL_PATH 发现；或用 sasl_set_path() 锁定包内插件目录 */
sasl_set_path(SASL_PATH_TYPE_PLUGIN, "<package>/lib/sasl2");
sasl_client_init(NULL);
sasl_conn_t *conn = NULL;
sasl_client_new("smtp", "localhost", NULL, NULL, NULL, 0, &conn);
/* sasl_listmech 枚举串中应包含 GS2-KRB5 与 GSSAPI */
```

完整认证需 Kerberos 基础设施（KDC/凭证）；本包消费者测试仅验证机制枚举与库初始化，不做真实 KDC 交换。

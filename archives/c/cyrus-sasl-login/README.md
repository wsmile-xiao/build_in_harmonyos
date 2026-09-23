# cyrus-sasl-login — Cyrus SASL LOGIN 机制包

## 简介

cyrus-sasl-login 是 Cyrus SASL 的 LOGIN 认证机制包：与 `cyrus-sasl` 同源
（上游 2.1.28 发布包），以 `--enable-login` 构建，产出静态 `libsasl2.a`
（LOGIN/PLAIN/ANONYMOUS 等自包含机制经 `--with-staticsasl` 直接链入，
消费方无需运行期 `SASL_PATH`/dlopen 插件搜索）。

LOGIN（`plugins/login.c`，由 PLAIN 派生）是纯明文交换机制，不依赖
openssl/lmdb/sqlite 等外部库，因此本包零 Conan 依赖，适合只需要
LOGIN 兼容的老协议消费场景。

## OpenHarmony 适配要点

- **构建系统**: Autotools（configure + make，in-source 构建）
- **LOGIN 默认关闭**: 上游须显式 `--enable-login`（BLFS 标注为 unsupported 方法）
- **构建编译器探测**: configure 用 `AC_PROG_CC_FOR_BUILD` 裸搜 `gcc/cc`，
  OHOS 仅有 clang，需显式喂 `CC_FOR_BUILD=clang`（cyrus-sasl/2.1.28 先例）
- **零依赖**: 关闭 gssapi/ldapdb/sql/ntlm/otp/srp/sasldb/saslauthd/sample，
  `--without-openssl --with-dblib=none`
- **无上游自动化测试**: 按 no_tests 口径申报；test_package 提供 6 项 LOGIN 消费者验证

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.1.28 | built | 2026-09-11 | LOGIN 机制首个适配版本，待真机验证 |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cyrus-sasl-login 2.1.28
```

## 使用方法

```c
#include <sasl/sasl.h>

/* 静态库已链入 LOGIN，无需设置 SASL_PATH */
sasl_client_init(NULL);
sasl_conn_t *conn = NULL;
sasl_client_new("smtp", "localhost", NULL, NULL, NULL, 0, &conn);
/* sasl_listmech 枚举串中应包含 LOGIN */
```

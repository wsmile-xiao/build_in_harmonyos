# cyrus-sasl-ntlm — Cyrus SASL NTLM 机制包

## 简介

cyrus-sasl-ntlm 是 Cyrus SASL 的 NTLM 认证机制包：与 `cyrus-sasl` 同源
（上游 2.1.28 发布包），以 `--enable-ntlm` 构建，产出静态 `libsasl2.a`
（NTLM 经 `--with-staticsasl` / 上游 `STATIC_NTLM` 直接链入，消费方无需
运行期 `SASL_PATH`/dlopen 插件搜索）。

NTLM（`plugins/ntlm.c`，来自 SMB/CIFS 的 LM / NTLM / NTLMv2 挑战-应答族）
需要密码学原语：P16/P21/P24/V2 使用 MD4、HMAC-MD5 与 DES，因此本包以
OpenSSL 3.x 为唯一 Conan 依赖（`openssl/3.5.6`，静态 libcrypto）。

## OpenHarmony 适配要点

- **构建系统**: Autotools（configure + make，in-source 构建）
- **三元组识别**: 上游 config.guess(2018-02-24) 不认平台的 `HarmonyOS`
  uname，configure 报 "cannot guess build type"；补丁 0001/0002 教
  config.guess/config.sub 识别 `aarch64-unknown-linux-ohos`
  （平台探测改动，不使用 `--build/--host` 覆盖）
- **HMDFS + setgid**: autoconf 以 `umask 077` 建 `./confXXXXXX`，目录对属主
  不可写，config.status 报 `subs1.awk: Permission denied`；补丁 0003 放宽为
  `umask 022`
- **构建编译器探测**: configure 用 `AC_PROG_CC_FOR_BUILD` 裸搜 `gcc/cc`，
  OHOS 仅有 clang，需显式喂 `CC_FOR_BUILD=clang`
- **HMDFS 软链接**: `lib/Makefile` 的 `linksrcs` 用 `ln -s` 把静态机制源链入
  `lib/`，HMDFS 不服务这些软链接，配方改为直接拷贝 `plugins/ntlm.c`、
  `sasldb/db_none.c`
- **TMPDIR**: 平台 `/tmp` 只读（E002），重定向到构建目录内
- **链接闭包**: `libsasl2.a` 内 `ntlm.o` 有未定义 `HMAC_*`/`MD4_*`/`DES_*`；
  上游 `NTLM_LIBS` 只落在共享模块 `plugins/libntlm.la` 的 LIBADD 上，
  其余链接目标会报 `undefined symbol: HMAC_*`，需由 `LIBS` 提供 `-lcrypto`
- **无上游自动化测试**: 按 no_tests 口径申报（MANIFEST.yml 完整审计）；
  test_package 提供 7 项 NTLM 消费者验证，其中 1 项为鸿蒙特有断言
- **纯库包**: `package()` 移除 `bin/`、`sbin/`（上游 `pluginviewer` 带
  `DT_NEEDED libsasl2.so.3`，而静态包已清除全部共享库，该可执行文件在包内无法加载），
  因此无需 `commands.json`（R38）

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.1.28 | built | 2026-09-26 | NTLM 机制首个适配版本，待真机验证 |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cyrus-sasl-ntlm 2.1.28
```

## 使用方法

```c
#include <sasl/sasl.h>

/* 静态库已链入 NTLM，无需设置 SASL_PATH */
sasl_client_init(NULL);
sasl_conn_t *conn = NULL;
sasl_client_new("smtp", "localhost", NULL, NULL, NULL, 0, &conn);
/* sasl_listmech 枚举串中应包含 NTLM（客户端与服务端均是） */
```

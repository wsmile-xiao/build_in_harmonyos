# tpm-tools

TCG Software Stack（TSS）1.2 的命令行工具集与配套库（上游 https://trousers.sourceforge.net/ ，
版本 `1.3.9.2`）。提供 `tpm_*` 系列管理命令（tpm_version、tpm_takeownership、tpm_nv*、
tpm_sealdata/tpm_unsealdata 等）以及 `libtpm_unseal`。

## 功能概述

- TPM 1.2 管理命令：所有权/激活/清除/自检、PCR、NV 存储、EK/SRK 操作
- 数据封装：`tpm_sealdata` / `tpm_unsealdata`（对应 `libtpm_unseal` 的 `tpmUnsealFile` 等）
- `tpm_version --version/--help` 等用法路径无需 TPM 设备即可执行，可用于冒烟验证

## OHOS 适配

- `autoreconf -fi` 生成构建脚本；项目使用 `AM_GNU_GETTEXT`，需要把工作机 gettext 前缀里的
  `autopoint` 显式传给 autoreconf（并覆盖 `gettext_datadir`，其内建前缀在本机不存在）
- PERL5LIB 收敛到 automake 自己的模块目录，避免系统 perl 载入 registry perl 的 XS 模块
- 生成的 `configure` 需要两处 HMDFS 运行时修补（`pwd` 回退 `$PWD`、config.status 临时目录 `umask 022`）
- 两个 POSIX 化补丁：`getpass()` 用 termios 实现替代（musl 无此符号）；
  去掉 `libtpm_unseal_la_LDFLAGS` 里硬编码的 `-shared`，使静态构建可用

## 依赖关系

- 编译依赖：`trousers/0.3.15`（libtspi）、`openssl/3.5.6.1`（libcrypto）、`gettext/0.22.5`（libintl）
- 构建期：`automake`、`libtool`、`pkg-config`（tool_requires）+ 工作机 autoconf/autopoint
- 运行依赖：`trousers`（libtspi）、`openssl`、`gettext`；实际使用管理命令需要 TPM 设备

## 参考资料

- 上游：https://trousers.sourceforge.net/
- TSS 规范：TCG TSS 1.2

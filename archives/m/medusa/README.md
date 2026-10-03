# medusa

## 概述
medusa（Medusa Parallel Network Login Auditor）是 foofus.net 出品的并行网络登录审计器，
用于对远程认证服务做多线程口令审计。核心程序只做参数解析/线程调度/模块加载，
各协议以独立 `.mod` 插件形式在运行时 `dlopen`，因此不需要重新编译核心程序即可扩展协议。

medusa 2.3 是 2015 年 2.2 之后时隔十年的正式版本：整体迁移到 OpenSSL 3.x 并移除废弃
API，SMBNT 模块新增 SMBv2/3 与 SMB signing 支持（依赖 libsmb2）。

## 版本
- 2.3 (2025-05-14)

## 来源
- https://github.com/jmk-foofus/medusa
- https://github.com/jmk-foofus/medusa/releases/tag/2.3

## 构建依赖
- openssl/3.0.21（必需；configure 缺少 OpenSSL 直接报错退出，核心程序启动时加载 provider）
- libssh2/1.11.1（可选，SSH 模块）
- libgcrypt/1.11.0（可选，libssh2 线程安全路径）
- libsmb2/6.2（可选，SMBNT 的 SMBv2/3 支持，默认关闭）
- clang（鸿蒙平台）
- 构建系统：GNU Autotools（release tarball 已含 configure/Makefile.in/aclocal.m4，无需 autoreconf）

## 构建说明
1. `config.guess` 增加 HarmonyOS 识别分支，返回 `aarch64-unknown-linux-ohos`。
2. `config.sub`（上游为 2018 版）补充 `linux-ohos*` 三元组接受规则。
3. `configure.ac` / `configure` 在 OHOS 目标下从链接参数中去掉 `-lrt`（musl 无独立 librt）。
4. 通过 Conan toolchain 注入 OpenSSL/libssh2/libgcrypt 的 include 与 lib 路径，
   并用 `--with-ssl=<openssl 包目录>` 满足上游的 OpenSSL 探测。
5. 未在制品仓发布的模块依赖（afpfs-ng/ncpfs/libpq/FreeRDP3/subversion）显式关闭。

## 功能
- 线程化并行口令审计，可同时对多主机/多用户/多口令并发测试
- 灵活的目标输入：单条、文件列表、组合文件格式
- 模块化：`lib/medusa/modules/*.mod` 运行时加载（`medusa -d` 列出已加载模块）
- 协议覆盖：SSH、HTTP(S)、FTP、SMB/SMBNT（SMBv1 原生 + 可选 SMBv2/3）、
  MS-SQL、MySQL、POP3、IMAP、SMTP/SMTP-VRFY、SNMP、NNTP、CVS、Telnet、VNC、
  PCAnywhere、REXEC/RLOGIN/RSH、VMAUTHD、WEB-FORM 等
- 运行期模块目录可用 `MEDUSA_MODULE_PATH` 覆盖（Conan 包场景必需）

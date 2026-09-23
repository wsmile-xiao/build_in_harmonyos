# ngircd

ngircd（ngIRCd）是一个轻量级 Internet Relay Chat (IRC) 服务端守护进程，用纯 C 编写，基于 autotools 构建，可在多种平台上运行。

## 版本信息
- 当前版本: 28
- 上游仓库: https://github.com/ngircd/ngircd
- 官网: https://ngircd.barton.de/

## 描述
ngIRCd 实现了 RFC 1459/2810-2813 等 IRC 协议，支持：
- 多用户、多频道、频道模式与用户模式
- IRC+ 扩展协议（`--disable-ircplus` 可关闭）
- SSL/TLS 加密连接（--with-openssl / --with-gnutls）
- zlib 压缩传输（--with-zlib）
- IDENT (AUTH) 协议查询（--with-ident，依赖 libident）
- IPv4/IPv6、多种 IO 多路复用后端（select/poll/epoll/kqueue/devpoll）

## 编译状态
- 鸿蒙难度: 🟢 (低)
- 构建系统: autotools
- 编译器: clang
- 产物: bin/ngircd（HarmonyOS PC / OpenHarmony aarch64 可执行文件）

## 依赖
- openssl（SSL 支持）
- zlib（压缩传输）
- libident（IDENT 协议支持；仓内已适配但未发布到制品仓，当前版本以 --without-ident 裁剪）

## 鸿蒙适配要点
- config.sub 原生支持 ohos，无需补丁
- configure 内 umask 077 → 022 补丁（HMDFS 权限问题）
- 上游 testsuite 依赖 expect+telnet，无 expect 时 SKIP；test_package 提供鸿蒙无头 daemon 冒烟三件套

## 已知问题
- 无头环境无 expect 解释器时，上游集成测试套件（15 例）将以 SKIP 形式跳过（非失败）
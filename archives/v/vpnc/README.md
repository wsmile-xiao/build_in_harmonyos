# vpnc

vpnc 是一个与 Cisco VPN 集中器兼容的 IPSec VPN 客户端，支持多种认证方式和加密算法。

## 功能概述

- 兼容 Cisco VPN Concentrator 3000 Series、Cisco IOS 路由器、Cisco PIX/ASA
- 支持混合认证、预共享密钥 + XAUTH、预共享密钥
- 支持 IKE DH-Groups: dh1, dh2, dh5
- 支持哈希算法: MD5, SHA1
- 支持加密: 3DES, AES128/192/256
- 支持完美前向保密 (PFS): nopfs, dh1, dh2, dh5
- 附带 cisco-decrypt 工具用于解密 Cisco .pcf 文件中的混淆密码

## OHOS 适配

### 适配要点

- **纯 Makefile 构建**：vpnc 没有使用 Autotools 或 CMake，直接使用 Makefile 编译
- **libgcrypt 依赖**：通过 Conan 管理依赖链，AutotoolsToolchain 生成 conanbuild 环境
- **环境变量覆盖**：使用 `make -e` 让 Conan 的 CC、CFLAGS、LDFLAGS 覆盖 Makefile 中的默认值
- **手动安装**：使用 `copy()` 手动安装二进制文件，避免依赖 `install` 命令

### 构建产物

- `sbin/vpnc` — VPN 客户端主程序
- `bin/cisco-decrypt` — Cisco 密码解码器
- `bin/pcf2vpnc` — .pcf 配置文件转换器
- `sbin/vpnc-disconnect` — VPN 断开脚本

## 依赖关系

### 编译依赖

- libgcrypt/1.12.2（传递依赖 libgpg-error/1.55）
- 编译器：clang 15.0 (OHOS SDK)

### 运行依赖

- libgcrypt.so、libgpg-error.so
- TUN/TAP 设备驱动（运行时需要，编译时不需要）

## 参考资料

- 官方主页：https://www.unix-ag.uni-kl.de/~massar/vpnc/
- 源码下载：https://www.unix-ag.uni-kl.de/~massar/vpnc/vpnc-0.5.3.tar.gz

## 版本列表

| 版本 | 状态 | 编译日期 | Conan 引用 |
|------|------|----------|------------|
| [0.5.3](./0.5.3/) | built | 2026-09-04 | vpnc/0.5.3 |

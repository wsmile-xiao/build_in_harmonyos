# openconnect 9.12 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, libtool)
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 (OHOS SDK, /data/service/hnp/bin/clang)
- 平台: HarmonyOS PC aarch64 (本机原生构建, os=OHOS)
- 状态: built

## 依赖
| 包 | 版本 | 角色 |
|---|------|------|
| gnutls | 3.8.10 | SSL/DTLS 后端 (openconnect 默认; 已发布 ohpcd) |
| libxml2 | 2.15.3 | XML 解析 (configure 强制) |
| zlib | 1.3.1 | 压缩 (configure 强制) |

传递依赖 (经 gnutls): nettle/3.10.2.1 libtasn1/4.21.0 libunistring/1.0 gmp/6.3.0 libgcrypt/1.11.0 libgpg-error/1.55 (均已在 ohpcd)。
可选上游特性按缺省禁用 (configure 自动降级, 非阻断): LZ4 (liblz4 无 .pc)、p11-kit、TPM2/tss2、libpsl、libproxy、GSSAPI、libstoken。
OpenSSL 后端未启用 (GnuTLS 为 openconnect 首选且 ohpcd 已发布)。

## 编译步骤 (本地探索, 模式 B Step 2)
```bash
# 依赖经 conan 提供 (PkgConfigDeps 生成 gnutls/libxml-2.0/zlib .pc, AutotoolsToolchain 注入 PKG_CONFIG_PATH)
source <conan-install-dir>/conanbuild.sh
./configure --prefix=/storage/Users/currentUser/usr/local --disable-docs \
            --with-vpnc-script=/etc/vpnc/vpnc-script
make -j2
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-openconnect-9.12
make check        # 5/5 PASS (LD_LIBRARY_PATH 指向依赖 lib 目录后)
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 报 "unable to guess system type" | uname -s=HarmonyOS 不被识别 | config.guess 加 `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos` (patch 0001) |
| 2 | config.sub: "OS `ohos' not recognized" | config.sub 不认识 ohos | config.sub 基本 OS 列表加 `ohos*`, kernel-os 组合加 `linux-ohos*` (patch 0002) |
| 3 | configure 写 conftest 临时文件 Permission denied | HMDFS: umask 077 建的目录继承 setgid 后 `drwx--S---`, 组内进程不可写 | configure 临时目录 `umask 077` → `umask 007` (patch 0003, E011 同款) |
| 4 | mtucalc.c 编译错 "redefinition of 'sockaddr_storage'" | OHOS `<linux/socket.h>` 重定义 musl 版 `<sys/socket.h>` 的结构体 | 4 个含 `<linux/tcp.h>` 的 .c (cstp.c/gpst.c/mtucalc.c/os-tcp-mtu.c) 在 __OHOS__ 下 rename-guard sockaddr_storage (patch 0004-0007, E091/E119 同款) |
| 5 | libtool 链接 libopenconnect.la 失败 "//lib/libgpg-error.la is not a valid libtool archive" | 依赖 conan 包带坏的 .la (libgcrypt.la libdir='//lib'), gnutls 的 .pc 把传递依赖列为公开 Requires 使 libtool 去读 | conanfile generate() 把 PkgConfigDeps 生成的 gnutls.pc 改 `Requires.private`, pkg-config --libs 只吐 -lgnutls, libtool 不再碰 .la |
| 6 | configure 检查 /etc/vpnc/vpnc-script 失败 | 打包环境无该脚本 | `--with-vpnc-script=/etc/vpnc/vpnc-script` 传标准部署路径绕过构建期检查 |

## 源码修改
补丁 7 个 (patches/ 0001-0007, conandata.yml 声明; 由 refresh-patch --auto 经 edit-tracker 生成):
- 0001: config.guess — HarmonyOS 识别 (aarch64:HarmonyOS → linux-ohos)
- 0002: config.sub — ohos/linux-ohos 支持
- 0003: configure — 临时目录 umask 007 (HMDFS setgid 可写)
- 0004-0007: cstp.c/gpst.c/mtucalc.c/os-tcp-mtu.c — OHOS sockaddr_storage rename-guard

## 验证结果
```bash
make check  → 5/5 PASS (autocompletion/lzstest/seqtest/buftest/symbols)
.libs/openconnect --version
  OpenConnect version v9.12-unknown
  Using GnuTLS 3.8.10. Features present: HOTP software token, TOTP software token, System keys, DTLS, ESP
readelf -d libopenconnect.so.5.9.0 → NEEDED libgnutls.so.30 / libxml2.so.16 / libz.so / libintl.so.8 / libc.so
```
上游网络类测试 (server-auth/DTLS/ESP/PPP, 需 test-server/socat/root) 在无网络沙箱自动跳过 — 记录为平台/环境限制, 非代码问题。

## 交付物
- 库: libopenconnect.so.5.9.0 (SONAME libopenconnect.so.5)
- CLI: openconnect (aarch64 OHOS ELF), list-system-keys, os-tcp-mtu
- 头文件: openconnect.h, gnutls.h (经 make install 入库)
- openconnect.pc (Requires.private: zlib gnutls libxml-2.0)

## 注意事项
- openconnect 为命令行工具 + 库混合包: 需 archives/o/openconnect/commands.json (R38, binary=true)
- conan-verify G2 从干净源码 conan create 复现; W3/finish 会再跑 conan create 写 .ci-result.json
- libopenconnect 运行时仍需系统 libz.so/libintl.so (DEFAULT_PREFIX 提供) — 本平台约定, 见 R26 说明
---

**编译结束**: 2026-09-02 19:39
**最终状态**: built

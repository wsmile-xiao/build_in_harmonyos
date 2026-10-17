# shadowsocks-libev

shadowsocks-libev 是 Shadowsocks 协议的 C 实现（基于 libev 事件循环），提供一整套
轻量级加密 SOCKS5 代理工具与静态库 `libshadowsocks-libev`。相比 Python 实现，
它以极低的内存占用与高并发能力支撑同样的加密隧道功能。

## 功能概述

- **ss-local** —— 本地 SOCKS5 客户端，把本地明文流量经加密隧道送往远端
- **ss-server** —— 服务端，解密隧道流量并转发到真实目标
- **ss-tunnel** —— UDP/DNS 隧道转发
- **ss-redir** —— 透明代理（TCP 重定向）
- **ss-manager** —— 多用户/多端口管理
- **libshadowsocks-libev.a** + `shadowsocks.h` + `shadowsocks-libev.pc`

加密套件覆盖 AEAD（`aes-*-gcm`、`chacha20-ietf-poly1305`）与流密码
（`aes-*-cfb/ctr`、`rc4-md5`、`salsa20`、`chacha20`、`chacha20-ietf`）两代算法。

## OHOS 适配

本适配基于官方 **v3.3.5** release 资产，在 HarmonyOS PC (aarch64) 上交叉编译
（profile `ohos-aarch64`，clang 15，三元组 `aarch64-linux-ohos`）。关键适配点
详见 `3.3.5/notes.md`：

- **E007 · `config.sub` 不认 ohos**：上游内置 2020 年的 GNU `config.sub`，
  实测 `configure` 报 ``Invalid configuration `aarch64-linux-ohos': system `ohos'
  not recognized``。配方在 `build()` 内就地插入与版本无关的 fast-path，把含
  `ohos` 的三元组规范化为 `<machine>-unknown-linux-ohos`（幂等，不改配方外文件）。
- **R40 · 必须用 release 资产而非 tag 源码归档**：GitHub tag 源码归档里
  `libcork/`、`libipset/`、`libbloom/` 三个子模块目录为空且不含生成的
  `configure`，用它必须联网 clone 子模块 + `autoreconf`，不可复现；
  官方 release 资产内嵌三者并自带 `configure`。
- **mbedtls 版本约束**：本库硬依赖 mbedtls **v2/v3** 的经典 cipher/md API
  （`src/crypto.h` 无条件 `#include <mbedtls/cipher.h>`，并要求
  `MBEDTLS_CIPHER_MODE_CFB`/`MBEDTLS_GCM_C`；`crypto.c` 调
  `mbedtls_md_info_from_string("MD5")`）。OHOS 制品仓只发布了 `mbedtls/4.1.0`，
  而 4.x 已重构为 TF-PSA-Crypto（`cipher.h` 降为 `mbedtls/private/cipher.h`，
  `md5.h`/`ctr_drbg.h`/`entropy.h` 移除）。故按仓库既有先例
  （`bzrtp/5.3.105`、`librist/2.0.18`、`lib60870/2.4.0`）**就地 vendoring
  mbedtls 2.28.10** 作私有子构建，不新增 conan requirement，也不装入本包。
- **依赖探测形态**：上游 `--with-pcre/sodium/cares/ev/mbedtls=DIR` 只加
  `-I$DIR/include` 与 `-L$DIR/lib`，**不做 pkg-config 探测**，故必须显式喂入
  Conan 依赖的 `package_folder`。

## 测试

上游 `tests/test.sh` → `tests/test.py`（8 组加密套件）**硬依赖公网**
（`curl http://www.google.com/` 经 SOCKS5 + `dig @127.0.0.1 -p1082`），
在离线 CI 与真机环境无法执行；且上游未把测试接入 automake（无 `make check`）。

因此 `test_package` 提供**等价的离线回环**消费者用例：自实现最小 SOCKS5 客户端
+ 内建 HTTP 源站，驱动包内**真实的** `ss-server`/`ss-local` 可执行文件，
逐字节校验隧道载荷。覆盖 4 个代表加密套件（AEAD 与流密码两条路径），
不依赖公网、DNS、curl、dig 或 python。

本地实测（qemu 执行 aarch64 产物）：

```
conan exit=0
  [PASS] SOCKS5 tunnel round-trip  aes-256-gcm (payload matched)
  [PASS] SOCKS5 tunnel round-trip  chacha20-ietf-poly1305 (payload matched)
  [PASS] SOCKS5 tunnel round-trip  aes-256-cfb (payload matched)
  [PASS] SOCKS5 tunnel round-trip  rc4-md5 (payload matched)
E2E summary: 4 passed, 0 failed (ciphers=4)
```

## 依赖关系

| 依赖 | 版本 | 来源 |
|------|------|------|
| pcre | 8.45 | conan（ohpcd） |
| libev | 4.33 | conan（ohpcd） |
| libsodium | 1.0.22 | conan（ohpcd） |
| c-ares | 1.34.6 | conan（ohpcd） |
| mbedtls | 2.28.10 | 就地 vendoring（私有子构建） |

## 参考资料

- 上游仓库: https://github.com/shadowsocks/shadowsocks-libev
- 源码: https://github.com/shadowsocks/shadowsocks-libev/releases/download/v3.3.5/shadowsocks-libev-3.3.5.tar.gz
- 许可证: GPL-3.0-or-later

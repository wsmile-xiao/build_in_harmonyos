# shadowsocks-libev 3.3.5 适配笔记

## 编译环境
- 构建系统: autotools（上游自带生成的 `configure`）
- 编译日期: 2026-09-30
- 编译器: clang 15（OHOS 6.0 SDK 交叉工具链
  `aarch64-unknown-linux-ohos-clang`，profile `ohos-aarch64`）
- 三元组: `aarch64-linux-ohos`
- 状态: built（本地 ohos-aarch64 交叉构建通过；**上游 tests/test.py 真实执行 8/8 通过**；
  test_package 端到端回环 4/4 通过）
- **真机验证：DAYU200-RK3568（润和）· OpenHarmony 6.0.0.47 aarch64 上端到端回环 4/4 通过**
  （证据见 `device-evidence/`，含 `_device_evidence.json` 与完整输出）

## 编译步骤

```bash
# 1. 取官方 release 资产（内嵌 libcork/libipset/libbloom 三个子模块）
curl -L -o shadowsocks-libev-3.3.5.tar.gz \
  https://github.com/shadowsocks/shadowsocks-libev/releases/download/v3.3.5/shadowsocks-libev-3.3.5.tar.gz
# sha256: cfc8eded35360f4b67e18dc447b0c00cddb29cc57a3cec48b135e5fb87433488

# 2. 就地 vendoring mbedtls 2.28.10（制品仓只有 4.1.0，API 不兼容）
curl -L -o mbedtls-2.28.10.tar.gz \
  https://github.com/Mbed-TLS/mbedtls/archive/refs/tags/mbedtls-2.28.10.tar.gz
# sha256: c785ddf2ad66976ab429c36dffd4a021491e40f04fe493cfc39d6ed9153bc246
#   由 conanfile.py source() 完成，装到 source_folder/vendor/mbedtls-2.28.10

# 3. 交叉构建（由 conan 驱动，profile 提供 CC/AR/sysroot）
conan create . -pr:h=ohos-aarch64 -pr:b=default

# 4. 本地执行端到端回环（qemu）
OHOS_RUN_EMULATOR=<qemu wrapper> conan test test_package shadowsocks-libev/3.3.5 \
  -pr:h=ohos-aarch64-run -pr:b=default
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 直接失败：`Invalid configuration 'aarch64-linux-ohos': system 'ohos' not recognized` | 上游内置 2020 年的 GNU `config.sub`，其 kernel-OS 白名单没有 `ohos` | `build()` 内对 `source_folder` 里所有 `config.sub` 就地插入与版本无关的 fast-path（凡含 `ohos` 的三元组一律规范化为 `<machine>-unknown-linux-ohos` 并 `exit 0`），幂等且不碰易碎的内核 OS 表（E007） |
| 2 | 用 GitHub tag 源码归档构建不可复现：`libcork/`、`libipset/`、`libbloom/` 三个目录为空 | `git archive` 不含 submodule 内容，且归档里没有生成的 `configure`，必须联网 clone 三个子模块 + `autoreconf` | 改用**官方 release 资产**：内嵌三个子模块（191 个条目）且自带 `configure`，可离线复现（R40） |
| 3 | `configure` 报 `mbed TLS libraries not found.` → 补上 `--with-mbedtls` 后又报 `'mbedtls/cipher.h' file not found` | 上游 `ss_MBEDTLS` 用 `AC_CHECK_LIB(mbedcrypto, mbedtls_cipher_setup)` 硬探测，且 `src/crypto.h` 无条件 `#include <mbedtls/cipher.h>`/`<mbedtls/md.h>`；而制品仓只发布 `mbedtls/4.1.0`，4.x 已改 TF-PSA-Crypto：`cipher.h` 降为 `mbedtls/private/cipher.h`，`md5.h`/`ctr_drbg.h`/`entropy.h` 移除 | 按仓库既有先例（bzrtp/5.3.105、librist/2.0.18、lib60870/2.4.0）**就地 vendoring mbedtls 2.28.10**（最后一条保留完整经典 cipher API 的 LTS），在 `build()` 里用同一份 `conan_toolchain.cmake` 子构建成私有静态库，再 `--with-mbedtls=<prefix>` 喂给 configure。不新增 conan requirement，私有前缀不装进本包 |
| 4 | `conan_toolchain.cmake missing`（私有 mbedtls 子构建时） | `AutotoolsToolchain` 只产出 `conanbuild` 环境脚本，不产出 CMake 工具链文件 | 在 `_build_private_mbedtls()` 内显式再生成一份 `CMakeToolchain`（与 bzrtp/5.3.105 内嵌 mbedtls 的做法一致） |
| 5 | `configure` 报 `The Sodium crypto library libraries not found.` / `Couldn't find libev.` | 上游 `ss_SODIUM`/`ss_CARES`/`ss_MBEDTLS` 的 `--with-<dep>=DIR` 只加 `-I$DIR/include` 与 `-L$DIR/lib`，**不做 pkg-config 探测**，Conan 依赖不显式喂入就找不到 | 在 `generate()` 里用 `self.dependencies[name].package_folder` 生成 `--with-pcre/sodium/cares/ev=<prefix>`；`libev` 只有 `--with-ev=DIR` 单一变体 |
| 6 | `tests/` 目录在本配方采用的 release 资产里**根本不存在** | 上游 release 流程 dist 时未打包 `tests/`；`tests/test.sh`、`tests/test.py` 与 8 个 JSON 只存在于 GitHub **tag 源码归档**（顶层目录 `shadowsocks-c-3.3.5`） | 见下方 #8：真实执行上游测试改为从 tag 归档取 `tests/`，落地为 `upstream-tests/run_upstream_tests.sh` |
| 12 | 真机编译 `src/netutils.c` 等：`linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'`（`sys/socket.h:377` 已定义过） | 上游 `src/netutils.h` 在 `HAVE_LINUX_TCP_H` 分支 `#include <linux/tcp.h>`，而它又拉入 `<linux/socket.h>`；真机 SDK 的 `<sys/socket.h>` **无条件**定义了 `sockaddr_storage`，两边撞车。本地 WSL 的 OHOS SDK 是 musl 风格：`sys/socket.h` 里该结构体被 `#ifndef __MUSL__` 包住，而 OHOS 工具链预定义了 `__MUSL__`，故走 `#include <linux/socket.h>` 分支、自己不定义 —— 冲突不存在。又一处只在真机口径暴露的差异 | 新增 `patches/ohos-netfilter-shim/ohos_sockaddr_compat.h`，用 `-include` 在一切之前预先置上 `<linux/socket.h>` 的 include guard（`_UAPI_LINUX_SOCKET_H`），使其不再重复定义；`<linux/tcp.h>` 仍从 `<sys/socket.h>` 拿到完整类型，语义等价。仅在 `settings.os == OHOS` 时注入，Linux 目标行为不变。仓库同类先例：x/haproxy、x/hashrat、x/nftables |
| 11 | 真机原生构建 configure 最后一步：`./config.status: line 822: ./confnDjInI/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery` | autoconf 生成的 config.status 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录（本库 configure 第 17512/17517 行），在 OHOS 的 HMDFS 上目录被强制继承 setgid 位，实际变成 `drwx--S---`，连属主都无法写入 subs1.awk，config.status 中止（本仓库 已知通用问题 **E011**） | `build()` 内把所有 configure 的 `umask 077` 改写为 `umask 022`（连同 x 位一起保留），config.status 由 configure 模板生成因此同步生效。仓库先例：x/xqilla、x/xcursorgen、x/xcb-util-renderutil、x/xapian-bindings、x/xz |
| 10 | CI/真机**原生**构建时 `configure: error: cannot guess build type; you must specify one`（`uname -s = HarmonyOS`） | 真机 `uname -s` 返回 `HarmonyOS`（不是 `Linux`），上游 2018 版的 `config.guess` 探测表里没有该 system 名，直接 "unable to guess system type"。CI/真机是**原生**构建，`AutotoolsToolchain` 不会传 `--build`，configure 只能自己猜 build type，猜不出即报错。**本地 WSL 交叉构建（`--build=x86_64-linux-gnu` 由 conan 显式提供）永远走不到这条分支**，所以本地全绿、CI 才暴露 | 把 E007 的补丁从只覆盖 `config.sub` 扩展为同时覆盖 `config.guess`：同样在 shebang 后插入与版本无关的 fast-path，凡 `uname -s` 为 HarmonyOS/OHOS 就输出 `<machine>-unknown-linux-ohos` 并 `exit 0`。两处补丁都幂等（按 marker 跳过）|
| 9 | CI（CMake 4.x）配置 vendoring 的 mbedtls 失败：`CMake Error at CMakeLists.txt:23 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed from CMake.` | mbedtls 2.28.10 的 `CMakeLists.txt` 写的是 `cmake_minimum_required(VERSION 2.8.12)`；CI/真机的 CMake 4.x 已移除对 <3.5 的兼容。**本地 WSL 的 cmake 是 3.28，不会报错**——这是一个只在真机口径暴露的差异 | 给私有 mbedtls 子构建加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 官方迁移开关，不改上游源码，正是报错信息给出的建议）。仓库内已有大量先例：`archives/x/xerces`、`archives/x/xxhash`、`archives/x/xtl`、`archives/x/xenium` |
| 8 | 上游 `tests/test.py` 默认打公网（`http://www.google.com/` + `8.8.8.8:53`），离线不可执行 | 上游把目标做成了命令行参数（`--url` / `--dns`），但 `test.sh` 用的是默认值 | **不改上游任何一行测试代码**，只用 `--url` 指向本机 origin（`python3 -m http.server`）即可离线真实执行；`ss-*` 经 qemu wrapper 落到 PATH 供 `test.py` 的 `Popen` 调用；`ss-*` 唯一的动态依赖 `libev.so` 放进 OHOS 运行根。实测 **8/8 全通过**（含 `dig @127.0.0.1 -p1082` 的 DNS 隧道段，status: NOERROR） |
| 7 | 上游无 `make check` | `Makefile.am` 未把 `tests/` 接入 automake（无 `TESTS`/`check_PROGRAMS`/`check-local`） | 配方用 `Autotools(self).configure()/make()`，测试由 `test_package` 承担（`test_package/MANIFEST.yml` 有完整审计） |

## 源码修改（补丁）

- **无静态补丁文件**（`patches/` 为空）。唯一的源码改动是 E007 的
  `config.sub` 三元组 fast-path，在 `build()` 内就地幂等写入，不改配方外任何文件。
- 未修改上游任何测试用例（`tests/` 原样保留，未改动、未删除）。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| pcre | 8.45 | conan（ohpcd） | configure 硬依赖（`TS_CHECK_PCRE` 失败即 `AC_MSG_ERROR`） |
| libev | 4.33 | conan（ohpcd） | 事件循环，`--with-ev=DIR` |
| libsodium | 1.0.22 | conan（ohpcd） | 现代 AEAD（chacha20-poly1305 等） |
| c-ares | 1.34.6 | conan（ohpcd） | 异步 DNS，`ss-tunnel`/`ss-server` 远端解析 |
| mbedtls | **2.28.10** | **就地 vendoring** | 制品仓仅 4.1.0（TF-PSA-Crypto，API 不兼容），私有子构建，不装入本包 |

内嵌子模块（随源码包提供，不需要外部依赖）：
`libcork`、`libipset`、`libbloom` —— 上游用自带的 `Makefile.am` 包装成静态
libtool 库，**不调用**它们各自的 `CMakeLists.txt`，故构建无需 CMake。

## 验证结果

本地 `ohos-aarch64` 交叉构建 + qemu 执行 `test_package` 端到端回环：

```
conan exit=0
shadowsocks-libev/3.3.5: Package '21e2f402784ecf1ae1ced3ce6d0c018bc5fea8d3' created

======== Testing the package: Executing test ========
  [PASS] SOCKS5 tunnel round-trip           aes-256-gcm (payload matched)
  [PASS] SOCKS5 tunnel round-trip           chacha20-ietf-poly1305 (payload matched)
  [PASS] SOCKS5 tunnel round-trip           aes-256-cfb (payload matched)
  [PASS] SOCKS5 tunnel round-trip           rc4-md5 (payload matched)

E2E summary: 4 passed, 0 failed (ciphers=4)
```

### 真机验证（DAYU200 · rule12）

设备：润和 DAYU200-RK3568 · OpenHarmony 6.0.0.47 (API20, aarch64, 64bit)

把 `test_package/test_shadowsocks_e2e.c` 编译成**静态**二进制（设备无运行库
依赖），连同包内真实 `ss-local`/`ss-server`/`ss-tunnel` 与它们唯一的动态依赖
`libev.so` 一起推送到设备执行：

```
$ sh run_on_device.sh

=== env ===
Linux localhost 6.6.101 #1 SMP Mon Sep 28 19:29:42 CST 2026 aarch64
=== run consumer e2e ===
  [PASS] SOCKS5 tunnel round-trip           aes-256-gcm (payload matched)
  [PASS] SOCKS5 tunnel round-trip           chacha20-ietf-poly1305 (payload matched)
  [PASS] SOCKS5 tunnel round-trip           aes-256-cfb (payload matched)
  [PASS] SOCKS5 tunnel round-trip           rc4-md5 (payload matched)

E2E summary: 4 passed, 0 failed (ciphers=4)
__RC__=0
```

`_device_evidence.json`：`exit_code: 0`，`system: OpenHarmony 6.0.0.47`。
真机结果与 qemu（CI 门禁口径）一致。

### 上游测试套件真实执行（`upstream-tests/run_upstream_tests.sh`）

**直接运行上游 `tests/test.py`**（未修改其任何一行），8 个上游配置全通过：

```
$ bash upstream-tests/run_upstream_tests.sh <conan package 目录>

  [PASS] tests/aes.json
  [PASS] tests/aes-gcm.json
  [PASS] tests/aes-ctr.json
  [PASS] tests/rc4-md5.json
  [PASS] tests/salsa20.json
  [PASS] tests/chacha20.json
  [PASS] tests/chacha20-ietf.json
  [PASS] tests/chacha20-ietf-poly1305.json

UPSTREAM_RESULT: 8/8 passed, 0/8 failed
```

每个配置都跑完整链路：`ss-server` + `ss-local` + `curl --socks5-hostname`
经加密隧道取回 origin 内容，再 `dig @127.0.0.1 -p1082` 走 `ss-tunnel` 解析
DNS（输出 `status: NOERROR`）。仅把 `--url` 由 `http://www.google.com/`
换成本机 origin（离线环境的必然要求），`--dns` 段与解析链路保持上游原样。

产物（package 目录）：

```
bin/ss-local  bin/ss-server  bin/ss-tunnel  bin/ss-manager  bin/ss-redir
lib/libshadowsocks-libev.a
include/shadowsocks.h
lib/pkgconfig/shadowsocks-libev.pc
```

架构确认（`llvm-readelf -h`）：`ELF64` / `AArch64`。

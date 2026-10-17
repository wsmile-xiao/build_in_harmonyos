# libkcapi-tools

Linux 内核 crypto API（AF_ALG）用户态命令行工具集，取自 [libkcapi](https://github.com/smuellerDD/libkcapi) 上游 `apps/` 目录的四个工具：

| 工具 | 功能 |
| --- | --- |
| `kcapi-dgst` | 消息摘要 / HMAC / PBKDF2（stdin → stdout） |
| `kcapi-enc` | 对称加解密（AES-CTR/GCM/XTS 等内核 skcipher 与 AEAD） |
| `kcapi-rng` | 从内核 DRBG 读取随机数 |
| `kcapi-hasher` | FIPS 风格校验和工具（md5sum/sha*hmac/openssl 风格同名链接语义） |

## 本仓库适配版本

| 版本 | conan 包 | 状态 | 说明 |
| --- | --- | --- | --- |
| 1.5.0 | `libkcapi-tools/1.5.0` | built | 与 `libkcapi/1.5.0` 同源，仅发行 4 个工具二进制 |

## OHOS 适配要点

- **同源自包含子包**：上游 Makefile.am 将每个工具静态链接到 in-tree `libkcapi.la`，本包构建出的二进制 `DT_NEEDED` 仅 `libc.so`，因此配方不 `requires libkcapi`（先例：`libfreeaptx-tools`）。
- **补丁**：与 base 包共用同一组修复思路——
  - `0001`：OHOS SDK 内核 UAPI 头 `linux/socket.h` 与 musl `sys/socket.h` 的 `sockaddr_storage` 重定义冲突（E091），在 include `<linux/netlink.h>` 期间重命名内核侧 typedef（**无条件宏守卫**，规避 R8 平台宏禁令，glibc 下为无害 no-op，已在 aarch64-linux-ohos 上实测编译）；
  - `0002`：musl 严格模式 `bool` 冲突，改 `apps/app-internal.h`（工具直接相关）与 `lib/internal.h`。
- **Bootstrap**：GitHub tag 包不含 `configure`，需 aclocal → libtoolize → autoconf → automake 自举（勿用 autoreconf，OHOS HMDFS 下有 autoconf.m4f 宏冲突）；`tool_requires automake/1.18 + libtool/2.5.4`。
- **configure 陷阱**：HMDFS 下 `mktemp -d` 恒 0700 导致 config.status EPERM，配方内替换为 `umask 000 && mkdir`；`ac_cv_path_OPENSSL=` 阻止构建机 openssl 探测开启 FIPS `.hmac` 安装钩子。
- **运行时限制**：OHOS SELinux 策略拒绝非特权进程 `bind(AF_ALG)`，工具的 `--version`/`-v`/`--help` 均可用（纯用户态 `kcapi_versionstring()` API），但真实加解密/摘要/取随机数操作返回 EPERM——这是平台能力限制，非构建缺陷（base 包 `libkcapi/1.5.0` notes 同型结论）。

## 目录结构

- `commands.json` — 工具入口清单（type: tool, binary: true）
- `1.5.0/` — conan 配方、补丁、test_package 与构建笔记

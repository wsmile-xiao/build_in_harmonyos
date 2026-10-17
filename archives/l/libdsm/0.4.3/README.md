# libdsm 0.4.3 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64) 的 conan 包。libdsm 是极简 SMB1/SMB2 只读
客户端库（NetBIOS 名字服务 + SMB 会话/文件/目录访问，SPNEGO/NTLM 认证）。

> 上游 0.4.3 为 **meson** 构建（非早期版本的 autotools）；真实依赖是
> **libtasn1**（SPNEGO ASN.1 解析）+ threads + libc iconv（musl 原生），
> **不含 zlib**。spnego_asn1.c 由构建时 asn1Parser 生成（tool_requires
> libtasn1/4.21.0 提供工具）。

## 出包（鸿蒙 PC 本机）

```bash
conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=2
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验。

## 适配要点（详见 notes.md）

- `c_std=gnu11` + native file `c_args=['-D_GNU_SOURCE']`：meson.build 对非
  linux/darwin 系统统一加 `-D_POSIX_C_SOURCE=200809L`，严格方言下 musl 不声明
  strlcpy；注入 `_GNU_SOURCE` 后声明全可见（零源码 patch）。
- `-Dbinaries=false`：关闭 bin/ 下 4 个示例工具（需真实 SMB 服务器/局域网），
  纯库包形态，无 commands.json。
- `-Dwrap_mode=nodownload`：依赖一律走 conan。
- iconv：OHOS musl libc 原生自带（实测 iconv_open OK），无第三方依赖。
- ELF 签名：`package()` 重签 `lib/**/*.so`（XPM 要求，本仓通行手法）。

## 消费 A：conan 工程

```bash
conan install --requires=libdsm/0.4.3 -pr ohos-aarch64
```

生成 `libdsm-config.cmake` / `libdsm.pc`；`find_package(libdsm)` 消费。

头文件布局：`<bdsm.h>` 聚合头（含 bdsm/netbios_ns.h、bdsm/smb_session.h 等）。

## 消费 B：裸程序（设备 ~/usr/local）

```bash
conan install --requires=libdsm/0.4.3 -pr ohos-aarch64 \
    --deployer=usr_local --deployer-folder=$HOME/usr/local
```

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "libdsm/0.4.3:*" --file libdsm.tgz
conan cache restore libdsm.tgz
```

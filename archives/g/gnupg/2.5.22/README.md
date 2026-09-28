# gnupg 2.5.22 — 鸿蒙 PC conan 制品

GnuPG（OpenPGP 实现）：提供 `gpg` / **`gpgv`** / `gpgsm` / `gpg-agent` 等。

> **`gpgv`** 是 apt 的 Release 签名验证实际使用的工具，也是本包适配的主因。

## 出包（鸿蒙 PC）

```bash
conan create archives/g/gnupg/2.5.22 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## ⚠️ 前置依赖（重要）

gnupg 2.5.22 的 `configure.ac` 要求 **`NEED_GPGRT_VERSION=1.56`**（libgpg-error ≥ 1.56），
而 ohpcd 现存 libgpg-error 仅为 **1.55**。

→ 必须先合入并发布 **`libgpg-error/1.61`**（本目录同批次分支 `feat/libgpg-error-1.61`），
本 PR 的 CI 才能通过。

另注：`libgcrypt/1.12.2` 与 `1.11.0` 的配方**硬钉 `libgpg-error/1.55`** → 与本包要求的
1.61 产生 conan 图版本冲突，故本配方用 `self.requires("libgpg-error/1.61", override=True)`
强制全图统一（libgpg-error 1.x 保持 ABI 稳定，soname 仍为 `libgpg-error.so.0`）。

## OHOS 适配要点（均为实测踩坑）

| # | 措施 | 原因 |
|---|------|------|
| 1 | `config.guess` / `config.sub` 的 HarmonyOS patch | 2.5.22 上游**不含** ohos 支持（`grep -c ohos` = 0）；用仓库 `scripts/patch-autotools-ohos.pl` 生成 |
| 2 | **`config.sub` 的 kernel-os 白名单加 `linux-ohos*`** | 仅改 os 识别不够：configure 报 `Kernel 'linux' not known to work with OS 'ohos'` —— 必须把 `linux-ohos*` 加进 `linux-gnu* \| linux-android* \| ...` 那一行 |
| 3 | `0003-configure.patch`：`*-linux-ohos*` 走 android 分支 | 该分支设 `require_iconv=no`，避免对 libiconv 的强依赖（main 上 2.4.9 的 notes 记录其失败于 libiconv 运行时链接问题） |
| 4 | `0003-configure.patch`：`umask 077` → `022` | configure 内 `mktemp -d ./confXXXXXX` 用 077，HMDFS 上导致临时文件权限异常 |
| 5 | **显式 `GPGRT_CONFIG` + 依赖 bin 目录前置 PATH** | libgpg-error **1.56+ 已移除 `gpg-error-config`**，只剩 `gpgrt-config`；而 `--with-libgpg-error-prefix` 只按约定拼出 `$prefix/bin/gpg-error-config`（不校验存在性）→ configure 拿到不存在的路径、真正的 `gpgrt-config` 又不在 PATH → `GPGRT_CONFIG=no` → 报 `You need libgpg-error` |
| 6 | **依赖的 `lib/pkgconfig` 前置 `PKG_CONFIG_PATH`** | `npth` 的 conan 包**不提供 `bin/npth-config`**（只有 `npth.pc`）；gnupg 的 `m4/npth.m4` 会回退到 `$GPGRT_CONFIG npth`（gpgrt-config 代查 `npth.pc`），该回退要求 gpgrt-config 能经 `PKG_CONFIG_PATH` 找到它 |
| 7 | **`extra_cflags`/`extra_ldflags` 注入依赖真实 include/lib** | libgpg-error 的 `.pc` 中 `prefix=/`（conan `--prefix=/` 约定）→ gpgrt-config 输出 `-I//include` 与 `-L//lib -lgpg-error`，编译报 `fatal error: 'gpg-error.h' file not found`。gnupg 的 m4 宏**不提供** CFLAGS/LIBS 环境变量覆盖入口，故在工具链层补齐真实路径（`-I//include` 无害） |
| 8 | `--with-{libgpg-error,libgcrypt,libassuan,ksba,npth}-prefix` | gnupg 的 `AM_PATH_*` 宏不会自动在 conan 缓存里找依赖 |
| 9 | 收窄依赖面 | `--disable-{all-tests,doc,card-support,ccid-driver,ldap,libdns,gnutls,ntbtls,sqlite,selinux-support,rpath,nls}` —— 免 libusb / TLS 栈 / sqlite 等 |

## 测试

`test_package/test_gnupg.sh` **真实执行** `gpgv --version` 与 `gpg --version` 并断言版本号
`2.5.22`（R34 反空壳，非仅存在性断言）。实测输出：

```
OK: gpgv --version → gpgv (GnuPG) 2.5.22
OK: gpg --version → gpg (GnuPG) 2.5.22
gnupg test_package PASS (2.5.22)
```

> ⚠️ test_package 必须用 `env="conanrun"`：`gpgv` 为动态链接可执行文件，运行时需
> `LD_LIBRARY_PATH` 带上依赖 lib 目录，否则报
> `Error relocating .../bin/gpgv: gpgrt_vasprintf: symbol not found` 等一长串符号缺失。

上游测试以 `--disable-all-tests` 关闭（gnupg 的 `tests/` 为需要完整环境的集成测试）。

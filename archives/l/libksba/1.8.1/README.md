# libksba 1.8.1 — 鸿蒙 PC conan 制品

libksba = **X.509 / CMS / S/MIME 证书与签名解析库**，GnuPG 组件之一
（gnupg 链：`libgpg-error` → `libksba`）。

## 出包（鸿蒙 PC）

```bash
conan create archives/l/libksba/1.8.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 源

```
https://gnupg.org/ftp/gcrypt/libksba/libksba-1.8.1.tar.bz2
sha256 c2f84393011827219ae117131dba8e7684c2bed0961eed11b0642c2acba440b5   (722040 字节)
```

> 与 `1.6.7.1` 的区别：**1.8.1 是上游真实发行版**；而 `1.6.7.1` 是版本映射（实际打的是 `libksba-1.6.7.tar.bz2`）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| **libgpg-error** | **1.55** | ✅ **1.55 即足够** —— 1.8.1 只要求 `NEED_GPG_ERROR_VERSION=1.28`（实测 `configure.ac:61`），低于 ohpcd 现存的 1.55 |

> ⚠️ **不要按"同族统一抬升"推断**：gnupg 2.5.22 要求 libgpg-error ≥ **1.56**（需 1.61），
> 但 libksba 1.8.1 只要 **1.28**。gpg-error 系各库的最低版本要求须**逐库从 `configure.ac` 读取**。

## OHOS 适配要点

| # | 措施 | 原因 |
|---|------|------|
| 1 | **`--build/--host=aarch64-unknown-linux-musl`** | ① 设备 HMDFS 上 `config.guess` 的 mktemp 探针写 `dummy.c` 报 Permission denied（"unable to guess system type"）；② **1.8.1 的 `config.sub` 仍不识别 `linux-ohos`**（实测 `Invalid configuration ... OS 'ohos' not recognized`），但**自带 `linux-musl` 分支**（实测 `config.sub aarch64-unknown-linux-musl` 通过）→ **用 musl triplet 显式指定即可，无需 patch `config.sub`**<br>（对比：**gnupg 2.5.22 必须补 `config.sub` 的白名单**）|
| 2 | **`gpgrt-config` 而非 `gpg-error-config`** | libgpg-error **1.56+ 已移除** `gpg-error-config`，只剩 `gpgrt-config`。`gpg-error.m4` 用 `AC_PATH_PROG` 在 **PATH** 上找 → 须把 libgpg-error 的 `bin` 加入 PATH；而 `--with-libgpg-error-prefix` 按约定拼出的 `$prefix/bin/gpg-error-config` **并不存在** |
| 3 | **`CPPFLAGS`/`LDFLAGS` 兜底** | `gpgrt-config --cflags` 输出**为空**（`includedir` 按烤死的 `/` 算成标准路径）→ 编译找不到 `gpg-error.h`；直接补 libgpg-error 的 include/lib（autoconf 会烤进 Makefile）|
| 4 | `TMPDIR` 指向 conan build 目录 | 设备默认 TMPDIR 在 HMDFS 上写临时文件失败 |
| 5 | `configure` 内 `umask 077` → `022` | HMDFS 上会产生 0600 成员的归档目录，install 阶段可读性不稳 |

## 测试

- **上游测试**：`make check` **实跑通过** —— **7 个**测试二进制
  （`cert-basic` / `t-crl-parser` / `t-dnparser` / `t-oid` / `t-reader` / `t-cms-parser` / `t-der-builder`），
  sample 数据随源码包分发。在 `build()` 内执行（`--disable-static` 不影响）。
- **test_package**：`dlopen` 加载 `libksba.so` + `dlsym` 解析**真实导出符号**
  （`ksba_cert_new` / `ksba_cert_release`），R34 反空壳。

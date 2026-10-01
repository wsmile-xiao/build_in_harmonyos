# libgpg-error 1.61.1 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64) 的 conan 包，支持两种消费形态。

libgpg-error 是 **GnuPG 全系的错误码基座**（gnupg / libassuan / libksba / npth /
pinentry 均依赖它），也是 apt 满血依赖链（签名验证 `gpgv`）的上游基座。

> **版本说明（R37）**：1.61.1 为 1.61 的**适配版本迭代** —— 上游源码仍使用
> libgpg-error-1.61 官方 tarball（1.61 的适配方案已在 main 合入并发布 ohpcd），
> 仅以版本号后缀区分适配修复（cnb.cool 制品仓不支持同版本多 recipe revision 并存）。

## 出包（鸿蒙 PC）

```bash
conan create archives/l/libgpg-error/1.61.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

> 源码由 `conandata.yml` 的官方 URL（libgpg-error-1.61 tarball）在 `conan create`
> 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。

## OHOS 适配要点

| # | 措施 | 原因 |
|---|------|------|
| 1 | `--build=aarch64-unknown-linux-musl` + `--host=aarch64-unknown-linux-musl` | 设备 HMDFS 上 `config.guess` 的 mktemp 探针写 `dummy.c` 报 `Permission denied`（"unable to guess system type"）→ configure 中止。显式给出可直接跳过 config.guess。<br>**且 build==host → 原生模式**（非 cross），libgpg-error 会跑 `gen-posix-lock-obj` 探针按设备**真实 musl 尺寸**生成 lock-obj，而非误用 glibc 预置头 —— 后者会导致后续 gnupg 链运行期 pthread 锁尺寸不匹配。 |
| 2 | `TMPDIR` 指向 conan build 目录 | 设备默认 `TMPDIR` 在 HMDFS 上，config.guess / conftest 写临时文件失败。 |
| 3 | `configure` 内 `umask 077` → `022` | HMDFS 上 077 会导致临时文件权限问题。 |
| 4 | 关闭 `USE_POSIX_THREADS_WEAK` | gnulib `threadlib.m4` 的 `gl_pthread_in_glibc` 只认 glibc，把 musl 误判为「需 `-lpthread`」→ 定义 `USE_POSIX_THREADS_WEAK`；musl 下 pthread 在 libc 内，该 weak 引用不声明 `pthread_cancel` → 编译报 `use of undeclared identifier 'pthread_cancel'`。去掉该定义后回退 `use_pthread_p()=(1)`。 |
| 5 | 保留 `config.guess`/`config.sub` 的 HarmonyOS patch | 双重保障：即使某环境未走 `--build/--host` 路径，config.guess 也能识别 HarmonyOS（生成 `aarch64-unknown-linux-ohos`）。 |

### 关于 patch 导出（易踩的坑）

`patches/` **必须经 `export_sources()` 导出**，否则 `build()` 里
`apply_conandata_patches()` 会报：

```
FileNotFoundError: .../s/patches/0001-build-aux-config.guess.patch
```

本配方用 `export_conandata_patches(self)`（与 npth 1.8 一致）。

## .so 签名

**签名默认关**：本 recipe 的 `package()` 不自签 `.so`，靠链接器自签（构建时 clang
直接产出有效自签 ELF，无需事后重签）。

## 测试

- **test_package（鸿蒙特有，R34 反空壳）**：`dlopen` 真实加载 `libgpg-error.so`，
  `dlsym` 解析并**实际调用**被测库 API —— `gpg_strerror(0)`→`'Success'`、
  `gpg_strsource(ANY)`→`'Unspecified source'`、`gpg_error_check_version(NULL)`
  （gpgrt/gpg-error 版本 API）→`'1.61'`。实测输出：
  ```
  libgpg-error: gpg_strerror(0)='Success' ok
  libgpg-error: gpg_strsource(ANY)='Unspecified source' ok
  libgpg-error: gpg_error_check_version()='1.61' ok
  ```
- 上游测试：以 `--disable-tests` 关闭（其为 gpg-error 自检工具，非独立测试框架）；
  但已按 R51 三步法在**不加 --disable-tests** 的真实构建中运行 `make check`，
  15 项中 14 项通过（93.3%），唯一失败 `t-argparse` 为测试宿主 UID 不在
  `/etc/passwd` 的环境限制（非库缺陷）—— 逐项明细见 `reports/test-report.md`。

## 版本关系

1.61.1 与 1.61 唯一差异为版本号后缀（R37 迭代）；适配方案与 1.61（main 已合入并
发布 ohpcd）完全一致。1.61 与 1.55 接口无变化，故整体沿用 1.55 已验证的构建方案。

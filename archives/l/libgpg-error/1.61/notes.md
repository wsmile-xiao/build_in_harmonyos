# libgpg-error 1.61 适配笔记（OHOS / 鸿蒙 PC）

## 编译环境
- 构建系统: autotools
- 适配日期: 2026-09-11
- 编译器: clang / clang++ (clang15, libc++)
- 目标: os=OHOS, arch=armv8 (aarch64), Release
- 状态: built（本地 `conan create` EXIT=0，test_package PASS）

## 源码
- URL: `https://gnupg.org/ftp/gcrypt/libgpg-error/libgpg-error-1.61.tar.bz2`
- sha256: `7a85413f2bc354f4f8aa832b718af122e48965e9e0eb9012ee659c13c6385c93`
- 说明：本版本为 1.55 的同族版本升级（接口无变化），沿用 1.55 已在 main 并发布 ohpcd 的构建方案。

## 编译步骤
1. `get()` 下载官方 tarball 并校验 sha256
2. `export_sources()` 导出 `patches/`（**必需**，否则 `apply_conandata_patches` 找不到文件）
3. `apply_conandata_patches()` 应用 config.guess / config.sub 的 HarmonyOS patch
4. `TMPDIR` 指向 conan build 目录；configure 内 `umask 077` → `022`
5. configure：`--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl --disable-nls --disable-doc --disable-tests --disable-static`
6. 关闭 `USE_POSIX_THREADS_WEAK`（musl 误判修正）
7. `make -j1` → `install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 不识别 OHOS → "unable to guess system type" | ① OHOS 不在 autoconf 支持列表；② 设备 HMDFS 上 mktemp 探针写 `dummy.c` 报 Permission denied | 显式 `--build/--host=aarch64-unknown-linux-musl` 跳过 config.guess（并保留 config.guess patch 作双保险）|
| 2 | `config.sub` 不识别 OHOS | 同上 | patch config.sub（`ohos*` / `linux-ohos*` 分支）|
| 3 | conftest / 临时文件写入失败 | 设备默认 `TMPDIR` 在 HMDFS 上 | `TMPDIR` 指向 conan build 目录 |
| 4 | 临时文件权限异常 | configure 内 `umask 077` 在 HMDFS 上行为异常 | 改为 `umask 022` |
| 5 | 编译报 `use of undeclared identifier 'pthread_cancel'` | gnulib `threadlib.m4` 的 `gl_pthread_in_glibc` 只认 glibc，把 musl 误判为需 `-lpthread` → 定义 `USE_POSIX_THREADS_WEAK`；musl 的 pthread 在 libc 内，weak 引用不成立 | 去掉 `config.h` 的 `USE_POSIX_THREADS_WEAK` 定义（回退 `use_pthread_p()=(1)`）|
| 6 | `FileNotFoundError: .../s/patches/0001-...patch` | `patches/` 未经 `export_sources()` 导出 | 加 `export_sources()` + `export_conandata_patches(self)`（同 npth 1.8）|

## 为什么必须 build == host（重要）

libgpg-error 的 `src/lock-obj-pub.*.h` 是**平台相关的锁尺寸定义**。以 cross 模式构建时，
configure 会走 `force_use_syscfg=yes`（套用**预置**的 glibc 头）；而 `--build == --host`
时为原生模式，会实际运行 `gen-lock-obj.sh` 探针，按**设备真实 musl** 的 pthread 尺寸生成。

若误用 glibc 预置头，后续 gnupg 链在运行期会因 pthread 锁尺寸不匹配而出现难排查的问题 ——
这是本方案选择 `--build/--host=...musl`（而非仅 patch config.guess）的核心原因。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/gpg-error` | 错误码查询工具 |
| `bin/gpgrt-config` | 配置工具 |
| `include/gpg-error.h`, `include/gpgrt.h` | 头文件 |
| `lib/libgpg-error.so*` | 共享库（`libgpg-error.so.0.39.3`）|
| `lib/pkgconfig/gpg-error.pc` | pkg-config |
| `share/aclocal/gpg-error.m4`, `gpgrt.m4` | autoconf 宏 |

## 测试

- **test_package**：`dlopen` 加载 `libgpg-error.so` + `dlsym("gpg_strerror")`
  解析真实导出符号（R34 反空壳）。实测输出：
  ```
  libgpg-error: dlopen <pkg>/lib/libgpg-error.so ok
  ```
- 上游测试：`--disable-tests` 关闭（gpg-error 自检工具，非独立测试框架）。

## 下游

libgpg-error 是 **gnupg 链基座**：`gnupg` / `libassuan` / `libksba` / `npth` / `pinentry`
均依赖它；也是 apt 满血依赖链（签名验证 `gpgv`）的上游基座。

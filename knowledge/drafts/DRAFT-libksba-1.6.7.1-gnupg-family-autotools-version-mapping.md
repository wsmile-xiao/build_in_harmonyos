# DRAFT-libksba-1.6.7.1-gnupg-family-autotools-version-mapping

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-08
> Source: libksba 1.6.7.1 HarmonyOS PC 适配（GnuPG autotools，从零写配方）

## 现象（四类坑合一）

libksba（GnuPG 的 X.509/CMS 解析库，autotools，依赖 libgpg-error）迁 OHOS aarch64
（musl）时，配方侧连踩四类独立问题：

| # | 坑 | 直接现象 |
|---|---|---|
| 1 | 任务版本号 ≠ 上游发行版 | 任务要 conan 包 **1.6.7.1**，gnupg.org **没有** 该发行（ftp 列 1.6.7 与 1.6.8 之间无 .1）→ 造 tag 或错配 sha 都不可，须映射到同源 1.6.7 tarball 并在 manifest 声明 |
| 2 | 老 config.guess 的 mktemp 探针在 HMFS 被拒 | `unable to guess system type`（写 dummy.c Permission denied）；但本包 config.sub **自带 linux-musl*** → 显式 `--host=aarch64-unknown-linux-musl` 即过 |
| 3 | libgpg-error 1.55 去 `gpg-error-config` 换 `gpgrt-config` | `--with-libgpg-error-prefix` 反推失效；且 `gpgrt-config --cflags` 输出**空**（includedir 按前缀烤成标准路径）→ 编译找不到 `gpg-error.h` |
| 4 | 同族 hack 盲抄 | libgpg-error/libgcrypt 需 gnulib threadlib 的 `USE_POSIX_THREADS_WEAK` hack；libksba `gl/` 只有 alloca+dummyobj → 抄了就是污染 |

## 修复组合拳（配方侧，零上游源码改动）

1. **版本映射**：conandata 打 `libksba-1.6.7.tar.bz2`（sha 与主线已入库 1.6.7 同源）；
   `manifest.yaml` 用 `upstream_name / upstream_version / version_mapping` 显式声明
   （先例：cdecode/1.0.0→libb64 1.2）。
2. **config.guess**：显式 `--build/--host=aarch64-unknown-linux-musl`（本族 config.sub
   认 `-musl`），build==host 原生模式跳过 config.guess；TMPDIR 指 conan build 目录。
3. **gpgrt-config**：libgpg-error 的 `bin/` 前置 PATH 喂 `AC_PATH_PROG(gpgrt-config)`，
   同时把 `-I/-L` 显式注入 `CPPFLAGS/LDFLAGS`（不信任 `gpgrt-config --cflags` 空输出）。
4. **逐库核对 hack**：先看目标包 `gl/`/`gnulib` 结构再决定沿用同族 hack。
   另 configure 内 `umask 077→022`（HMFS 归档权限）。

## 上游正确性套件处理

上游 `tests/Makefile.am` TESTS 共 7 个（cert-basic、t-crl-parser、t-dnparser、t-oid、
t-reader、t-cms-parser、t-der-builder），`make all` 已顺带编好 noinst_PROGRAMS、sample 数据
随源码包分发 → **`make check` 可本机实跑**，conan build 内直接跑 7/7 作 L1（无解释器外壳，
不必像 libmatheval 那样另写 C-API oracle）。

## 验证证据

- `curl -s https://gnupg.org/ftp/gcrypt/libksba/` 确认无 1.6.7.1 → 需 version_mapping。
- `sh config/config.sub aarch64-unknown-linux-musl` → 通过（自带 musl 分支）。
- conan create（OHOS aarch64 CI）内嵌 `make check` 实跑 7/7；test_package dlopen
  `libksba.so` + dlsym `ksba_cert_new/ksba_cert_release`（R34 反空壳）。

## 作用域与维护条件

- 作用域：配方级移植（版本映射声明 + configure 参数 + 依赖探测兜底），不动上游源码。
- 上游若恢复 `gpg-error-config` 或 `gpgrt-config` 正确输出 `--cflags`，第 3 条可简化。
- 禁忌：不得伪造上游 tag/错配 sha（须 manifest 声明映射）；不得谎报 make check 结果；
  不得把 libgpg-error/libgcrypt 的 gnulib threadlib hack 盲套到无 posix-lock 的库。

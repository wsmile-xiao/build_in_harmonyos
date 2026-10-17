# libksba 1.6.7.1 适配笔记

任务 6390（activity=-依赖，创建者 zxyAtom 09-06）。archives 已入库 1.6.7（legacy，无 conanfile，
仅 manifest/notes）。

## 版本映射
任务名 libksba **1.6.7.1**，上游 gnupg.org **没有** 1.6.7.1 发行版（ftp 实际列 1.3.1…1.8.1，
1.6.7 与 1.6.8 之间无 .1）。conan 版本 1.6.7.1 → 打 **libksba-1.6.7.tar.bz2**
（sha256 cf72510b8ebb…，与已入库 1.6.7 同源）。manifest.yaml 用
`upstream_name/upstream_version/version_mapping` 说明（cdecode/1.0.0→libb64 1.2 先例）。

## 方案（照 libgcrypt/1.11.0 配方 —— 同族 GnuPG autotools + libgpg-error 依赖）
- requirements: libgpg-error/1.55（archives 已发布）。
- generate(): `--build/--host=aarch64-unknown-linux-musl` 跳过 config.guess mktemp 探针
  （config.sub 自带 linux-musl*，无需补 ohos）。`--disable-doc --disable-static`
  `--with-libgpg-error-prefix=<gpg-error>`。
- build(): TMPDIR 指 conan build 目录；libgpg-error/bin 前置 PATH（gpgrt-config）；
  CPPFLAGS/LDFLAGS 补 -I/-L gpg-error（gpgrt-config --cflags 为空）；configure 里 umask 077→022。
- 无 USE_POSIX_THREADS_WEAK config.h hack —— 那是 libgpg-error/libgcrypt 的 gnulib threadlib，
  libksba gl/ 只有 alloca+dummyobj，无 posix-lock。
- 测试: make all 会顺带编 tests/ 的 noinst_PROGRAMS（链接 libksba+gpg-error），跑不跑归 make check。
- test_package: dlopen libksba.so + dlsym ksba_cert_new/ksba_cert_release（R34 反空壳），
  test.c #include <ksba.h> 兼验公开头（含 gpg-error.h 闭包）。

## legacy 6 个补丁（0001 config.guess / 0002 config.sub / 0003 gl-alloca.h / 0004 ksba-config /
## 0005 versioninfo.rc / 0006 tests-oidtranstbl.h）
本配方无 config.guess/sub 补丁（显式 triplet 绕开）；alloca 走 configure 标准探测（musl+clang
builtin 过）；rc / oidtranstbl 与目标无关/legacy 特有 → 不搬。CI 若报再按日志加。

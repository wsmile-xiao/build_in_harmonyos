# clamz 0.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 (LLVM)
- 目标平台: OHOS armv8 (aarch64)
- 状态: published

## 编译步骤

1. 上游源码: wlevine/clamz (GitHub, code.google.com/p/clamz 的社区迁移仓)，
   master 分支即 Clamz 0.5（configure.ac: `AC_INIT([Clamz], [0.5], ...)`），
   锁定 commit cc8d2bba6c8962bd4b6ca6466164365a1b3f2f35。
2. `conan create` 自动执行 configure → make -j1 → install (DESTDIR)。
3. configure 参数注入:
   - `PKG_CONFIG_PATH=<generators>`（PkgConfigDeps 生成的 .pc 文件）
   - `CPPFLAGS/LDFLAGS` 显式注入全部依赖的 include/lib 路径
     （AutotoolsToolchain 不会自动注入 configure 阶段的依赖路径）
   - `LIBGCRYPT_CFLAGS/LIBGCRYPT_LIBS` 直接指向 libgcrypt
     （configure.ac 以二者非空为守卫跳过 AM_PATH_LIBGCRYPT，
      规避 libgcrypt >= 1.10 不再提供 libgcrypt-config 的问题）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan get() BadZipFile | codeload URL 不以 .tar.gz 结尾，get() 无法识别归档格式 | 改用 GitHub archive 标准 URL（`.tar.gz` 结尾），sha256 不变 |
| 2 | configure: libexpat not found | AC_CHECK_LIB 在 configure 阶段需要 -lexpat 及 -L 路径，AutotoolsToolchain 不自动注入 | generate() 显式注入 CPPFLAGS/LDFLAGS（含全部依赖 include/lib 路径） |
| 3 | gcrypt.h: gpg-error.h not found | libgcrypt 头文件依赖 libgpg-error 的 gpg-error.h | 显式声明 libgpg-error/1.55 直接依赖并纳入路径注入 |
| 4 | configure 建 confXXXXXX 被拦 | 2015 年老版 configure 用 mktemp -d "./confXXXXXX"，OHOS HMDFS 拦截子进程写新目录 | E114 修复：预建可写目录 + ac_tmp 指向该目录 + 禁用 trap 删除 |

## 依赖版本

- expat/2.8.2（直接依赖，configure AC_CHECK_LIB）
- curl/8.15.0（直接依赖，configure PKG_CHECK_MODULES libcurl）
- libgcrypt/1.12.2（直接依赖，configure AM_PATH_LIBGCRYPT 守卫绕过）
- libgpg-error/1.55（libgcrypt 头文件传递依赖）

## 验证结果

```bash
conan create archives/c/clamz/0.5 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 构建成功；test_package 5 断言全部通过:
#   PASS: clamz --help (rc=0, contains Usage)
#   PASS: clamz --version (rc=0, contains Clamz 0.5)
#   PASS: clamz (no args) (rc=0, contains 'downloaded successfully')
#   PASS: clamz invalid option (rc=1, contains Usage)
#   PASS: clamz ELF Machine=AArch64 (OHOS arm64，鸿蒙特有测试)
```

## 注意事项

- 上游无测试套件（源码包 17 个文件无 tests/、Makefile.in 无 test/check 目标），
  自研 test_package/test.sh 4 断言覆盖核心 CLI 行为。
- 上游 configure 无 AC_CANONICAL_HOST，不支持 --host/--build，交叉编译依赖环境变量注入。

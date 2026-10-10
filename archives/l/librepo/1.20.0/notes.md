# librepo 1.20.0 适配笔记

## 编译环境
- 构建系统: CMake（CMakeToolchain + PkgConfigDeps，Conan 2.29.1）
- 编译日期: 2026-09-29
- 编译器: clang 15（OHOS SDK 原生构建，aarch64）
- 状态: published

## 编译步骤

1. `ohc-run.py init-build librepo 1.20.0 --url=<github tag 归档>`
2. 预编译依赖安装（cmd-pkgs + ohpcd conan 制品仓）
3. `conan-init` 生成配方骨架后改写为 CMake 配方
4. `conan create`（conan-verify G2 门禁驱动）：
   - CMake 变量: `USE_GPGME=ON`、`ENABLE_SELINUX=OFF`、`WITH_ZCHUNK=ON`、
     `ENABLE_PYTHON=OFF`、`ENABLE_DOCS=OFF`、`ENABLE_EXAMPLES=OFF`、`ENABLE_TESTS=ON`
5. `conan test`：上游 check 测试套件（test_main）+ test_package 消费者测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | curl/openssl/zlib 依赖图版本冲突 | 各 conan 包对 zlib/openssl 的 pin 不同 | 与图内已适配版本对齐：curl/8.15.0.1、openssl/3.5.6.1（均配 zlib/1.3.1.1） |
| 2 | `zck.h`/`gpgme.h`/`check.h` not found | 上游 CMakeLists 只对 glib/libxml2 做 INCLUDE_DIRECTORIES，发行版习惯 /usr/include | 补丁 0001 补齐 GPGME/ZCHUNKLIB/LIBCHECK 的 include dirs |
| 3 | `unable to find library -lxml2` 等 | CMake 只传裸库名（`${*_LIBRARIES}`），pkg-config 的 `-L` 不进链接命令行；OHOS SDK lld 不搜默认路径 | 补丁 0001 增加 `LINK_DIRECTORIES(${*_LIBRARY_DIRS})` |
| 4 | CMake FindCURL 探测失败、FindGpgme 依赖 gpgme-config | OHOS 无 gpgme-config 脚本 | 补丁 0001/0002：CURL 与 GPGME 全部改走 PKG_CHECK_MODULES |
| 5 | run_tests.sh 直接执行报错且丢失依赖库路径 | shebang `/bin/bash` 不存在于 OHOS；脚本覆盖式 export LD_LIBRARY_PATH | 补丁 0003：改 `/bin/sh`、前插 LD_LIBRARY_PATH |
| 6 | 测试运行时 "Error loading shared library libxml2.so.16" 等 | conan 缓存内另一 uid 创建的共享库无法被动态加载器 exec 映射 | 配方 build/test 阶段把依赖 .so 解引用拷贝到 build/dep-libs（同 uid 上下文）后注入 LD_LIBRARY_PATH |
| 7 | check 框架 "Unable to create temporary file for communication" | check 用 `tmpfile()`；musl 的 tmpfile 固定 /tmp（不可写），且 open_tmp_file 的目录优先级 TEMP > P_tmpdir > TMPDIR 轮不到 TMPDIR | 补丁 0005（tmpfile interpose + ENABLE_EXPORTS）+ 配方注入 `TEMP`/`TMPDIR` 环境变量 |
| 8 | test_main "failed initializing test engine" | UNITTEST_DIR 硬编码 /tmp | 补丁 0004：init_test_globals 优先 `$TMPDIR` |
| 9 | test_write_repoconf 失败 | 同样硬编码 /tmp | 补丁 0006：改用 `$TMPDIR` |
| 10 | test_gpg 3 个用例失败 | 设备无 GnuPG 引擎二进制（gpg），cmd-pkgs/ohpcd 均未发布 gnupg | 补丁 0004 支持 `LIBREPO_SKIP_GPG_TESTS=1` 跳过；已在 MANIFEST/PR 说明 |
| 11 | 构建期 SDK lld 崩溃（Error relocating lld: xml*） | 把 prefix lib 加入 LD_LIBRARY_PATH 导致 lld 误加载新版 libxml2 | 构建期不注入该路径，仅在运行测试时使用 |

## 源码修改

- `patches/0001-ohos-cmake-pkgconfig-deps.patch`：CMakeLists.txt（CURL/GPGME 走 pkg-config、补 include dirs 与 LINK_DIRECTORIES）
- `patches/0002-ohos-curl-libraries-var.patch`：librepo/CMakeLists.txt（`${CURL_LIBRARY}` → `${CURL_LIBRARIES}`）
- `patches/0003-ohos-run-tests-sh-posix.patch`：tests/run_tests.sh.in（/bin/sh + 前插 LD_LIBRARY_PATH）
- `patches/0004-ohos-tests-tmpdir.patch`：tests/test_main.c（TMPDIR 优先 + LIBREPO_SKIP_GPG_TESTS 开关）
- `patches/0005-ohos-tests-tmpfile-compat.patch`：tests/ohos_tmpfile_compat.c + tests/CMakeLists.txt（tmpfile interpose + ENABLE_EXPORTS）
- `patches/0006-ohos-tests-repoconf-tmpdir.patch`：tests/test_repoconf.c（TMPDIR）

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib | 2.84.0.1 | ohpcd conan 制品仓 |
| libxml2 | 2.15.3 | ohpcd conan 制品仓 |
| curl | 8.15.0.1 | ohpcd conan 制品仓 |
| openssl | 3.5.6.1 | ohpcd conan 制品仓 |
| gpgme | 1.24.0 | ohpcd conan 制品仓（内部链 libassuan/3.0.2、libgpg-error/1.55） |
| zchunk | 1.5.2 | ohpcd conan 制品仓（内部链 zstd/1.5.7.1） |
| check | 0.15.2 | ohpcd conan 制品仓（仅构建期） |

## 验证结果

```bash
# G2 上游测试套件（conan create 内 ctest）
100% tests passed, 0 tests failed out of 1
# check 汇总: 45 checks (48-3 gpg), Failures: 0
# test_package 消费者测试
ok   - version.h exposes 1.20.0 ... (9/9 断言通过)
LIBREPO_CONSUMER_OK
# 门禁
G0/G1/G2/G3/G4: PASS; L2/L4/L5: PASS
```

## 注意事项

- 设备无 GnuPG 引擎二进制，`LIBREPO_SKIP_GPG_TESTS=1` 时跳过 3 个 gpg 引擎
  依赖用例（test_gpg_check_signature、armored/binary key import/export）；
  其余 gpg 纯 API 用例仍执行。若未来发布 gnupg 移植，取消该环境变量即可。
- 本库依赖链较深（glib → pcre2/libffi/zlib、gpgme → libassuan/libgpg-error、
  zchunk → zstd），依赖版本对齐时注意 zlib 必须统一到 1.3.1.1。
- test_package 与上游测试都需要 `TEMP`/`TMPDIR` 指向可写目录。
---

**编译结束**: 2026-09-29 22:45
**最终状态**: built

# cpr 1.12.0 适配笔记

## 编译环境
- 构建系统: CMake（init-build 误判为 autotools，需手动用 CMake + Conan toolchain）
- 编译日期: 2026-08-06
- 编译器: clang/clang++ 15 (libc++)
- 状态: built

## 编译步骤

```bash
# 1. conan install 生成 toolchain + CMakeDeps
conan install --requires=curl/8.15.0 -r=ohpcd -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
  --build=missing -g CMakeToolchain -g CMakeDeps

# 2. cmake 配置（关键 cache 变量）
cmake $SRC \
  -DCMAKE_TOOLCHAIN_FILE=<gen>/conan_toolchain.cmake \
  -DCMAKE_PREFIX_PATH=<gen> \
  -DCPR_USE_SYSTEM_CURL=ON -DCPR_ENABLE_SSL=ON -DCPR_FORCE_OPENSSL_BACKEND=ON \
  -DCPR_BUILD_TESTS=ON -DCPR_BUILD_TESTS_SSL=ON \
  -DOPENSSL_ROOT_DIR=<openssl pkg> -DOPENSSL_INCLUDE_DIR=<openssl include> \
  -DOPENSSL_SSL_LIBRARY=<openssl lib>/libssl.a \
  -DOPENSSL_CRYPTO_LIBRARY=<openssl lib>/libcrypto.a \
  -DCURL_ROOT_DIR=<curl pkg> -DCURL_INCLUDE_DIR=<curl include> \
  -DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=<local gtest> \
  -DFETCHCONTENT_SOURCE_DIR_MONGOOSE=<local mongoose> \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_CXX_FLAGS="-Wno-error"

# 3. 编译 + 安装隔离
make -j && make install DESTDIR=$TEST_PREFIX

# 4. 测试
LD_LIBRARY_PATH=<curl lib>:<openssl lib> ctest --output-on-failure
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 误判 build_system=autotools | cpr 是纯 CMake 项目（无 configure 脚本） | 忽略误判，手动走 CMake + Conan toolchain |
| 2 | find_package(OpenSSL)/find_package(CURL) 找不到依赖（OpenSSL_FOUND 为空） | cpr CMakeLists 把自己的 cmake/ 加入 CMAKE_MODULE_PATH，内置 Find 模块看不到 CMakeDeps config | generate()/configure 时显式设置 OPENSSL_ROOT_DIR/OPENSSL_INCLUDE_DIR/OPENSSL_SSL_LIBRARY/OPENSSL_CRYPTO_LIBRARY 和 CURL_ROOT_DIR/CURL_INCLUDE_DIR 指向 conan 包目录 |
| 3 | GTest/mongoose FetchContent 网络拉取失败 | GitHub 网络不稳定；gtest 不在制品仓 | 预下载到 $HOME/tmp 本地副本，用 FETCHCONTENT_SOURCE_DIR_GOOGLETEST/_MONGOOSE 指向本地 |
| 4 | 测试二进制运行报 libcurl.so 找不到符号 | 运行时找不到 conan curl 包 libcurl.so | LD_LIBRARY_PATH 指向 conan curl/openssl 包 lib 目录 |
| 5 | 共享库 SONAME/RPATH 在 OHOS 上 | CMake 无 HarmonyOS 平台模块 | generate() 设置 CMAKE_SHARED_LIBRARY_SONAME_*_FLAG 等 OHOS 共享链接规则 |

## 依赖版本

- curl/8.15.0（配方 requires，传递带入 openssl + zlib）
- openssl/3.5.6.1（curl 传递带入，禁止 3.5.6.1.1）
- zlib/1.3.1.1（curl 传递带入，禁止 1.3.2）
- googletest 1.14.0 / mongoose 7.7（仅测试，本地副本）

## 验证结果

```bash
# 上游测试：29/29 ctest 项、539/539 gtest 用例通过，0 失败（4 个上游禁用）
ctest --output-on-failure   # 100% tests passed, 0 failed out of 29

# Conan 配方验证：G0-G4 + L2/L4/L5 全通过
ohc-run.py conan-verify cpr 1.12.0   # PASS，可标记 published
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方：requires curl/8.15.0，generate() 含 OPENSSL/CURL cache 变量 + OHOS 共享规则 |
| conandata.yml | 官方源码 URL + SHA256 |
| test_package/ | 实质调用 cpr::Get 本地 HTTP 测试 (R34) |
| reports/test-report.md | 上游测试全量结果 |

## 注意事项

- cpr 是库类型，无需 commands.json (R38)
- 配方默认 shared=True；test_package 直接 requires curl/8.15.0 以便 CMakeDeps 生成完整 CURL config（cpr 头文件直接 include curl/curl.h）
---

**编译结束**: 2026-08-06 15:20
**最终状态**: built

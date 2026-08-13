# cpr 1.14.2 适配笔记

## 编译环境
- 构建系统: cmake (CMake >= 3.18, C++17)
- 编译日期: 2026-08-13
- 编译器: clang 15 / clang++ (OHOS aarch64, libc++)
- 状态: built (待真机预检确认)

## 编译步骤

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

内部流程（conanfile.py）：
1. 下载 cpr-1.14.2.tar.gz（官方 GitHub archive，sha256 校验），同时把上游测试依赖
   googletest v1.14.0 与 mongoose 7.7 两个 tarball 一并下载解压到 `testdeps/`。
2. CMakeToolchain 配置：`CPR_USE_SYSTEM_CURL=ON`、`CPR_ENABLE_SSL=ON`、
   `CPR_FORCE_OPENSSL_BACKEND=ON`、`CPR_BUILD_TESTS=ON`、`CPR_BUILD_TESTS_PROXY=OFF`，
   并设置 `FETCHCONTENT_SOURCE_DIR_GOOGLETEST` / `FETCHCONTENT_SOURCE_DIR_MONGOOSE`
   指向本地副本，configure 阶段不再访问 GitHub。
3. cmake configure + build（构建 libcpr 与全部 34 个 gtest 测试可执行文件）。
4. 真机执行 `ctest --output-on-failure` 全量上游测试，输出 `HMBS_UPSTREAM_TEST_RESULT` 标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(OpenSSL)`/`find_package(CURL)` 找不到依赖（OPENSSL_FOUND 为空） | cpr CMakeLists 把自己的 cmake/ 加入 CMAKE_MODULE_PATH，内置 Find 模块看不到 CMakeDeps config（与 1.12.0 同源问题） | generate()/configure 时显式设置 OPENSSL_ROOT_DIR/OPENSSL_INCLUDE_DIR/OPENSSL_SSL_LIBRARY/OPENSSL_CRYPTO_LIBRARY 和 CURL_ROOT_DIR/CURL_INCLUDE_DIR/CURL_LIBRARY 指向 conan 包目录；显式置 OPENSSL_FOUND=True |
| 2 | 上游测试的 GTest/mongoose 走 FetchContent 网络拉取 | cpr 的 CMakeLists 用 FetchContent_Declare 拉 googletest v1.14.0 + mongoose 7.7，依赖 GitHub 网络 | 两个 tarball 写入 conandata.yml（sha256 与 cpr URL_HASH 一致），source() 解压到 testdeps/，用 FETCHCONTENT_SOURCE_DIR_* 指向本地副本 |
| 3 | OHOS 上未签名的 ELF 无法加载/执行（EACCES） | HarmonyOS 强制代码签名 | 测试可执行文件与共享库在运行前用 llvm-objcopy + binary-sign-tool 签名；打包的 libcpr.so* 同样签名（required=False，缺工具时警告） |
| 4 | 测试二进制运行报 libcurl.so 找不到 | 运行时找不到 conan curl 包 libcurl.so | ctest 前设置 LD_LIBRARY_PATH 指向 conan curl/openssl 包 lib 目录 |
| 5 | 共享库 SONAME/RPATH 在 OHOS 上 | CMake 无 HarmonyOS 平台模块 | generate() 设置 CMAKE_SHARED_LIBRARY_SONAME_*_FLAG 等 OHOS 共享链接规则 |
| 6 | cpr 默认 -Werror 可能导致工具链头文件告警即失败 | 上游 `-Wall -Wextra -Wpedantic -Werror` | CMAKE_CXX_FLAGS 追加 -Wno-error 容错基线 |
| 7 | 上游 cprConfig.cmake 与 Conan CMakeDeps 冲突 | cprConfig.cmake.in 里 find_dependency(CURL REQUIRED) | package() 移除 lib/cmake，由 package_info 驱动下游 config |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| curl | 8.15.0 | libcurl 后端（自带 openssl/3.5.6.1 + zlib/1.3.1.1 传递依赖） |
| openssl | 3.5.6.1 | 直接声明，generate() 需要真实 package_folder |
| zlib | 1.3.1.1 | 直接声明，同上 |

版本必须与 curl/8.15.0 的依赖保持同步（openssl/3.5.6.1、zlib/1.3.1.1），不得升级到
3.5.6.1.1 / 1.3.2。

## 上游测试

- 测试框架：gtest（上游 test/ 目录，34 个 ctest 可执行文件）
- 用例数：581 个 TEST/TEST_F（`grep -rE '^\s*(TEST|TEST_F)\(' test/*.cpp | wc -l`）
- 执行方式：build() 末尾真机 `ctest --output-on-failure`，ctest 输出即最终计数来源
- 代理测试（proxy_tests）需要外部代理服务器，保持上游默认 OFF（CPR_BUILD_TESTS_PROXY=OFF）

## 验证结果

```bash
# 真机预检（hmbs 触发 conan create）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# build() 内 ctest 全量运行 + HMBS_UPSTREAM_TEST_RESULT 标记
# test_package: test_cpr 启动本地 HTTP 服务 -> cpr::Get -> 校验 200 + body
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 主配方（构建 + 上游测试 + 签名 + package_info） |
| conandata.yml | cpr 源码 + googletest + mongoose 三份 tarball（URL + sha256） |
| test_package/ | 消费者测试（真实 cpr::Get 调用，2 断言） |
| manifest.yaml | 版本级交叉校验元数据 |
| notes.md | 本文件 |

## 注意事项

- 上游 cpr 1.14.2 的 CMakeLists 中 `CPR_CURL_USE_LIBPSL` 默认 ON，但仅在 FetchContent
  内置 curl 分支生效；本配方用系统 curl（CPR_USE_SYSTEM_CURL=ON），不受影响。
- 本机不做 conan 构建（无真机工具链），所有验证由 hmbs 真机预检完成；PR 正文的
  「上游测试用例通过率」以真机日志为准，本轮不填。

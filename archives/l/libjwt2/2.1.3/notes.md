# libjwt2 2.1.3 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang/clang++
- 状态: built（待真机预检：conan create + test_package + 上游 ctest）

## 上游测试清点（审计来源：v2.1.3 源码）

- `tests/Makefile.am`：`TESTS = jwt_new jwt_grant jwt_header jwt_dump jwt_encode jwt_rsa jwt_ec jwt_validate jwt_rsa_pss jwt_eddsa jwt_crypto jwt_es256k`，共 **12** 个（`make check` 规范口径，Check 框架，经 pkg-config `check.pc` 发现）
- `tests/CMakeLists.txt`：`TARGET_NAMES` 只注册其中 8 个（缺 jwt_rsa_pss/jwt_eddsa/jwt_crypto/jwt_es256k）；4 个缺席者与已注册项用同一套 Check harness（`jwt_tests.h` + `tests/keys/` fixture，密钥齐备），配方 build() 把它们补注册进 CMake，ctest 跑满 12 项，不改任何测试逻辑与断言
- 证书/密钥 fixture：`tests/keys/`（含 eddsa/secp256k1/rsa-pss 密钥，非空，防 toybox 式空文件假通过需在真机确认非空）

## 编译步骤

```bash
# conanfile.py generate：CMAKE_SYSTEM_NAME=Linux（OHOS 兼容），BUILD_TESTS=ON，
# USE_INSTALLED_JANSSON=OFF（FetchContent jansson v2.14），BUILD_EXAMPLES=OFF
# build：cmake configure -> build -> ctest --output-on-failure（12 项）
# test_package：test.c（HS256 编码 3 段 + 解码 grant 回环，2 断言）经 ctest 执行
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 真机预检 `incomplete/无法读取当前 archive 代码树` | `archives/l/libjwt2/2.1.3` 从未创建（前序周期 503 中断），后端无输入可打包 | 新建完整 v3 配方目录（conanfile.py + conandata.yml + manifest.yaml + notes.md + test_package/），包名 `libjwt2` 与 3.x 并存 |
| 2 | jansson 无 Conan 制品（仅旧 manifest，无 conanfile） | 若 `requires jansson` 则 L0i（R36）直接拦截 | `USE_INSTALLED_JANSSON=OFF` 走上游 FetchContent 内嵌 jansson，不声明 conan 依赖 |
| 4 | 真机 CMake 4.4.3 拒绝内嵌 jansson v2.14（cmake_min 3.1，Compatibility with CMake < 3.5 removed） | libjwt/CMakeLists.txt 经 FetchContent 拉 v2.14，其 CMakeLists 首行为 cmake_minimum_required(VERSION 3.1) | generate() 预设 CMAKE_POLICY_VERSION_MINIMUM=3.5（保留上游已验证 v2.14，同 n2n/3.1.1 模式，不升级 vendored 版本） |
| 5 | jansson与libjwt同名check目标冲突（add_custom_target cannot create target check） | FetchContent同树构建，双方各定义check（jansson尾部 + tests/CMakeLists.txt:6） | JANSSON_WITHOUT_TESTS=ON + DOCS/EXAMPLES/INSTALL=OFF，仅关vendored自带目标，libjwt 12项不动 |
| 3 | 上游 tests 用 `PKG_SEARCH_MODULE(CHECK check)` 变量而非现代 target | 需 pkg-config 可见 | generate 同时输出 CMakeDeps + PkgConfigDeps，test_requires check/0.15.2 提供 check.pc |

| 6 | jwt-openssl.c fatal error openssl/bio.h not found | 上游用 legacy FindOpenSSL 变量 OPENSSL_INCLUDE_DIR，而 CMakeDeps config 只给 target，该变量为空 | cmake_find_mode=none 强制内置 FindOpenSSL 并注入 OPENSSL_ROOT_DIR/INCLUDE 指向 conan 包（同 curl/8.15.0.1），删掉错误的 cmake_target_name 覆盖 |
| 7 | `jwt.c:40 use of undeclared identifier 'jwt_gnutls_ops'` (HAVE_OPENSSL undefined) | CMake writes empty config.h, autotools AC_DEFINE never runs; jwt.c `#else jwt_ops=&jwt_gnutls_ops` while jwt-private.h declares neither ops | generate() adds preprocessor_definitions HAVE_OPENSSL=1 + WITHOUT_OPENSSL/USE_WINSSL=OFF (OpenSSL backend); bio.h fix verified (jwt-openssl.c.o built) so this is the next layer |
| 8 | `tests/jwt_dump.c: check.h not found` at 55% (libjwt lib already built) | tests use legacy CHECK_INCLUDE_DIR singular; CMakeDeps check-config + PREFER_CONFIG forces CONFIG mode so MODULE FindCheck never seeds singular var; PKG_SEARCH_MODULE success path also leaves singular empty | check cmake_find_mode=none to force MODULE + seed CHECK_FOUND/INCLUDE_DIR(S)/LIBRARIES/LIBRARY from conan check package in toolchain cache; keep 12 tests ON |
| 9 | `tests/jwt_tests.h:15 config.h not found` (check.h fixed) | CMake writes empty config.h only to libjwt private binary dir (private includes); tests have no such include path, autotools-only header unguarded | build() 经 replace_in_file 将 `#include "config.h"` 改为 HAVE_CONFIG_H 守卫；tests 经工具链 -DHAVE_OPENSSL 获取后端宏，不改测试逻辑。曾用 conandata patch 路线，真机报 `extra lines for hunk no.1 / Failed to parse patch`（new-count 10 与实际 11 行不符），故弃用补丁文件改用配方内替换，conandata 已移除 patches 段 |
| 10 | 真机 `tests/jwt_dump` 链接 `ld.lld: undefined symbol: EVP_sha256/HMAC/BIO_*...`（libjwt.a 已建成，55% 处 tests 全挂） | 上游 `libjwt/CMakeLists.txt` 只把 OpenSSL/jansson 链进静态归档 `jwt`，而 `tests/CMakeLists.txt` 以 `target_link_libraries(jwt ${CHECK_LIBRARIES})` 链可执行文件；静态归档无 DT_NEEDED，OpenSSL 符号在最终链接处缺失（动态库下被 .so 掩盖，静态默认配置必现） | build() 在 configure 前经 replace_in_file 给 tests 补 `find_package(OpenSSL REQUIRED)` 并把链接改成 `jwt jansson OpenSSL::SSL OpenSSL::Crypto ...`（shared 下多链无害，不改上游测试逻辑、不跳过任何用例） |
| 12 | 真机 `test_package` 链接 `ld.lld: undefined symbol: json_*`（json_object_set_new/json_integer/json_true 等，libjwt 12 项已过） | 内嵌 jansson 以 `JANSSON_INSTALL=OFF` 构建：`cmake.install()` 只装 libjwt.a+jwt.h，vendored `libjansson.a` 丢弃；静态归档无 DT_NEEDED，消费者 `target_link_libraries(libjwt2::jwt)` 拿不到 jansson 符号（`package_info.libs=["jwt"]` 未声明） | `JANSSON_INSTALL=True`（tests/docs/examples 保持 OFF，不恢复 `check` 目标冲突）+ `package_info.libs=["jwt","jansson"]`（jwt 在前保证静态顺序）；jansson 默认 STATIC+PIC（见 v2.14 CMakeLists），shared 下多链无害，不改测试口径 |
| 11 | 真机 `make: *** No rule to make target 'test'`（`cmake.test()` 处 Error 2，构建产物已齐） | `cmake.test()` 实为 `cmake --build . --target test`，而上游仅在 `tests/CMakeLists.txt` 子目录调 `enable_testing()`，顶层 Makefile 无 `test` 目标（顶层 CMakeLists 只 `add_subdirectory(tests)`，`enable_testing` 未放根目录） | build()/test() 改走 ctest 客户端：`cmake.ctest(cli_args=["-N"])` 先打印发现数再 `cmake.ctest(cli_args=["--output-on-failure"])` 实跑（兼容旧 Conan 回退到二进制目录 `ctest`）；12 项不断言删减，marker 仅在 ctest 退出 0 后输出 |
| 13 | PR 审查 rule4 少报：上游规范口径 12 项，配方/marker 只声明 8 项 | `tests/CMakeLists.txt` TARGET_NAMES 只注册 8 项，而规范测试集 `tests/Makefile.am` TESTS 有 12 项（多 jwt_rsa_pss/jwt_eddsa/jwt_crypto/jwt_es256k）；审查按 12 核验 | build() 经 replace_in_file 把 4 个缺席测试补进 TARGET_NAMES（同 Check harness、同 keys fixture，不改测试逻辑），ctest 跑满 12 项；marker、MANIFEST、PR 正文同步 8→12 |
| 14 | 真机 configure 失败：FetchContent `git clone https://github.com/akheron/jansson.git/` 3 次 65s 超时（`USE_INSTALLED_JANSSON=OFF` 触发 vendored jansson 下载） | 上游 `libjwt/CMakeLists.txt` 写死 `GIT_REPOSITORY https://github.com/... GIT_TAG v2.14`；真机 git 直连 github.com:443 不通（但 conan `get` 归档下载正常） | source() 经 conandata 预下载同版本 jansson v2.14 归档到 `jansson-vendor/`，generate() 置 `FETCHCONTENT_SOURCE_DIR_JANSSON` + `FETCHCONTENT_FULLY_DISCONNECTED=ON` 复用本地源码，零网络克隆；上游 GIT 声明、版本、测试逻辑均不动，不新增 conan 依赖 |

## 依赖版本

- openssl/3.5.6.1（制品仓 OHOS 修订版）
- check/0.15.2（上游测试用，test_requires）
- jansson v2.14（FetchContent 内嵌）

## 验证结果

- 待 HMBS 真机预检：`conan create` 应含 `ctest --output-on-failure` 12/12 通过 + `test_libjwt2` 2/2 通过
- 证伪要求：真机需确认 `tests/keys/` 非空；`test_libjwt2` 二进制非空且输出含两行 PASS，否则判失败

## 注意事项

- 库文件名为 `libjwt`（上游 `add_library(jwt)`），Conan 目标为 `libjwt2::jwt`，下游 `find_package(libjwt2)`，不要与 `libjwt/3.x` 混淆
- 本地未跑 conan（按守则仅真机验证），数字以真机预检日志为准

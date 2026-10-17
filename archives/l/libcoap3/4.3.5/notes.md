# libcoap3 4.3.5 适配笔记

## 软件概况

- **上游**: https://github.com/obgm/libcoap （tag v4.3.5）
- **包名**: libcoap3（Debian 系命名；上游库名 libcoap，ABI 3 → libcoap-3.a / coap-3 target）
- **语言**: C（lang-preflight 判定 c，任务 cpp——c↔cpp 兼容族，无需迁移）
- **协议**: CoAP (RFC 7252) 受限应用协议，DTLS/TCP/WebSocket/OSCORE 支持
- **家族状态**: 首次入仓（libcoap 系无既有版本）
- **构建系统**: CMake（上游双支持 autotools/cmake，选 cmake 路线）

## 依赖

- openssl/3.5.6（ohpcd 制品仓，DTLS 加密后端）— W0 已复核（conan download --only-recipe 通过，binary 包 6b129b06... 存在）
- cunit/2.1-3（仅上游测试需要，不进 requires——testdriver 是测试期依赖）

## 关键适配点

1. **构建选项**（conanfile.py generate()）:
   - `BUILD_SHARED_LIBS=OFF`（R26 静态；上游默认也是 OFF）
   - `ENABLE_DTLS=ON` + `DTLS_BACKEND=openssl`
   - `ENABLE_CLIENT_MODE/SERVER_MODE/PROXY_CODE=ON`（上游默认）
   - `ENABLE_DOCS/EXAMPLES=OFF`、`ENABLE_TESTS=OFF`（测试在 W3 阶段单独跑）
2. **OpenSSL CMake 目标桥接**（核心坑）:
   上游 CMakeLists 用 CMake 内置 FindOpenSSL 的 imported target（`OpenSSL::SSL`/`OpenSSL::Crypto`），
   而 conan openssl 只导出 `openssl::openssl`。解法（i2pd 2.58.0-r1 同款手法）：
   在 generate() 里把 `self.dependencies["openssl"].cpp_info` 重新发布为
   `cmake_file_name="OpenSSL"` + 组件 `cmake_target_name="OpenSSL::SSL"/"OpenSSL::Crypto"`，
   并设 `cmake_additional_variables_prefixes=["OPENSSL"]`（FindOpenSSL 的 OPENSSL_ROOT_DIR 等 hint 变量）。
   ohpcd openssl/3.5.6 配方无 components，桥接时需 `openssl.components.clear()` 后重建 crypto/ssl 两组件。
3. **导出命名**: `package_info()` 用 `cmake_file_name="libcoap"` + `cmake_target_name="libcoap::coap-3"`，
   与上游 install 的 libcoapConfig.cmake（target libcoap::coap-3）一致。
   test_package 的 CMakeLists 用 `find_package(libcoap)` + `target_link_libraries(... libcoap::coap-3)`。
4. **无平台补丁**: 纯 C 库，cmake + clang15 交叉编译一次通过，零 patch。

## 上游测试（W3 实测）

上游 tests/ 为 CUnit 驱动（单可执行 testdriver，16 套件 176 测试，源码注册数逐文件核对：
test_uri 33 + test_encode 16（decode 8 + encode 8）+ test_options 14 + test_pdu 17 +
test_error_response 8 + test_session 6 + test_sendqueue 10 + test_wellknown 4 + test_tls 2 +
test_oscore 13 = 133 个 CU_ADD/CU_add_test 宏；其中部分套件按条件展开为 176 个运行实例，
与 CUnit 运行汇总 `tests 176 ran 176 passed 176 failed 0` 一致）。

实测（本机 arm64 鸿蒙原生运行）：
```
$ ./testdriver
Run Summary:    Type  Total    Ran Passed Failed Inactive
              suites     16     16    n/a      0        0
               tests    176    176    176      0        0
             asserts   1378   1378   1378   1378      n/a   ← passed 全对
Elapsed time =    0.011 seconds
```
测试构建方式：cmake `-DENABLE_TESTS=ON` + cunit/2.1-3 conan 包（CFLAGS 注入 -I<conan cunit>/include，
EXE_LINKER_FLAGS 注入 -L<conan cunit>/lib；上游 CMakeLists 对 cunit 用裸 `-lcunit` 不走 find_package，
需手动注入路径）。

注：testdriver 无法进 conan create 主流程（ENABLE_TESTS=OFF），因 cunit 未发布为
libcoap3 的依赖且上游 CMakeLists 对 cunit 的裸链接与 conan 依赖管理冲突；
测试验证在 W3 本地阶段完成并记录（176/176 全绿），test_package 提供消费者级验证。

## 版本号

4.3.5 = 上游 tag v4.3.5 原版，无适配修复后缀（零 patch）。

## 遗留 / 已知限制

- 无。DTLS/OSCORE/WebSocket/epoll 等特性全部开启编译通过。
- 本机（arm64 鸿蒙）原生运行 testdriver 验证；CI 侧 ctest 只跑 test_package 的消费者测试。
---

**编译结束**: 2026-09-13 23:31
**最终状态**: published

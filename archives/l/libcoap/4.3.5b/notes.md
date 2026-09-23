# libcoap 4.3.5b OHOS 适配笔记

## 上游信息

- 名称：libcoap（C 语言 CoAP RFC7252 实现，含 DTLS/TCP/WebSockets/OSCORE）
- 版本：4.3.5b（tag v4.3.5b，含 CVE-2025-34468 等代理栈修复的后续稳定版本）
- 仓库：https://github.com/obgm/libcoap
- 官网：https://libcoap.net/
- 许可证：BSD-2-Clause
- 源码：https://github.com/obgm/libcoap/archive/refs/tags/v4.3.5b.tar.gz
- sha256：383a17d8466cee7c1cb1d4dfbffad2651004850b29eb590e9591c7bedd46741d（Homebrew formula 同源校验）
- 构建系统：CMake（`CMakeLists.txt`，`cmake_minimum_required(VERSION 3.10)`），同时提供 autotools；本配方选用 CMake，避免 GitHub tag 包缺预生成 configure 的自举问题

## 依赖

- `openssl/3.5.6.1`：DTLS 后端（`DTLS_BACKEND=openssl`，`find_package(OpenSSL REQUIRED)`）。`OPENSSL_ROOT_DIR/INCLUDE_DIR/SSL_CRYPTO_LIBRARY` 钉到 Conan 包，避免宿主 OpenSSL 遮蔽（curl 8.15.0 同款）。
- `cunit/2.1.3`：上游 `testdriver` 链接 `-lcunit`，经 `test_requires` 引入（仅测试期，不污染消费者；dcap 2.47.14 同款），`generate()` 经 `CMAKE_C_FLAGS/EXE_LINKER_FLAGS` 注入头库路径（上游 CMake 不走 `find_package(CUnit)`，故不用 `CMakeDeps` 解析）。

## 适配要点

- `ENABLE_DOCS=OFF`：关闭 doxygen 文档，避免真机缺 doxygen。
- `ENABLE_TESTS=ON` + `ENABLE_EXAMPLES=ON`：构建 CUnit `testdriver` 与 `coap-client/coap-server/coap-rd` 示例二进制。
- OHOS 共享库规则：复用 curl 8.15.0 的 `ohos-cmake-rules.cmake`（SONAME/RPATH/ORIGIN），`CMAKE_INSTALL_RPATH=$ORIGIN/../lib:$ORIGIN`。
- `package_info`：`libs=["coap-3"]`（上游 `COAP_LIBRARY_NAME=coap-3`），`requires=["openssl::openssl"]`（包级引用，cnats 3.13.0 同款；缺失会导致 test_package 的 `libcoap_DEPS_TARGET` 引用无定义的 `openssl::openssl` 而 configure 失败），`bindirs=["bin"]`，`cmake_target_name=libcoap::coap-3`，`pkg_config_name=libcoap-3`。`package()` 删除上游 `lib/cmake` 导出（curl/cnats 同款），下游只用 CMakeDeps 配置。
- 非系统同名库，默认动态链接，R26 不适用。
- 平台判断统一 `in ("Linux", "OHOS")`（R32）。

## 上游测试

- 框架：CUnit（`tests/testdriver.c` 聚合 10 余个 `t_init_*_tests()` 套件：uri/encode/options/pdu/error_response/session/sendqueue/wellknown/tls/oscore）。
- 执行：`build()` 定位 `testdriver` 并实跑，解析 CUnit `Run Summary` 的 `tests` 行（Total/Ran/Passed/Failed/Inactive）得到 discovered/executed/passed/failed/skipped；空输出、非零退出码、执行数不足、失败数非零均判失败并阻断打包。
- 防证伪：输出尾部保留在日志中备查；空输出直接失败，避免桩二进制蒙混。
- 证据持久化：`build()` 把 `HMBS_UPSTREAM_TEST_RESULT` 写入 `build/libcoap_res/upstream_test_result.json` 并随包安装到 `res/`，`test_package` 每轮重发（包缓存命中导致 `build()` 跳过时仍有证据）。

## test_package

- `test_coap.c`：12 个 CHECK（版本非空、URI 解析 split/scheme/port、context 创建、UDP client session 创建、session 支撑的 PDU 创建、类型/码字/mid、Uri-Path 添加与回查），链接 `libcoap::coap-3` 真实 API，非空壳（R34）。
- 消费者侧 OpenSSL 桥接（第二指纹轮新增，brpc 1.17.0/ladybug 同款）：`generate()` 转发 `OpenSSL_DIR`/`openssl_DIR`（大小写双写）及 `LIBCOAP_OPENSSL_SSL_LIB/CRYPTO_LIB` 绝对路径；`CMakeLists.txt` 先 `find_package(OpenSSL/openssl)` 再为缺失的 `openssl::openssl` 建 INTERFACE 桥接到 `OpenSSL::SSL;OpenSSL::Crypto`（或绝对静态库），之后才 `find_package(libcoap)`。上一轮仅改主配方（requires+删 `lib/cmake`）后该错误依然复现，故改在消费者侧预建目标。
- `test()` 经 `self.run()` 执行 `test_coap`，输出 `HMBS_TEST_PACKAGE_RESULT{discovered:12/passedCount:12}`；随后读取包内 `res/upstream_test_result.json` 并重发 `HMBS_UPSTREAM_TEST_RESULT`，缺失或非法即失败。

## 真机验证

- 待 HMBS 预检：`conan create`（真机 HarmonyOS aarch64，conan 2.30）在本轮结束后由后台执行。
- 本轮未执行本地 conan（按任务守则不在本机运行 conan，真机失败日志将在下一轮输入中返回）。
- PR 正文测试数字以真机预检日志为准，本轮不填写猜测数字。

## 已知限制

- Windows 检出本仓库会因 `archives/l/libXext` 与 `archives/l/libxext` 大小写冲突显示脏文件，与本适配无关，Linux 真机不受影响。

# libcoap 4.3.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64, Conan 2.29.1)
- 状态: built

## 编译步骤

```bash
conan create archives/l/libcoap/4.3.4 -pr:h=ohos-aarch64
```

配方要点：
- `cmake_layout()` + `CMakeToolchain`/`CMakeDeps`；`BUILD_SHARED_LIBS=OFF` + `CMAKE_POSITION_INDEPENDENT_CODE=ON`。
- `ENABLE_TESTS=ON`（上游 CUnit 测试，本包的核心验证路径）；`ENABLE_EXAMPLES=OFF`、`ENABLE_DOCS=OFF`（examples 不打包、避免 doxygen 依赖）。
- DTLS/TLS 保持上游默认关闭（openssl/gnutls/mbedtls/tinydtls 均不引入，保持包最小依赖面）。
- 上游 `testdriver` 裸链 `-lcunit`（无 find_package），`generate()` 从依赖 `cunit/2.1.3` 的 `cpp_info` 取 include/lib 目录注入 `CMAKE_C_FLAGS`/`CMAKE_EXE_LINKER_FLAGS`（依赖私有 prefix，符合 R49）。
- `build()` 内真实执行 testdriver 并解析 CUnit `Run Summary` 的 tests 行：Failed>0 或 ran<total 即抛错（CUnit 测试失败不影响退出码，必须看汇总行）。
- 打包：`include/coap3/*.h`（静态头）+ 构建生成的 `coap_config.h`、`include/coap3/coap.h` + `libcoap-3.a`（os.walk 匹配）+ LICENSE；`cpp_info.libs=["coap-3"]`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试是 CUnit testdriver 可执行文件，无 add_test/ctest 注册 | 上游 CMake 只把 testdriver 作为构建目标，测试靠手工运行 | 配方 build() 中显式执行 testdriver 并解析汇总行判定（Failed 数），见上 |
| 2 | CUnit 测试失败不影响进程退出码（CU_basic_run_tests 返回框架错误码） | CUnit 设计如此 | 不能只看退出码，解析 `Run Summary` 的 tests 行（total/ran/passed/failed）判定 |
| 3 | testdriver 头文件与链接找不到 cunit | 上游假定 Debian 式系统路径（`-lcunit` + /usr/include） | 从依赖 cpp_info 注入 -I/-L（R49 私有 prefix 形态） |

## 上游测试清点（R51）

- N_static = **167**：tests/ 下 10 个 CUnit 套件的注册宏统计（encode 16 / error_response 8 / options 43 / oscore 13 / pdu 41 / sendqueue 10 / session 6 / tls 2 / uri 24 / wellknown 4）。
- 执行结果（配方 build() 内 testdriver 实测）：**154/154 全部执行并通过**（failed 0）。
- 未执行 13 项（test_oscore，逐项同因）：OSCORE 套件注册条件为 `COAP_OSCORE_SUPPORT`，其依赖 DTLS/crypto 后端；本包为消除"系统 openssl 隐性依赖"（find_package(OpenSSL) 摸到设备系统路径且无法向消费者传递）显式 `ENABLE_DTLS=OFF`，该 13 项不注册。如后续迭代引入 openssl 依赖可恢复 167 项。

## 验证结果

```bash
# 设备侧（OHOS aarch64）
conan create archives/l/libcoap/4.3.4 -pr:h=ohos-aarch64
# build(): CUnit testdriver（执行/通过数以 Run Summary 为准，见 conan create 日志）
# test_package: test_libcoap（9 项断言，PDU 回环）
```

## 注意事项

- `tests/test_common.h` 由 configure_file 生成到源码树内（上游行为），conan 源目录内完成，不外溢。
- 上游库目标名/产物名带版本（`coap-3`），`cpp_info.libs=["coap-3"]`；如后续版本改名需同步。
---

**编译结束**: 2026-09-16 01:34
**最终状态**: built

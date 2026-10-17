# cyrus-sasl-scram

Cyrus SASL 的 **SCRAM** 机制包（SCRAM-SHA-1 / SCRAM-SHA-224 / SCRAM-SHA-256 /
SCRAM-SHA-384 / SCRAM-SHA-512，RFC 5802 / RFC 7677），面向 HarmonyOS PC（aarch64）。

## 说明

- 与 `cyrus-sasl`、`cyrus-sasl-digestmd5`、`cyrus-sasl-crammd5`、`cyrus-sasl-ntlm`
  **同源同版本**（上游 `cyrus-sasl-2.1.28.tar.gz`），只是机制闭包不同：
  本包 `--enable-scram`，其余机制/后端全部关闭。
- 构建产物为**静态** `libsasl2.a`（`--disable-shared --enable-static --without-staticsasl`），
  SCRAM 通过 `lib/staticopen.h` 静态注册，**无运行期插件目录/dlopen 依赖**。
- 依赖 `openssl/3.5.6`：SCRAM 的 `Hi()`/HMAC/PBKDF2 密钥派生使用 OpenSSL EVP。

## 消费者用法（Conan 2）

```python
self.requires("cyrus-sasl-scram/2.1.28")
```

```cmake
set(BUILD_SHARED_LIBS OFF)          # 保持全静态，避免 DT_NEEDED libsasl2.so.3
find_package(cyrus-sasl-scram REQUIRED CONFIG)
target_link_libraries(app PRIVATE cyrus-sasl-scram::cyrus-sasl-scram)
```

## 测试

- 消费者测试：`test_package/`（`./test_scram` 8 项 + 鸿蒙特有静态注册断言，共 9 断言）。
- 上游测试：`utils/testsuite`（上游无 automake `make check`；19 阶段测试台）。
  逐项真实读数见 [2.1.28/reports/upstream-tests.md](2.1.28/reports/upstream-tests.md)。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 2.1.28 | built | 首个适配版本（静态 libsasl2.a + openssl/3.5.6） |

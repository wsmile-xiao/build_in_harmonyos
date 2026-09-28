# DRAFT：pkg_check_modules 只设复数变量而上游读单数变量 → 编译缺头文件

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `build-system, conan, cmake` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-libuhttpd-3.14.2-pkg-config-singular-include-var.kv`

---

**匹配关键词**：pkg_check_modules, OPENSSL_INCLUDE_DIR, openssl/ssl.h, plural vs singular, FindOpenSSL

## 错误签名（error_signature）

```text
openssl/ssl.h: No such file or directory|OPENSSL_INCLUDE_DIR.*empty|pkg_check_modules.*OPENSSL|Select OpenSSL as the SSL backend.*fatal error
```

## 错误摘录（error_excerpt）

```text
src/ssl/openssl.c:14:10: fatal error: 'openssl/ssl.h' file not found
```

## 根因（root_cause）

上游 CMake 用 `pkg_check_modules(OPENSSL openssl)` 探测 OpenSSL 时，pkg-config 只设置**复数**变量 `OPENSSL_INCLUDE_DIRS`/`OPENSSL_LIBRARIES`，但代码/子模块读取**单数**变量 `OPENSSL_INCLUDE_DIR`/`OPENSSL_LIBRARIES`（FindOpenSSL.cmake 风格），单数变量始终为空 → 编译缺头文件。

## 推荐方案（rec_approach）

Conan 配方 generate() 中从 `self.dependencies['openssl'].cpp_info` 显式注入单数变量：
```python
ossl = self.dependencies["openssl"].cpp_info
tc.variables["OPENSSL_INCLUDE_DIR"] = ";".join(ossl.includedirs)
tc.variables["OPENSSL_LIBRARIES"] = ";".join(ossl.libdirs)
```
再配合 `CMAKE_INCLUDE_PATH`/`CMAKE_LIBRARY_PATH` 供模块查找器（FindOpenSSL/FindLibev）使用。

## 验证（verification）

libuhttpd 3.14.2：注入 `OPENSSL_INCLUDE_DIR` 后 `conan create` 编译通过，xssl 静态库成功链接 openssl（OpenSSL 3.5.6 后端）。

## 适用边界（applicable_library_types）

cmake、openssl、pkg-config、ssl 类库，凡上游用 pkg_check_modules 探测后读单数变量的项目。

## 反例（counter_examples）

- 上游直接用 `find_package(OpenSSL)` 且读取复数变量时不适用
- pkg-config 已正确配置且代码读复数变量时无需注入

## 限制（limitations）

单数变量名因库而异（`SSL_INC`/`OPENSSL_INCLUDE_DIR` 等），需按上游实际读取的变量名注入。

---

*本文件由 `knowledge/drafts/DRAFT-libuhttpd-3.14.2-pkg-config-singular-include-var.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*

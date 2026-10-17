# DRAFT — 静态 OpenSSL 下上游错误注入测试重复符号：HUNTER_ENABLED 守卫跳过路径

> 状态: 草稿（基于 jwt-cpp 0.7.1 R01 真实证据，待查重/提升）。
> 依据: 测试统计以实际执行为准；上游官方静态构建守卫语义（OpenSSLErrorTest.cpp `#ifndef HUNTER_ENABLED`）。

## 真实问题（场景）

jwt-cpp 0.7.1 在 OHOS aarch64 静态构建（-DSTATIC libcrypto.a，Conan openssl/3.5.6.1）下，
构建上游测试 `jwt-cpp-test` 在链接阶段失败：

```
ld.lld: error: duplicate symbol: EVP_PKEY_CTX_new_from_name
>>> defined at OpenSSLErrorTest.cpp
>>>            CMakeFiles/jwt-cpp-test.dir/OpenSSLErrorTest.cpp.obj:(EVP_PKEY_CTX_new_from_name)
>>> defined at pmeth_lib.c
>>>            libcrypto-lib-pmeth_lib.o in archive .../lib/libcrypto.a
ld.lld: error: duplicate symbol: EVP_PKEY_CTX_new_from_pkey
ld.lld: error: duplicate symbol: OSSL_PARAM_BLD_new
```

## 根因

OpenSSLErrorTest.cpp 为触发/探测 OpenSSL 错误路径，自定义了与 libcrypto 相同的符号
（EVP_PKEY_CTX_new_from_name / EVP_PKEY_CTX_new_from_pkey / OSSL_PARAM_BLD_new 等）。
动态 .so 时用户自定义符号可覆盖库导出符号；静态 .a 时同一可执行文件内两处定义即重复。
上游官方对静态/Hunter 构建的处理（OpenSSLErrorTest.cpp 第 3 行注释 + tests/CMakeLists.txt
HUNTER 分支 `target_compile_definitions(jwt-cpp-test PRIVATE HUNTER_ENABLED=1)`）：

```cpp
#ifndef HUNTER_ENABLED // Static linking (which hunter always does) breaks the tests (duplicate definition), so skip them
```

即静态构建下跳过该文件是**上游官方语义**，非本库适配缺陷。

## 方案

按上游官方静态语义编译测试：给测试目标加 `-DHUNTER_ENABLED` 编译宏，等价于上游 Hunter
静态构建的官方跳过路径（该文件 42 个用例按官方设计不参与静态构建），其余 108 个用例
正常编译运行。

```bash
cmake /path/to/jwt-cpp-src -DJWT_BUILD_TESTS=ON -DCMAKE_CXX_FLAGS="-DHUNTER_ENABLED" ...
make -j4 jwt-cpp-test
./jwt-cpp-test   # 108 tests from 7 test suites ran. / PASSED 108 tests.
```

台账如实记录：OpenSSLErrorTest 42 项硬阻塞（静态重复符号，上游官方跳过），计入分母不计通过；
全量通过率 108/180 = 60%，实际运行通过率 108/108 = 100%。

## 验证

- 运行日志 SHA-256: `eb59683436aa297eeb0ce00e0e5e34e5287d83f3aad3e7cbfede537e3c0851a4`
- 结果: `[==========] 108 tests from 7 test suites ran. / [  PASSED  ] 108 tests.`（exit 0）

## 适用边界

- 适用: 依赖 OpenSSL、上游测试含错误注入自定义符号、静态 libcrypto 构建的 C/C++ 库。
- 不适用: 上游测试未定义与 libcrypto 冲突符号（无此问题）；动态 libcrypto 场景（无重复定义）。

## 查重

搜索范围: `knowledge/drafts/` + `knowledge/graph/` + `knowledge/doc/`
（grep `duplicate symbol|HUNTER_ENABLED|EVP_PKEY|错误注入|static libcrypto`）。
命中:
- E163（`__packed` 重复符号，OHOS 内核头 binder.h/userfaultfd.h 根因）——异根因。
- E412（configure 可选 OpenSSL 后端自动探测，缺失/未声明链接需求）——异根因。
- E235（OHOS OpenSSL getrandom 种子）——异主题。
**均未专门覆盖「上游错误注入测试在静态 OpenSSL 下重复符号 + HUNTER_ENABLED 守卫」——本草稿为新增知识，无重复条目。**
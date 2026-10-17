# libmongocrypt 1.20.1 适配笔记

## 编译环境

- 构建系统: CMake（上游 3.15+）
- 编译器: clang 15.0.4，`--target=aarch64-unknown-linux-ohos`（harmonybrew ohos-sdk@26.0.0.18）
- 依赖: `openssl/3.5.6`（制品仓已发布，真机 `conan download` 命中预编译包，无需现场编）
- 真机: HarmonyOS PC / HongMeng Kernel 1.12.0 / aarch64，2026-09-19
- 状态: 编译 + 上游官方测试 + 消费者测试全部实跑通过

## 构建配方要点

- 上游 1.20.1 以 vendored 方式构建 libbson：`cmake/FetchMongoC.cmake` 的
  `MONGOC_FETCH_TAG_FOR_LIBBSON = 2.3.3`（`etc/purls.txt` 记 `pkg:github/mongodb/mongo-c-driver@2.3.3?#src/libbson`）。
  配方在 `source()` 里按该确切 tag 预解到 `mongo-c-driver/`，并传 `MONGOCRYPT_MONGOC_DIR`，
  使 CMake 不走 FetchContent 联网（真机访问 github.com 常被墙）。
- 源码用 codeload 双源（`https://`，无第三方镜像）；codeload URL 末段是 tag 名、没有 `.tar.gz`
  后缀，必须 `get(..., filename="libmongocrypt-1.20.1.tar.gz")` 显式声明归档类型，否则 `BadZipFile`。
- `-DBUILD_VERSION=1.20.1`：tarball 无 git，上游靠 git describe 推版本。
- `-DOPENSSL_ROOT_DIR=<openssl 包目录>`：上游用 `include (FindOpenSSL)` 模块而不是 config 包，
  只认 `OPENSSL_ROOT_DIR`；因此依赖必须显式指向 conan 包，不能依赖环境里的 `~/.harmonybrew`。
- `-DBUILD_TESTING=ON -DENABLE_ONLINE_TESTS=OFF`：打开上游测试，关掉需要真实 KMS/mongod 的在线用例。
- `-DMONGOCRYPT_ENABLE_DECIMAL128=OFF`：见问题 #3。
- `build()` 里真实执行上游 ctest（不是 test_package 代替）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `kms_crypto_libcrypto.c:22: 'openssl/sha.h' file not found` | 上游 `kms-message/CMakeLists.txt` 只给 `kms_message`/`kms_message_static` 加了 `OPENSSL_INCLUDE_DIR`，漏了 OBJECT library `kms_message_obj`（OBJECT 库不继承消费方的头路径） | `patches/0001-kms-message-obj-openssl-include.patch` 给该 target 补 `target_include_directories` |
| 2 | `os_dll.c:112: call to undeclared function 'dlinfo'` | OHOS `<dlfcn.h>` 不声明 `dlinfo`，`libc.so` 也不导出（`llvm-nm` 实测只有 `dladdr`/`dl_iterate_phdr`）；且 `dlopen` 句柄是脱敏指针（实测 `0x906a8f02f29aa087`，同模块 `dlpi_addr=0x5bb7000000`），所以 `handle==dlpi_addr` 的 musl 替代写法也不行 | `patches/0002-mcr_dll-path-via-dladdr-on-ohos.patch`：新增 `#elif defined(__OHOS__)` 分支，用 `dlsym`（`mongo_crypt_v1_status_create` / `mongocrypt_version`）+ `dladdr` 反查库路径 |
| 3 | 打开 Decimal128 后 `IntelRDFPMathLib20U2/LIBRARY/float128/architecture.h:716: error: Architecture must be specified` | 上游 vendored 的 Intel DFP 架构表没有 OHOS/aarch64 分支 | `-DMONGOCRYPT_ENABLE_DECIMAL128=OFF`；4 个 `*_decimal128` 用例因此被上游 `#if MONGOCRYPT_HAVE_DECIMAL128_SUPPORT()` 排除，已逐条记进 `test_package/MANIFEST.yml` |
| 4 | ctest 里 3 个用例报 `Error loading shared library libmongocrypt.so`（并连带报一串 `symbol not found`） | 真机实测链路：Conan 的 `conan_toolchain.cmake` **不写** `CMAKE_SYSTEM_NAME`（grep 无命中）→ CMake 按 `uname -s` 得到 `HarmonyOS` → CMake 只有 `Modules/Platform/OHOS.cmake`（`include(Platform/Linux)`），没有 `HarmonyOS.cmake` → 平台语义不加载（只警告、退出码 0）→ `CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG` 为空 → build-tree 可执行文件不写 RPATH（`link.txt` 里 `-Wl,-rpath` 0 次、`llvm-readelf` 无 RPATH/RUNPATH），且 `CMAKE_BUILD_RPATH` 被静默忽略 | `generate()` 里 `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"`（根因修法，恢复 RUNPATH 与 `DT_SONAME`）；`build()` 里另用 `LD_LIBRARY_PATH="<build/Release>" ctest` 兜底（路径是 Python 拼的字面量，避开 R33） |
| 5 | CMakeDeps 报 `Library 'bson-static-for-libmongocrypt' not found in package` | conan 的 `copy()` 用 fnmatch 匹配**相对 src 的完整相对路径**，只写裸文件名时子目录里的产物被静默漏拷 | `package()` 里对子目录产物改用 `*/名字` 模式 |

## 验证结果（2026-09-19 真机，同一次 `conan create` 日志）

```
conan create . -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=同 --build=missing --build=libmongocrypt/1.20.1
CREATE_EXIT:0
100% tests passed out of 8        # 上游 ctest 条目
Total Test time (real) = 7.33 sec
```

- 上游 `test-mongocrypt`（ctest 条目 `mongocrypt`）单独直跑：`TMC_EXIT:0`，
  **按用例名去重后 `begin` 294 个、`end` 294 个且完全配对**（`comm` 双向差集为空），
  日志里 `FAILED|Assertion|abort` 计数 0。
  口径：源码安装点 347（`INSTALL_TEST` 334 + `INSTALL_TEST_CRYPTO` 13，取数
  `grep -rhoE "INSTALL_TEST(_CRYPTO)?\(" test/*.c | wc -l`）→ 唯一用例名 295（`sort -u`）
  + main() 里字面名安装 6 = 301；本次配置未安装 7 个（4 个 Decimal128、2 个 CRYPTO_PROHIBITED、
  1 个 `#if defined(__GLIBC__)||defined(__APPLE__)`），301-7=294 与实测一致；
  「registered but NOT run」与「ran but not registered」两份清单逐条打印后正好是这 7 + 6 个。
- `test_kms_request` 40 个 `RUN_TEST` 用例通过。
- `mlib.path` / `mlib.str` / `mc-mlib.int128` / `example-state-machine` / `example-state-machine-static` 通过；
  `mc-dec128` 按上游自身逻辑打印 `@@ctest-skip@@`（Decimal128 未启用）并返回 0。
- 消费者（鸿蒙特有）测试：`# 23 checks, 0 failures` → `PASS`，
  其中包含一次真实 FLE1 local datakey 加密封装（AES-256-CBC + HMAC-SHA-512 走 openssl/3.5.6），
  并校验产物首 4 字节小端长度与文档长度自洽（确认是真 BSON）。
- 根因修法单独成立的实证（同一份构建目录）：`env -u LD_LIBRARY_PATH ctest` → `100% tests passed out of 8`；
  `example-state-machine` 的 ELF 现有 `(RUNPATH) Library runpath: [.../build/Release]`（1 次命中），
  `CMakeFiles/example-state-machine.dir/link.txt` 里 `-Wl,-rpath` 出现 1 次。修之前这三项分别是
  「3 条失败」「0 命中」「0 次」。配方仍保留 `LD_LIBRARY_PATH` 前缀作为兜底：CI 容器里的 cmake
  安装未必与真机 `~/.harmonybrew/share/cmake/Modules/Platform/OHOS.cmake` 同版本。
- 产物：`include/{mongocrypt,mongocrypt-compat,mongocrypt-config,mongocrypt-export}.h`、
  `lib/{libmongocrypt-static.a,libbson-static-for-libmongocrypt.a,libkms_message-static.a,libmongocrypt.so,libmongocrypt.so.0,libmongocrypt.so.0.0.0}`
  （补上 `CMAKE_SYSTEM_NAME` 后平台模块链加载，链接器才开始写 `DT_SONAME=libmongocrypt.so.0` 并生成版本化文件名）、
  `licenses/LICENSE`。无 `bin/`（在线用例关闭 → 不产 csfle 工具，避开 R38）。

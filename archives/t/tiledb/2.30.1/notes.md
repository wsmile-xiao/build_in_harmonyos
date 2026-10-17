# tiledb 2.30.1 适配笔记

## 编译环境

- 构建系统: cmake（源码根目录 `CMakeLists.txt`，无 configure 脚本）
- 编译日期: 2026-09-20
- 编译器: OHOS NDK clang（`ohos.toolchain.cmake`，`OHOS_ARCH=arm64-v8a`），C++20 强制
- 状态: built

## 编译步骤

配方 `build()` 不用 `CMakeToolchain`（tiledb 必须整体走 OHOS NDK toolchain），改为手工驱动 cmake：

```bash
# 1) CMakeDeps 生成 9 个依赖的 *-config.cmake 到 <build_folder>/generators
# 2) 自发现 ohos.toolchain.cmake：
#      tools.cmake.cmaketoolchain:user_toolchain conf → $OHOS_NDK_HOME/build/cmake/
#      → glob /data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/
# 3) 造 llvm-ranlib shim（OHOS SDK 只有 llvm-ar，用 `llvm-ar s` 顶替）
printf '#!/data/service/hnp/bin/bash\nexec %s s "$@"\n' "$NDK/llvm/bin/llvm-ar" \
    > "$build_folder/llvm-ranlib-shim" && chmod 0755 "$build_folder/llvm-ranlib-shim"

cmake -G "Unix Makefiles" -B "$build_folder/build-ohos" -S "$source_folder" \
  -DCMAKE_TOOLCHAIN_FILE="$ndk/build/cmake/ohos.toolchain.cmake" \
  -DCMAKE_AR="$ndk/llvm/bin/llvm-ar" -DCMAKE_RANLIB="$build_folder/llvm-ranlib-shim" \
  -DOHOS_ARCH=arm64-v8a -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=20 -DCMAKE_CXX_STANDARD_REQUIRED=ON \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=OFF -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_PREFIX_PATH="$build_folder/generators" \
  -DBlosc2_DIR=... -Dnlohmann_json_DIR=... -Dspdlog_DIR=... -Dzstd_DIR=... -Dfmt_DIR=... \
  -DOPENSSL_ROOT_DIR=... -DOPENSSL_INCLUDE_DIR=... \
  -DOPENSSL_CRYPTO_LIBRARY=.../libcrypto.a -DOPENSSL_SSL_LIBRARY=.../libssl.a \
  -DBZIP2_INCLUDE_DIR=... -DBZIP2_LIBRARIES=.../libbz2.a -DBZIP2_LIBRARY_RELEASE=... \
  -DLZ4_INCLUDE_DIR=...   -DLZ4_LIBRARIES=.../liblz4.a   -DLZ4_LIBRARY_RELEASE=... \
  -DZLIB_INCLUDE_DIR=...  -DZLIB_LIBRARIES=.../libz.a    -DZLIB_LIBRARY_RELEASE=... \
  -DTILEDB_WERROR=OFF -DTILEDB_S3=OFF -DTILEDB_AZURE=OFF -DTILEDB_GCS=OFF \
  -DTILEDB_SERIALIZATION=OFF -DTILEDB_WEBP=OFF -DTILEDB_TOOLS=OFF -DTILEDB_TESTS=OFF \
  -DTILEDB_ALLOW_REGEX_CHAR_PATH=ON

cmake --build "$build_folder/build-ohos" -- -j$(nproc)

# package(): cmake --install → package_folder，然后对 libtiledb.so 重新签名
llvm-objcopy --remove-section .codesign libtiledb.so
binary-sign-tool sign -inFile libtiledb.so -outFile libtiledb.so -selfSign 1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `concepts requires` / `std::span` 编译失败 | 顶层 `CMakeLists.txt` 硬编码 C++20，OHOS toolchain 默认 c++17 | 显式 `-DCMAKE_CXX_STANDARD=20 -DCMAKE_CXX_STANDARD_REQUIRED=ON` |
| 2 | `-Wunused-command-line-argument` 被升级为硬错误 | OHOS toolchain 注入 `--gcc-toolchain=<sdk>/llvm`，clang 在 OHOS 目标下不消费该参数；`TILEDB_WERROR` 把它当 error | `-DTILEDB_WERROR=OFF`（其余告警仍保留，不做全局 `-w`） |
| 3 | `BZip2::BZip2` / `LZ4::LZ4` / `ZLIB::ZLIB` / `OpenSSL::SSL` target 不存在 | CMake 4.1 的 `FindBZip2`/`FindLZ4`/`FindZLIB`/`FindOpenSSL` 只解析库变量、不生成 imported target；Conan 导出名是 `bzip2::bzip2` / `lz4::lz4` / `zlib::zlib` / `openssl::openssl` | 注入 `*_INCLUDE_DIR` + `*_LIBRARY_RELEASE` 后仍需 `add_library(<标准名> ALIAS <conan 名>)`（补丁 0001/0004/0006） |
| 4 | `find_package(Blosc2/fmt/nlohmann_json/spdlog/zstd)` 找不到 | CMake 4.1 CONFIG 模式不从 `CMAKE_PREFIX_PATH` 搜 `<pkg>-config.cmake`，必须逐个给 `<pkg>_DIR` | `-DBlosc2_DIR/-Dfmt_DIR/...` 全部指向 `build_folder/generators` |
| 5 | `OpenSSL::SSL/Crypto` 无 imported location | OHOS 的 openssl 包只有静态 `libssl.a`/`libcrypto.a`，`FindOpenSSL` 在 `OPENSSL_CRYPTO_LIBRARY` 未入缓存时不建 target | 显式给 `OPENSSL_ROOT_DIR` + `OPENSSL_INCLUDE_DIR` + 两个 `*_LIBRARY` 指向真实 `.a` |
| 6 | `indexed_list.h` / `dd_compressor.cc` 报 dependent type 缺 `typename` | 上游按 libstdc++ 宽松解析写依赖类型名，OHOS libc++（clang 15）要求显式 `typename` | 补丁 0002 / 0005 补 `typename` |
| 7 | `fmt::format("{:%Y-%m-%d %X}", time_point)` 编译失败 | fmt 12.x 移除了 `std::chrono` 的内置格式化（duration 与 time_point 都不能直接传） | 补丁 0003：`duration_cast` 成秒数 double 手动格式化；time_point 走 `to_time_t` + `localtime_r` + `strftime` |
| 8 | `uri_ <=> uri.uri_` 编译失败 | OHOS libc++（clang 15）对 `std::string` 的 `operator<=>` 支持不全 | 补丁 0007：改用 `<` / `>` 组合显式返回 `std::strong_ordering` |
| 9 | 链接期缺 `llvm-ranlib` | OHOS SDK 的 llvm 工具链不含 `llvm-ranlib` | 用 `llvm-ar s` 造 `llvm-ranlib-shim`，`-DCMAKE_RANLIB` 指向它 |
| 10 | 设备侧 `dlopen("libtiledb.so")` 失败 | HarmonyOS PC 要求 `.so` 签名，未签名/旧签名段不合法 | `package()` 里 `llvm-objcopy --remove-section .codesign` 后 `binary-sign-tool -selfSign 1` 重签 |

## 源码修改

7 个补丁，全部为可移植性修复（无平台宏、无空壳分支）：

| 补丁 | 目标文件 | 内容 |
|------|----------|------|
| `0001-tiledb-CMakeLists.txt.patch` | `tiledb/CMakeLists.txt` | 顶层补 ZLIB/BZip2/LZ4/Zstd imported target 别名 + OpenSSL::SSL/Crypto 别名 |
| `0002-tiledb-common-indexed_list.h.patch` | `tiledb/common/indexed_list.h` | `iterator` / `const_iterator` 的 `Elements::iterator` 等依赖类型补 `typename` |
| `0003-tiledb-common-log_duration_instrument.h.patch` | `tiledb/common/log_duration_instrument.h` | 析构函数里 duration/time_point 改显式转换后格式化 |
| `0004-tiledb-sm-compressors-CMakeLists.txt.patch` | `tiledb/sm/compressors/CMakeLists.txt` | compressors 子工程补 BZip2/ZLIB/LZ4 别名 |
| `0005-tiledb-sm-compressors-dd_compressor.cc.patch` | `tiledb/sm/compressors/dd_compressor.cc` | `common::integral_64<T>::type` 补 `typename` |
| `0006-tiledb-sm-crypto-CMakeLists.txt.patch` | `tiledb/sm/crypto/CMakeLists.txt` | crypto 子工程补 OpenSSL::SSL/Crypto 别名（含 MODULE 回退） |
| `0007-tiledb-sm-filesystem-uri.cc.patch` | `tiledb/sm/filesystem/uri.cc` | `operator<=>` 改 `<` / `>` 组合 |

## 上游测试审计

- 源码 tarball：`https://github.com/TileDB-Inc/TileDB/archive/refs/tags/2.30.1.tar.gz`，
  sha256 `36381f9eaa2a6defc8990aa1a95d1f0e87971748a50bf6fb705bf032ac7384cf`（实测下载一致）。
- 清点方式（与 PR 正文同一取数命令，避免口径不一致）：
  - 全树注册宏口径（申报 N）：`find . \( -name '*.cc' -o -name '*.cpp' \) | xargs grep -hoE 'TEST_CASE(_METHOD)?\(' | wc -l` = **2320**。
  - `test/src` 口径：`grep -rhE 'TEST_CASE(_METHOD)?\(' test/src --include='*.cc' | wc -l` = **1317**
    （其中唯一 `TEST_CASE(` 404、唯一 `TEST_CASE_METHOD(` 913）。
  - 编译单元口径（辅助，非申报口径）：`test/CMakeLists.txt` 基础测试源清单 = 95 个 `.cc`；
    加 `TILEDB_CPP_API` 48 个 = 143；`TILEDB_SERIALIZATION` 的 4 个与本配置无关不计入。
- 申报说明：正文按全树注册宏行数口径申报 N=2320（含 TEST_CASE/TEST_CASE_METHOD），
  平台复查口径（Septest 2227 / 独立复核 1317 / 1310）均 ≤ 申报值，无少报。
- ctest 注册项：`test/CMakeLists.txt` 共 4 个 `add_test` —— `tiledb_unit`（始终注册）、
  `tiledb_timing_unit`（需 `libfaketime`）、`tiledb_unit_nightly`（需 `TILEDB_NIGHTLY_BUILD`
  环境变量）、`unit_arrow`（需 `TILEDB_ARROW_TESTS` + pybind11）。
- 回归测试：`test/regression/` 下有 21 个 `.cc` 文件，自带 `CMakeLists.txt`。
- **未纳入本次 OHOS 构建**：上游 `tiledb_unit` 目标硬链接 `Catch2::Catch2` 与
  `rapidcheck`（`test/CMakeLists.txt` 的 `target_link_libraries`），而 `rapidcheck` 未发布到
  ohpcd 制品仓，因此 `-DTILEDB_TESTS=OFF`。这是"缺制品仓依赖"的具体技术原因，不是"没环境"。
- 消费者侧验证改由 `test_package` 承担（见下）。

## 依赖版本

9 个强制第三方依赖，全部来自 ohpcd 制品仓（`conan download --only-recipe` 逐个核验 rc=0）：

- blosc2/3.2.3、bzip2/1.0.8.2、lz4/1.10.0.3、openssl/3.5.6.1.2
- nlohmann_json/3.12.0、spdlog/1.17.0、fmt/12.2.0、zlib/1.3.1.2、zstd/1.5.7.1

`fmt` 是显式 requires 而非纯传递依赖：tiledb 公共头直接 `#include <fmt/format.h>`。

## 验证结果

- 源码校验：conandata.yml 的 sha256 与实测下载一致（见上）。
- 补丁可应用性：7 个补丁按 conandata 声明顺序对 TileDB 2.30.1 原始 tarball
  `git apply -p1` 全部成功；应用后源码树内 `__OHOS__` 出现次数为 0。
- 消费者测试（test_package）：`test.c` 调 `tiledb_version` / `tiledb_config_alloc` /
  `tiledb_ctx_alloc_with_error` / `tiledb_ctx_free` / `tiledb_config_free`，退出码 0，
  4/4 断言通过。
- CI：build `#53884`（`OpenHarmonyPCDeveloper-CI-039`）PASSED，构建包
  `archives/t/tiledb/2.30.1`，Conan test_package 通过、L0 门禁通过、L1 门禁通过。

## 交付物

- `libtiledb.so`（含 C API），已用 `binary-sign-tool -selfSign 1` 签名。
- 头文件 `tiledb/tiledb.h` 及 `tiledb/api/**`。
- 库类型包，不含可执行文件，因此不需要 `commands.json`（R38）。

## 注意事项

- 上游 C++ 测试套件本次**未运行**（rapidcheck 未发布 → `TILEDB_TESTS=OFF`）。PR 正文里的
  通过率必须如实写"上游 0/N′"，不得用 404/406 之类的上游用例数暗示已执行。
- `TILEDB_WERROR=OFF` 是必要妥协：OHOS toolchain 的 `--gcc-toolchain` 参数会产生
  `-Wunused-command-line-argument`，无法在不改 NDK 的前提下消除。
- openssl 在 OHOS 只有静态库，配方显式把 `OPENSSL_CRYPTO_LIBRARY` / `OPENSSL_SSL_LIBRARY`
  指向 `libcrypto.a` / `libssl.a`；换 openssl 版本时需同步确认这两个文件名。
- 消费者必须继承依赖链的 include/lib 路径（`package_info()` 用 `collect_libs` 收集）。

---

**编译结束**: 2026-09-20
**最终状态**: built

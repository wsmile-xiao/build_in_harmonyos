# tdlib 1.8.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 `CMakeLists.txt`，`project(TDLib VERSION 1.8.0 LANGUAGES CXX C)`）
- 编译日期: 2026-09-24
- 编译器: clang / clang++ 15.0.4（OHOS SDK `ohos-sdk_26.0.0.18`，`-stdlib=libc++`）
- 宿主/目标: HarmonyOS PC aarch64（`uname -s` = HarmonyOS；Conan profile `ohos-aarch64` 未设置
  `CMAKE_SYSTEM_NAME`，故 `CMAKE_CROSSCOMPILING=FALSE`，上游 `test/`、`benchmark/`、`tg_cli` 均按
  上游默认被构建）
- conan 2.29.1（OHOS 适配版），remote `ohpcd`
- 状态: built（本地全部门禁通过，停在待确认，未 commit/push/PR）

## 编译步骤

```bash
# 1) 依赖（W0 已核验可消费，本步骤只做接线，不跳过任何依赖）
conan install --requires="openssl/3.5.6#748fc4deb56588d6f8ce900b21e8eb0a" --requires="zlib/1.3.2" \
  -g CMakeToolchain -g CMakeDeps -pr:h/-pr:b=ohos-aarch64 -r=ohpcd --build=never

# 2) 真实构建（探索阶段；等价于配方 build() 的内容）
cmake -S <src> -B build -DCMAKE_TOOLCHAIN_FILE=<generators>/conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DOPENSSL_FOUND=TRUE -DOPENSSL_ROOT_DIR=<openssl pkg> -DOPENSSL_INCLUDE_DIR=<...>/include \
  -DOPENSSL_CRYPTO_LIBRARY=<...>/lib/libcrypto.a -DOPENSSL_SSL_LIBRARY=<...>/lib/libssl.a \
  -DOPENSSL_LIBRARIES='<...>/lib/libssl.a;<...>/lib/libcrypto.a'
make -j20 && make install

# 3) 配方化验证（与 CI 同源）
conan create . -pr:h/-pr:b=ohos-aarch64 -r=ohpcd --build='tdlib/*'
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed from CMake.`（configure exit=1） | tdlib 1.8.0（2021）声明 `cmake_minimum_required(VERSION 3.0.2 FATAL_ERROR)`，OHOS 主机自带 CMake 4.1.2 已移除 <3.5 兼容层 | 传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 官方逃生口）。**不能放进 conan toolchain 文件**：CMake 在第一个 `project()` 时才加载 toolchain，而 `cmake_minimum_required` 是其之前求值的，实测 toolchain 内设置无效（`logs/19/20-*.log`）；故用 `cmake.configure(cli_args=[...])`。未改动上游文件 |
| 2 | `auto/mime_type_to_extension.gperf:47:20: error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]`（9 errors，make exit=2） | 上游 `tdutils/generate/CMakeLists.txt` 用 gperf 在构建期生成 MIME 表，gperf 输出仍含 `register`（C++17 已移除）。tdlib 自己追加 `-std=c++14` 并只抑制了 `-Wdeprecated-register`，但 Conan profile 固定 `compiler.cppstd=17`，CMake 把标准开关放在工程 flag 之后，实际编译为 C++17（`compile_commands.json` 实测两条 `-std=`，后者生效） | `tc.extra_cxxflags.append("-Wno-register")`（经 Conan toolchain 注入，不依赖 shell 环境变量，符合 R33）。未改动上游文件与生成文件 |
| 3 | `Can't find OpenSSL: stop TDLib building`（ZLIB 找到了，OpenSSL 没有） | tdlib 只认经典 FindOpenSSL 变量名（`OPENSSL_FOUND` / `OPENSSL_INCLUDE_DIR` / `OPENSSL_CRYPTO_LIBRARY` / `OPENSSL_SSL_LIBRARY`）；Conan CMakeDeps 只产出小写 `openssl_*`，且 OHOS profile 打开 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，config 模式"找到了"却不会设置大写变量 | `generate()` 中把经典变量接到 Conan 包（ohpcd openssl 为静态 `libcrypto.a`/`libssl.a`），并置 `OPENSSL_USE_STATIC_LIBS=True`。zlib 无需接线：其 Conan 包生成 `ZLIBConfig.cmake`，本已定义 `ZLIB_FOUND`/`ZLIB_INCLUDE_DIR`/`ZLIB_LIBRARIES` |
| 4 | `conan create ... --build=never` → `ERROR: Missing prebuilt package for 'tdlib/1.8.0'` | `--build=never` 也禁止构建当前包自身 | 改为 `--build='tdlib/*'`（只允许从源码构建被测包，依赖仍强制走预编译包，等价于 R36 口径，不新增 `--build=missing` 绕过） |
| 5 | W3 本地 CI 的 L5 门禁报 `L5a: libtdjson.so 缺少 DT_SONAME` + `L5c: 1 个 .cmake 文件含 IMPORTED_NO_SONAME TRUE` | CMake 没有 HarmonyOS 平台模块（configure 期报 `System is unknown to cmake, create Platform/HarmonyOS`），`CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG` 始终为空 → 生成的共享库不带 SONAME，`install(EXPORT)` 生成的 `TdTargets-release.cmake` 被打上 `IMPORTED_NO_SONAME TRUE` | 用 CMake 官方钩子 `CMAKE_USER_MAKE_RULES_OVERRIDE_{C,CXX}` 指向 `generate()` 写入的规则文件，恢复 `-Wl,-soname,`。未改动上游文件 |

## 源码修改

**无。** 上游源码零修改，`patches/` 为空；四处适配全部落在构建配置层
（CMake policy 逃生口、`-Wno-register`、经典 OpenSSL 变量接线、HarmonyOS 共享库 SONAME 规则）。

> 说明：`tdutils/generate/auto/*.cpp` 与 `*.gperf` 是**构建期由 gperf 生成**的文件
> （生成目标写在源码树里），不属于补丁内容，已在归档前从 `.work` 还原/清除。

## 依赖版本

| 依赖 | 版本 | 类型 | 消费方式 |
|------|------|------|----------|
| openssl | 3.5.6（recipe rev `748fc4de…` 固定） | 第三方·强制（构建期 + 运行期） | ohpcd 预编译静态包 `libcrypto.a`/`libssl.a`，静态链入 `libtdjson.so`，产物无 `libssl.so`/`libcrypto.so` 依赖 |
| zlib | 1.3.2 | 第三方·强制 | ohpcd 预编译静态包 `libz.a` |
| pthread / libc / libm / libdl / librt | 系统自带 | 平台 | 不计入第三方 |
| crc32c / abseil | 未启用（上游可选） | 可选 | `TD_HAVE_CRC32C`/`TD_HAVE_ABSL` 未定义，对应 2 个用例不编入 |

## 上游测试（OHOS 实际执行）

测试入口：`test/CMakeLists.txt:74` `add_test(run_all_tests run_all_tests)`（CTest 唯一注册项）。

| 测试程序 | 命令 | 用例数 | 通过 | 失败 | 跳过 | 退出码 |
|---|---|---|---|---|---|---|
| run_all_tests | `ctest --output-on-failure` | 208（编入） | 208 | 0 | 0 | 0 |
| test-tdutils | `./test-tdutils` | 109 | 109 | 0 | 0 | 0 |
| test-crypto | `./test-crypto` | 独立演示程序（无计数） | — | 0 | — | 0 |
| test-online | `./test-online` | 需 my.telegram.org api-id/api-hash | — | — | 未执行 | 1 |

- 上游声明用例总数 = **213**（210 个 `TEST(Suite, Name)` 宏 + 3 个 `RegisterTest<T>`），
  其中 **5 个被上游编译期守卫排除**，未编入任何二进制：
  `Test_Crypto_crc32c` / `Test_Crypto_crc32c_benchmark`（`#if TD_HAVE_CRC32C`，crc32c 未启用）、
  `Test_Http_Darwin`（`#if TD_DARWIN_WATCH_OS`）、`Test_Misc_to_wstring`（`#if TD_WINDOWS`）、
  `Test_SetWithPosition_stress`（`#if !TD_CLANG`）。
- 因此实际编入 208 个并**全部通过**（通过率 208/208 = 100%，无跳过、无失败、无跳过项漏报）。
- `test-online` 是上游自带的交互式真实 Telegram 客户端测试器，启动即要求
  `api-id`/`api-hash`（`You must provide valid api-id and api-hash obtained at https://my.telegram.org`），
  属上游设计约束，本环境无凭据，未执行。

## 验证结果

```bash
$ conan create . -pr:h/-pr:b=ohos-aarch64 -r=ohpcd --build='tdlib/*'      # exit 0
$ ctest --output-on-failure                                              # run_all_tests 208/208, exit 0
$ ./test-tdutils                                                         # 109/109, exit 0
$ ./test-crypto                                                          # exit 0
$ python3 scripts/ohc-run.py conan-verify tdlib 1.8.0                    # G0-G4 全 PASS
$ JUNK_PR_DIFF=<pr 文件清单> python3 scripts/ohc-run.py finish tdlib 1.8.0 built
    → W3 本地 CI 模拟通过：L0=pass L1=pass L2=skip(no bin/) L4=pass L5=pass
      JC=pass（0 杂项） KC=pass（0 错误） Pass rate 100% (1/1)
    → .ci-result.json: exit_code=0（integrity_hash + log_sha256）
```

产物关键属性（`llvm-readelf -d lib/libtdjson.so`）：
```
NEEDED  libc++_shared.so
NEEDED  libc.so
SONAME  libtdjson.so.1.8.0      ← L5 修复点
（无 RPATH/RUNPATH；openssl/zlib 已静态链入）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libtdjson.so` → `libtdjson.so.1.8.0` | 公共 JSON/C API 共享库（SONAME `libtdjson.so.1.8.0`；DT_NEEDED 仅 `libc++_shared.so`, `libc.so`；无 RUNPATH） |
| `lib/libtdjson_static.a` / `libtdjson_private.a` / `libtdclient.a` / `libtdcore.a` / `libtdapi.a` / `libtdutils.a` / `libtdactor.a` / `libtdnet.a` / `libtdsqlite.a` / `libtddb.a` | 静态库工具链 |
| `include/td/telegram/{td_json_client.h,td_api.h,td_api.hpp,Client.h,Log.h,...}`、`include/td/tl/TlObject.h` | 公共头文件 |
| `lib/cmake/Td/TdConfig.cmake` + `TdTargets*.cmake` | 上游 CMake 包（`Td::TdJson` / `Td::TdJsonStatic` / `Td::TdStatic`） |
| `lib/pkgconfig/*.pc` | 11 个 pkg-config 文件 |

## 注意事项

1. `tdlib` 的 `test/`、`benchmark/`、`tg_cli` 只在**非交叉编译**时构建。OHOS Conan profile 不设置
   `CMAKE_SYSTEM_NAME`，所以宿主即目标、`CMAKE_CROSSCOMPILING=FALSE`，测试可以原生执行；若将来
   profile 改为显式交叉（设置 `CMAKE_SYSTEM_NAME`），测试目标会整体消失，需另行处理。
2. 构建期 gperf 会在**源码树**内生成 `tdutils/generate/auto/{mime_type_to_extension,extension_to_mime_type}.cpp`
   与同名 `.gperf`；这些是生成物，不应进入补丁或归档。
3. `test-online` 未执行（需真实 Telegram 凭据），上游 `test-crypto` 无 TestsRunner 计数，
   两者均已如实记录，未虚构数字。
---

**编译结束**: 2026-09-24 16:08
**最终状态**: built

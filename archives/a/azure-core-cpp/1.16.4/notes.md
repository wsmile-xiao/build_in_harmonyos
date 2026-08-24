# azure-core-cpp 1.16.4 Build Notes

## Source
- Official: https://github.com/Azure/azure-sdk-for-cpp (tag: azure-core_1.16.4)
- tarball: https://codeload.github.com/Azure/azure-sdk-for-cpp/tar.gz/refs/tags/azure-core_1.16.4
- SHA-256: 25f8badf23c66ae82debd95e0d074d6269b276e5fa2ce5d4d3cff38fda9ab8c2
- License: MIT

## Dependencies
- Threads (system)
- OpenSSL >= 3.5.6 (required on non-Windows for SHA hashing)
- curl >= 8.5.0 (required when BUILD_TRANSPORT_CURL=ON)
- zlib >= 1.3.1 (runtime dependency)

## OHOS Build Configuration
- Compiler: clang-15 (OHOS NDK)
- libc++: yes
- C++ standard: 17
- Architecture: armv8
- Build type: Release
- Shared library: yes

## CMake Options
- BUILD_TRANSPORT_CURL=ON (curl HTTP transport)
- BUILD_WINHTTP=OFF (Windows-only)
- DISABLE_RUST_IN_BUILD=ON (no Rust in OHOS)
- DISABLE_AMQP=ON
- DISABLE_AZURE_CORE_OPENTELEMETRY=ON
- WARNINGS_AS_ERRORS=OFF
- BUILD_TESTING=OFF (separate test step)

## OHOS 限制记录

### 运行时限制
- `/tmp` 只读（OHOS 沙箱）→ 所有需要临时文件的工具（gtest 流捕获、mkstemp）需设置 `TMPDIR="$HOME/tmp"`
- GitHub 直连不可达（`github.com port 443 timeout`）→ 使用 `codeload.github.com` 替代
- ELF 需要 `binary-sign-tool` 签名（`llvm-objcopy --remove-section .codesign` + `sign -selfSign 1`）
- CMake 平台 `CMAKE_SYSTEM_NAME=HarmonyOS` 不被多数上游 CMake 模块识别（`if(WIN32) elseif(UNIX) else() FATAL` 陷阱）
- `find_package(OpenSSL)` 使用 FindOpenSSL 模块（系统路径）无法找到 Conan 提供的 openssl → 需 CMakeDeps 传递路径

### 编译限制
- OHOS clang15 + libc++ C++17 与上游 C++14 行为差异（`std::common_type<duration<long,ratio<1,10000000>>, duration<long long,ratio<1,1>>>` 触发类型不兼容）
- Conan 2 需要显式 `tools.build:compiler_executables` 指定 clang/clang++/llvm-ar/llvm-ranlib
- 上游 CMake FetchContent 从 GitHub 拉取依赖不可用（googletest、corrosion）

### 适配测试限制
- Azure 网络、凭据、云服务测试（http_test、bearer_token、curl_session、transport_adapter 等）需排除
- 上游测试需要 `_azure_BUILDING_TESTS` 定义访问测试私有 API
- gtest 流捕获在 `/tmp` 只读时崩溃，需 patch 支持 TMPDIR
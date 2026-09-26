# curl 8.22.0 adaptation notes

## 编译环境
- Build system: CMake
- Date: 2026-09-05
- Native validation compiler: GCC 11.4.0 (Linux host)
- Status: built (native, OHOS target smoke, and upstream closure validated; platform CI pending)

## 编译步骤

The codeload tag was unpacked with strip-root semantics. CMake was configured
with static libcurl, the curl executable, OpenSSL and zlib enabled, all other
optional compression/SSH/HTTP2/IDN/LDAP backends disabled, and manual/docs
targets disabled. The build and install ran single-threaded into the task F:
directory.

## 遇到的问题与解决方案

| # | Problem | Root cause | Resolution |
|---|---------|------------|------------|
| 1 | Autotools configure was absent | GitHub codeload tag omits generated files | Switched recipe to the upstream CMake project |
| 2 | CMakeToolchain has no extra_ldflags attribute | Flags are configured through CMake cache variables | Set CMAKE_C_FLAGS and CMAKE_EXE_LINKER_FLAGS |
| 3 | Host brotli/zstd were auto-detected | Optional CMake dependency options default to ON | Set CURL_BROTLI=OFF and CURL_ZSTD=OFF |

## 源码修改

No source patches were required.

## 依赖版本

* zlib/1.3.2 (OHOS armv8 binary verified with --build=never)
* openssl/3.5.8.1 (OHOS armv8 binary verified with --build=never)

## 验证结果

```text
cmake configure: PASS (OpenSSL, zlib; brotli/zstd disabled)
cmake --build --parallel 1: PASS
cmake --install: PASS
libcurl test.c: PASS (version/easy handle/file transfer)
curl --version: PASS (8.22.0-DEV, OpenSSL, zlib)
OHOS W3 r002: PASS for target smoke (AArch64 curl CLI plus libcurl consumer,
self-sign, one launch, target_tests=3/3, target_rc=0, stderr=0,
processes_zero=true); full upstream tests remain a separate gate.
The exact remote task root was then removed and independently read back absent
after the RELEASED receipt.
```

## 上游测试边界

The first WSL-on-DrvFs run reported a 1710-case denominator but test 762
failed because `/mnt/f` clamps its 1940 mtime to epoch zero. To preserve the
upstream assertion, the same source and CMake options were rebuilt inside a
task-private ext4 image stored under F:. That run considered 2072 tests, marked
490 capability-specific cases skipped, and completed the required inventory as
1582/1582 OK (100%), including test 762. The ext4 run is the authoritative
host upstream evidence; the DrvFs result remains a diagnostic boundary only.

## Conan create 边界

The Linux host `conan create` attempt resolved the curl recipe and both exact
dependency revisions, but ohpcd has no x86_64 host binaries for zlib/1.3.2 or
openssl/3.5.8.1. Building the OpenSSL dependency from source stopped in its
own recipe because `_configure_target()` compares the invalid Conan setting
value `aarch64`. This is a dependency-recipe blocker for the optional native
Conan reproduction; the OHOS W0 binary closure remains independently PASS and
the target-platform CI must use that published closure.

## 交付物

No package archive was uploaded during this pre-PR validation.

## 注意事项

This is native-host evidence plus a separately recorded OHOS target smoke
transaction. The local upstream closure is complete on the task-private ext4
filesystem; the final result still requires exact-current-head platform CI.
Do not treat the DrvFs-bound test 762 failure as a curl code PASS or as a
platform CI result.

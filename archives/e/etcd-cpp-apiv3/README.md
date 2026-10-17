# etcd-cpp-apiv3

etcd-cpp-apiv3 is the C++ client library for etcd's v3 API (gRPC based). It
provides synchronous (`etcd::SyncClient`) and asynchronous (pplx-based)
clients for key/value operations, transactions, leases, locks and watch, on
top of generated `etcdserverpb` protobuf messages and gRPC stubs.

## Status

| Version | Status |
|---------|--------|
| 0.15.4  | built (2026-09-01, CMake, `BUILD_ETCD_CORE_ONLY=ON`) |

## OHOS PC adaptation

- **Core-only synchronous build.** `BUILD_ETCD_CORE_ONLY=ON` packages the
  gRPC/protobuf core (`etcd-cpp-api-core`) only. The upstream asynchronous
  client depends on cpprestsdk/pplx, which is not available in the OHOS PC
  package repository; the synchronous `etcd::SyncClient` path is fully
  functional without it.
- **Dependencies** (OHOS PC, arm64): `grpc/1.70.0`, `protobuf/33.6`
  (grpc's pinned version), `openssl/3.5.6`, `zlib/1.3.1`.
- **Patch** `0001-src-v3-Action.cpp.patch`: grpc >= 1.70 removed `GPR_ASSERT`
  from public headers; the patch adds an `#ifndef` fallback definition
  (mirrors the upstream master fix).
- **CMake >= 4 note**: the recipe sets `CMAKE_POLICY_VERSION_MINIMUM=3.5`
  because upstream declares `cmake_minimum_required(VERSION 3.3)`.
- **Consumer note** (cmake_find_mode=none): grpc and protobuf ship their own
  CMake configs (`gRPCConfig.cmake`, `protobuf-config.cmake`) with target
  names `gRPC::*` and `protobuf::libprotobuf`. CMakeDeps-generated
  `etcd-cpp-apiv3-config.cmake` expects `grpc::grpc`/`protobuf::protobuf`,
  so consumers must point `gRPC_DIR`/`Protobuf_DIR` (and friends) at the
  registry packages' `lib/cmake/<name>` and bridge the target names — see
  `test_package/` for a working example.

## Consumers

```cmake
find_package(etcd-cpp-apiv3 CONFIG REQUIRED)
target_link_libraries(app PRIVATE etcd-cpp-apiv3::etcd-cpp-apiv3)
```

## Upstream

- Homepage: https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3
- License: BSD-3-Clause

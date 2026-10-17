# BoringSSL

BoringSSL 是 Google 维护的 OpenSSL 分支，Chromium / Android 的 TLS 加密栈。

## Description

- 提供与 OpenSSL 相近的 C API（`libssl` / `libcrypto`），无稳定 ABI 承诺（上游明确不保证跨版本兼容）
- 交付静态库 `libcrypto.a` / `libssl.a` 与头文件 `include/openssl/*`
- 附带 `bssl` 命令行工具（sha256sum / genrsa / client / server / s_client 等）
- 本包固定上游 main 快照 `e98a6564`（2026-09-25）：上游版本号对应关系见 `manifest.yaml` 说明

## Versions

| Version | Status | Build Date | Notes |
|---------|--------|------------|-------|
| 0.20260927 | built | 2026-09-28 | CMake/Ninja 适配；无补丁；Go 非必需；R26 静态交付（系统同名库） |

## Dependencies

- **Build**: 无（仅需要 C/C++ 工具链 + CMake + Ninja；无需 Go/Perl）
- **Runtime**: libc、pthread

## Build System

CMake（上游唯一官方构建系统）。适配要点：

- 系统同名库（`/usr/lib/libssl.so.3`、`libcrypto.so.3`）→ 只构建静态库（R26）
- CMake 在 HarmonyOS 上判为未知系统 → recipe 别名 `CMAKE_SYSTEM_NAME=Linux`（E092）
- 上游测试为 gtest 独立二进制，`build()` 内实际运行 crypto_test/ssl_test

## Usage

```python
# conanfile.py
def requirements(self):
    self.requires("boringssl/0.20260927")
```

```cmake
find_package(boringssl REQUIRED)
target_link_libraries(app PRIVATE boringssl::boringssl)
```

CLI（要求 `bindirs` 在 PATH 中）：

```sh
echo -n hello | bssl sha256sum
bssl client --connect example.com:443
```

# mmkv

Tencent MMKV — 基于 mmap 的高性能 key-value 存储框架（微信同款）。

- **Homepage**: https://github.com/Tencent/MMKV
- **License**: BSD-3-Clause
- **Build system**: CMake（Core/ 子工程）
- **Language**: C++20

## Products

| Product | Description |
|---------|-------------|
| `libmmkv.a` | 静态库（Core 全部符号 + C bridge），官方 SDK 同形态 |
| `include/MMKV/` | 公共头（MMKV.h / MMKVPredef.h / MMBuffer.h / MiniPBCoder.h / MMKVHandler.h / MMKVBridge.h + OHOS 通路附加 MemoryFile.h / MMKVLog.h） |

C++ API（`<MMKV/MMKV.h>`）：`MMKV::mmkvWithID` / `set` / `getString` /
`getInt32` / `removeValueForKey` / `allKeys` 等。
C API（`<MMKV/MMKVBridge.h>`）：`mmkv_initialize` / `mmkv_with_id` /
`mmkv_encode_*` / `mmkv_decode_*` 等（供其他语言绑定）。

## Platform notes (OHOS)

- 工具链自动定义 `__OHOS__` → 上游 `MMKV_OHOS` 通路（零补丁）
- 日志走 hilog（`OH_LOG_Print`），消费者需链系统库 `libhilog_ndk.z.so`（recipe 已声明）
- CRC32 用 armv8 硬件指令，AES 用 armv8 crypto asm（`-march=armv8+crypto`）
- zlib CRC32 与 AES/MD5 均内嵌，无外部 conan 依赖

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| (none) | — | zlib/AES 内嵌；hilog/pthread 为 OHOS 系统库 |

## Versions

| Version | Status |
|---------|--------|
| 2.4.2 | built |

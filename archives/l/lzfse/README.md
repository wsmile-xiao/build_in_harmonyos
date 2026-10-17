# lzfse

## 简介
LZFSE is a Lempel-Ziv style data compression algorithm using Finite State Entropy coding, developed by Apple. It targets similar compression rates at higher compression and decompression speed compared to deflate, zlib, etc.

## OHOS 适配
- CMake build system works natively on HarmonyOS
- No external dependencies
- Produces static library liblzfse.a and command line tool lzfse

## 依赖
- 无

## 功能验证
- Round-trip compression/decompression test via lzfse_encode_buffer/lzfse_decode_buffer

## 参考
- [GitHub](https://github.com/lzfse/lzfse)
- [Apple Developer Documentation](https://developer.apple.com/documentation/compression/algorithm/lzfse)

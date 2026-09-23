# metrohash

MetroHash — a set of state-of-the-art non-cryptographic hash functions
(64-bit and 128-bit) by J. Andrew Rogers.

- 官方仓库：https://github.com/jandrewrogers/MetroHash
- 许可证：Apache-2.0
- 版本：1.1.3（标签 `v1.1.3`，commit `690a521d9beb2e1050cc8f273fdabc13b31bf8f6`）
- 目录结构：`archives/m/metrohash/{version}/`（conanfile.py + conandata.yml + test_package/ + manifest.yaml + notes.md）
- 说明：CRC 变体（metrohash128crc）依赖 x86 SSE4.2 intrinsics，aarch64 包不包含；上游 tarball 无构建系统，配方以自带 CMakeLists.txt 编译

# uvg266

`uvg266` is an open-source VVC (H.266) video encoder, developed by the
Ultra Video Group at Tampere University. It provides a C library
(`libuvg266`) and a command-line encoder (`uvg266`), licensed under
3-clause BSD.

## 适配说明（HarmonyOS PC, aarch64）

- 通过 CMake 构建（`BUILD_SHARED_LIBS=OFF` 静态库 + CLI）。
- 官方 release tarball 不含 `greatest` 测试子模块，配方按官方
  `.gitmodules` 钉扎提交补拉，保证上游单元测试可编译运行。
- 上游 shell 测试依赖外部工具 ffmpeg（生成输入）与 VTM
  DecoderAppStatic（解码校验，上游仅提供 x86-64 二进制）；ffmpeg 已从
  制品仓恢复并验证，DecoderAppStatic 因无 aarch64 制品按上游原生
  XFAIL_TESTS 机制排除，见 `0.8.1/notes.md` 测试台账。

## Versions

| Version | Status |
| --- | --- |
| 0.8.1 | published |

Homepage: https://github.com/ultravideo/uvg266
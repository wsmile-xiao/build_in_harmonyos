# atracdenc

ATRAC1 / ATRAC3 / ATRAC3PLUS 兼容音频编码器（自由 LGPL 实现），提供命令行工具
`atracdenc`，可将 44100Hz 16bit WAV 编码为 ATRAC1 (.aea)、ATRAC3 (.oma) 或
ATRAC3PLUS (.oma) 格式。

## 功能概述

- ATRAC1 (SP)、ATRAC3 (LP2)、ATRAC3PLUS 编码
- 支持 ATRAC1 解码
- OMA / AEA / RealMedia 容器输出
- 瞬态检测、BFU 数量搜索等高级选项（`--bfuidxconst` / `--bfuidxfast` 等）

## OHOS 适配

- CMake 无 HarmonyOS 平台模块（E092），配方在 `generate()` 中设置
  `CMAKE_SYSTEM_NAME=Linux`，使上游 `if (UNIX)` 分支生效（启用
  `find_package(GTest)` + `test/` 子目录 + ctest）。
- 上游 gtest 测试套件（`atracdenc_ut`、`at3plus_pqf_ut`、
  `at3plus_bitstream_ut`、`at3plus_gha_ut`、`at3plus_mdct_ut`、
  `bs_encode_ut`，共 80 个 TEST 用例）在 `build()` 内通过 ctest 完整执行，
  并输出 `HMBS_UPSTREAM_TEST_RESULT` 标记。
- man page 生成依赖 gzip：OHOS 的 toybox gzip 仅支持短选项，补丁
  `0001-man-page-gzip.patch` 改用 `find_program(gzip)` + `-c`，gzip 缺失时跳过
  man page（不影响二进制安装）。

## 依赖关系

- 编译依赖：libsndfile（pcm_io_sndfile.cpp 链接 libsndfile）
- 测试依赖：gtest/1.17.0

## 参考资料

- 上游仓库：https://github.com/dcherednik/atracdenc
- 上游文档：https://code.mastervirt.ru/atracdenc/about/man/atracdenc.1

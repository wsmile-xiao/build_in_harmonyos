# OpenAPV — 开源高级专业视频编解码器

## 软件简介

OpenAPV（Open Advanced Professional Video）是由 AcademySoftwareFoundation 开发的开源专业视频编解码器，支持 YCbCr 4:2:2 和 4:4:4 色度格式的 10/12bit 高质量视频编解码，主要用于专业视频制作和后期处理领域。

- **项目主页**: https://github.com/AcademySoftwareFoundation/openapv
- **许可证**: BSD-3-Clause
- **构建系统**: cmake
- **编程语言**: C

## 已编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 0.2.1.2 | published | 2026-06-10 | 首次编译，需 -DARM=TRUE 启用 NEON |

## 关键编译说明

- 鸿蒙平台上 cmake 无法自动检测 CMAKE_SYSTEM_PROCESSOR 为 aarch64（显示为 unknown），因此编译 ARM 平台时必须手动指定 `-DARM=TRUE` 以启用 NEON SIMD 源文件
- NEON 相关源文件位于 `src/neon/oapv_sad_neon.c` 和 `src/neon/oapv_tq_neon.c`
- 若不加 `-DARM=TRUE`，链接时会出现 `undefined symbol: oapv_tbl_fn_sad_16b_neon` 等错误
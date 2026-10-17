# libsquish 1.15 — 适配笔记

> 档案创建时间: 2026-08-24

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libsquish |
| 版本 | 1.15 |
| 状态 | built |
| 构建系统 | cmake |
| 源码路径 | https://downloads.sourceforge.net/project/libsquish/libsquish-1.15.tgz |
| sha256 | 628796eeba608866183a61d080d46967c9dda6723bc0a3ec52324c85d2147269 |

## 二、上游调查

- 官方源码仓库: SourceForge https://sourceforge.net/projects/libsquish/
- 社区镜像（未使用）: https://github.com/oblivioncth/libsquish（fork，版本号 v1.15.1.x 不同）
- 1.15 对应发布: SourceForge `libsquish-1.15.tgz`（2017-03-14）
- 构建系统: 同时提供 CMake 和 GNU Makefile，优先使用 CMake。
- 公开头文件: `squish.h`（namespace `squish`）
  - 常量: kDxt1, kDxt3, kDxt5, kBc4, kBc5, kColourClusterFit, kColourRangeFit 等
  - API: CompressMasked, Compress, Decompress, GetStorageRequirements,
          CompressImage, DecompressImage, ComputeMSE
- 生成库名称: `libsquish`（CMake target `squish` → libsquish.a）
- 外部依赖: 无

## 三、SSE/OpenMP 处理（ARM 平台）

上游 CMakeLists.txt 提供三个 option:
- `BUILD_SQUISH_WITH_SSE2`（默认 ON）→ x86 专属，定义 `SQUISH_USE_SSE=2 -msse2`
- `BUILD_SQUISH_WITH_ALTIVEC`（默认 OFF）→ PowerPC 专属
- `BUILD_SQUISH_WITH_OPENMP`（默认 ON）→ 可选并行加速

`config.h` 通过宏控制 SIMD 后端选择:
- `SQUISH_USE_SSE` → `simd_sse.h`（x86 intrinsics）
- `SQUISH_USE_ALTIVEC` → `simd_ve.h`（PowerPC）
- 二者均关闭 → `simd_float.h`（纯标量 portable 实现）

ARM/aarch64 平台决策:
- 关闭 SSE2（x86 专属，`-msse2` 在 ARM 上非法）
- 关闭 Altivec
- 关闭 OpenMP（可选优化，不必要，避免依赖 libomp）
- 使用 `simd_float.h` 标量后端，保证正确性与可移植性

通过 CMakeToolchain 变量传递，无需补丁源码。

## 四、补丁
- 无补丁。上游 CMake option 足以完成适配。

## 五、编译验证
- conan create 使用 ohos-aarch64 profile
- test_package 调用 squish::CompressImage / DecompressImage 进行 DXT1 压缩-解压往返验证

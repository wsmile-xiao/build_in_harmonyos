# libSvtAv1Enc (SVT-AV1)

**描述**: Scalable Video Technology for AV1 (SVT-AV1) - 高性能 AV1 视频编码器

SVT-AV1 是 Intel 开发的开源 AV1 视频编码器，支持高度并行化处理，适合服务器端和云视频编码场景。

## 项目信息

- **项目主页**: https://gitlab.com/AOMediaCodec/SVT-AV1
- **许可证**: BSD-3-Clause
- **源码**: https://github.com/AOMediaCodec/SVT-AV1 (GitHub) 或 GitLab 镜像

## 已编译版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 3.1.2 | built | 2026-05-29 |

## 功能特性

- 高性能 AV1 视频编码（支持多线程并行）
- ARM NEON SIMD 优化（neon_i8mm）
- 支持 8/10-bit 编码
- 多种预设（preset 0-13，速度与质量权衡）
- 支持 CRF 和 VBR 码率控制
- 无外部依赖（自包含编译）

## 使用方法

### 命令行编码

```bash
# 基本编码（CRF 模式）
SvtAv1EncApp --preset 10 --crf 35 -i input.y4m -b output.ivf

# 单 pass VBR 编码
SvtAv1EncApp --passes 1 --rc 1 --tbr 1000 -i input.y4m -b output.ivf

# 双 pass 编码
SvtAv1EncApp --stats stats.log --passes 2 --rc 1 --tbr 1000 -i input.y4m -b output.ivf
```

### 库集成（CMake）

```cmake
find_package(SvtAv1Enc REQUIRED)
target_link_libraries(your_target libSvtAv1Enc)
```

## OHOS 适配要点

### 必需补丁

修改 `Source/Lib/Codec/svt_threads.h`，禁用 `pthread_setaffinity_np`：

```c
// 原代码
#if defined(__linux__) && !defined(__ANDROID__)

// 修改为
#if defined(__linux__) && !defined(__ANDROID__) && !defined(__OHOS__)
```

**原因**: 鸿蒙平台不支持 `pthread_setaffinity_np`（线程亲和性设置）。

### 已知问题

| 问题 | 级别 | 说明 |
|------|------|------|
| pthread_setaffinity_np 不可用 | 🟡 中 | 已通过补丁解决 |
| ⚠️ 依赖路径问题 | 🔴 高 | SvtAv1EncApp 可能依赖构建目录路径，需验证 |

## 依赖

- 无外部依赖（自包含编译）
- 系统库：libc.so

## 功能验证

```bash
# 版本验证
SvtAv1EncApp --version
SVT-AV1 v3.1.2 (release)

# 编码测试
SvtAv1EncApp --preset 10 -i test.y4m -b output.ivf
# 编码速度：~348 fps (64x64, 3帧)
```

## 参考资料

- 官方文档: https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/master/Docs/README.md
- FFmpeg 集成: `-c:v libsvtav1`
- 预设说明: preset 0-13，数值越高速度越快
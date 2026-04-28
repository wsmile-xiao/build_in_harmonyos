# c-blosc — OpenHarmony 编译记录

## 基本信息
- 软件: c-blosc (Blocking, shuffling and loss-less compression library)
- 描述: 高性能、无损压缩库，支持多种压缩算法和 shuffle/bitshuffle 优化
- 构建系统: CMake
- 目标: ohos-aarch64

## 已编译版本
| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 1.21.6 | ✅ | 2026-04-27 | 完整编译，1632 测试通过 |

## 编译指导
```bash
# CMake 配置（需添加兼容性参数）
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DBUILD_BENCHMARKS=OFF ..

make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
make test  # 1632 测试全部通过
```

## 补丁清单
无补丁（源码无需修改）

## 已知限制
- 硬件加速 shuffle (AVX2/SSE2) 不可用，使用 generic 实现
- benchmark 工具未编译（平台不支持 clock_gettime/CLOCK_MONOTONIC）

## 功能验证
```bash
pkg-config --modversion blosc  # 输出: 1.21.6
```

## 压缩算法支持
- blosclz (内置)
- lz4 / lz4hc (内置 1.9.4)
- zlib (内置 1.3.1)
- zstd (内置 1.5.6)

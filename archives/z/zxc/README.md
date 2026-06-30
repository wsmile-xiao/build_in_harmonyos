# ZXC

> 高性能非对称无损压缩库

## 简介

ZXC (zxc) 是一个高性能无损压缩库，采用非对称压缩/解压设计。压缩端使用多线程流水线（读取→工作线程压缩→写入），解压端高度优化以实现最快速度。支持三种块类型：RAW（原始数据）、GHI/GLO（LZ77 变体）、NUM（整数序列专用编码），以及 8-bit/16-bit 偏移模式。

库提供三层 API：
- **Buffer API** (`zxc_buffer.h`): 单次压缩/解压，最简单的使用方式
- **Stream API** (`zxc_stream.h`): 多线程流式压缩/解压，支持 FILE* 输入输出
- **Sans-I/O API** (`zxc_sans_io.h`): 底层无 I/O 原语，供自定义集成

## OHOS 适配要点

1. **CMAKE_SYSTEM_PROCESSOR 检测失败**: OHOS 不被 CMake 识别为已知平台，导致 `CMAKE_SYSTEM_PROCESSOR` 设为 "unknown"，SIMD 变体（NEON）不构建但被引用，链接失败。需在 conanfile.py 的 `generate()` 中设置 `CMAKE_SYSTEM_NAME=Linux` 和 `CMAKE_SYSTEM_PROCESSOR=aarch64`。

2. **tmpfile() 不可用**: OHOS 的 /tmp 为只读，测试代码中的 `tmpfile()` 调用失败。需替换为 `mkstemp()` + `$TMPDIR` 方案。

3. **-march=native 不稳定**: 建议通过 `ZXC_NATIVE_ARCH=OFF` 禁用，确保可移植性。

4. **静态链接**: 终端工具（zxc CLI）必须静态链接（`BUILD_SHARED_LIBS=OFF`），仅依赖系统 libc.so。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | - | 无外部依赖，rapidhash 为内嵌 |

## 功能验证

```bash
# 版本信息
zxc --version

# 压缩/解压往返
echo "test data" | zxc -z | zxc -d

# 静态链接检查
readelf -d $(which zxc) | grep NEEDED
# 预期: 仅 libc.so
```

## 参考

- [源码仓库](https://github.com/hellobertrand/zxc)
- [许可证](https://github.com/hellobertrand/zxc/blob/v0.9.1/LICENSE) - BSD-3-Clause

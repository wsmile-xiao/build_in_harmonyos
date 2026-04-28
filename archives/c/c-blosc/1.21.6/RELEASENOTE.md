# c-blosc 1.21.6 发布说明

## 版本信息
- 版本: 1.21.6
- 发布日期: 2026-04-27
- 目标平台: OpenHarmony aarch64

## 编译配置
- 构建系统: CMake
- 编译器: Clang 15.0.4
- 构建类型: Release
- 内置压缩库: LZ4 1.9.4, zlib 1.3.1, ZSTD 1.5.6

## 特性
- ✅ 静态库 (libblosc.a)
- ✅ 动态库 (libblosc.so)
- ✅ 5 种压缩算法支持: blosclz, lz4, lz4hc, zlib, zstd
- ✅ 多线程压缩支持
- ✅ 兼容历史版本数据格式

## 已知限制
- ⚠️ 硬件加速 shuffle (AVX2/SSE2) 不可用，使用 generic 实现
- ⚠️ benchmark 工具未编译（平台不支持 clock_gettime）

## 测试结果
- 总测试数: 1632
- 通过: 1632 (100%)
- 失败: 0

## 安装方法
```bash
# 下载安装脚本
curl -fsSL <url>/install.sh | sh -s -- 1.21.6

# 或手动安装
tar xzf c-blosc-1.21.6-ohos-aarch64.tar.gz -C ~/usr/local
```

## 验证安装
```bash
pkg-config --modversion blosc  # 应输出 1.21.6
```

## 预编译包
- c-blosc-1.21.6-ohos-aarch64.tar.gz (1907KB)
- c-blosc-1.21.6-ohos-aarch64-debug.tar.gz (94KB)

## 文件清单
```
lib/libblosc.so      # 动态库
lib/libblosc.a       # 静态库
include/blosc.h      # 主头文件
include/blosc-export.h  # 导出定义
lib/pkgconfig/blosc.pc  # pkg-config 文件
```

# HdrHistogram C

## 简介
HdrHistogram_c 是 HdrHistogram 的 C 语言实现，提供高动态范围直方图，用于延迟测量和性能分析。支持从纳秒到小时级别的值范围，低内存占用，线程安全。

## OHOS 适配
- 需要补丁添加 time.h/unistd.h 头文件，解决 CLOCK_MONOTONIC/CLOCK_REALTIME 未定义问题
- HDR_LOG 功能需要 zlib，当前未安装时禁用（HDR_LOG_REQUIRED=OFF）
- 编译有少量警告（usleep/clock_gettime 隐式声明），不影响功能
- 需链接 pthread 和 rt 库

## 依赖
- 编译依赖：cmake, clang
- 运行依赖：libpthread, librt, libm

## 功能验证
```bash
# 测试程序
./test/hdr_atomic_test
./test/hdr_histogram_test
./test/hdr_histogram_atomic_test
```

## 参考
- 源码：https://github.com/HdrHistogram/HdrHistogram_c
- 许可证：CC0-1.0 / BSD-2-Clause

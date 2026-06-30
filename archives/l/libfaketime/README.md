# libfaketime

## 软件简介
libfaketime 是一个用于修改系统时间的库和工具，主要用于测试时间相关功能。它通过 LD_PRELOAD 机制拦截时间相关的系统调用，返回指定的时间，而不需要修改系统时钟。

## 主要功能
- 模拟特定时间点
- 模拟时间加速/减速
- 支持单线程和多线程应用

## 编译版本
- **版本**: 0.9.10
- **编译日期**: 2026-05-22
- **平台**: OpenHarmony aarch64

## 使用方法
```bash
# 安装后设置库路径
export LD_LIBRARY_PATH=$HOME/usr/local/lib/faketime:$LD_LIBRARY_PATH

# 模拟特定时间
faketime '2020-01-01 00:00:00' date

# 时间加速（每小时快 10 秒）
faketime '+10s x1h' date

# 查看版本
faketime --version
```

## 平台适配说明
本版本已针对 OpenHarmony/musl libc 进行适配：
- 移除了 GLIBC 符号版本机制
- 移除了不支持的编译器警告选项

## 文件列表
- `bin/faketime` - 命令行工具
- `lib/faketime/libfaketime.so.1` - 单线程版本库
- `lib/faketime/libfaketimeMT.so.1` - 多线程版本库

## 许可证
GPL-2.0

## 主页
https://github.com/wolfcw/libfaketime
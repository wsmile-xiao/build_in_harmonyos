# libde265

## 简介
libde265 是开源 H.265/HEVC 视频解码库，提供完整的 HEVC 解码支持。

## OHOS 适配
- CMake 构建
- ARM64 平台需禁用 ARM32 汇编代码优化
- 使用 libc++ 时需显式链接 C++ 标准库
- SSL 证书下载问题，可用 git clone 替代 wget
- HMDFS 不允许创建 fifo，make 自动降级单进程

## 依赖
- 无编译依赖

## 功能验证
```bash
# 设置库路径
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
dec265 --help
```

## 注意事项
- dec265 工具需设置 LD_LIBRARY_PATH 运行（RPATH 问题）

## 参考
- 主页: https://github.com/strukturag/libde265

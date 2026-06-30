# volk

Vulkan Overlay Loader

## 简介

volk 是一个 Vulkan 加载器的替代实现，提供更高效的 Vulkan API 访问。

## OHOS 适配

- CMake 构建系统，需要指定 `-stdlib=libc++`
- 需要手动编译 fmt 库（FetchContent 在平台受限）
- 需要 Python mako 模板库
- RPATH 使用相对路径，需设置 LD_LIBRARY_PATH

## 依赖

- fmt >= 10.2.1
- Python mako 模块

## 功能验证

```bash
volk-config-info --version  # 显示版本号 3.3.0
volk_profile                # Vulkan profiling 工具
```

## 参考

- GitHub: https://github.com/zeux/volk
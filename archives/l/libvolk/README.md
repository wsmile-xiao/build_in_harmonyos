# libvolk

libvolk 是 Vulkan 的 meta-loader，用于动态加载 Vulkan entrypoints。它提供了一个轻量级的解决方案，让应用程序能够在运行时加载 Vulkan 函数，而不需要链接完整的 Vulkan loader。

## OHOS 适配

### 已知问题
- **install规则缺失**: cmake 默认不生成 install 规则

### 解决方案
- 在 cmake 配置时添加 `-DVOLK_INSTALL=ON` 参数

## 依赖

- 无外部依赖（Vulkan header-only）

## 使用方式

libvolk 可以通过三种方式使用：
1. 链接静态库 `libvolk.a`
2. 直接编译 `volk.c` 源文件
3. Header-only 模式（直接包含头文件）

## 功能验证

```bash
# 检查静态库
ls ~/usr/local/lib/libvolk.a

# 检查头文件
ls ~/usr/local/include/volk.h volk.c
```

## 参考

- 官网: https://github.com/zcompute/libvolk
- 源码: https://github.com/zcompute/libvolk/archive/refs/tags/v1.4.350.tar.gz
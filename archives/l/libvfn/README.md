# libvfn

libvfn 是一个 NVMe 函数库，提供用户态 NVMe 驱动支持，用于直接访问 NVMe 设备，绕过内核块层，实现高性能存储操作。

## OHOS 适配

### 已知问题
- **void指针算术**: C++ 标准不允许 void* 算术运算，会导致编译错误
- **meson编译器识别**: meson 构建系统无法自动找到编译器，需显式设置环境变量
- **文档生成依赖**: 缺少 sphinx-rtd-theme 包导致文档生成失败

### 解决方案
- 将 void* 强制转换为 char* 进行算术运算
- export CC=/完整路径/clang CXX=/完整路径/clang++ AR=/完整路径/llvm-ar
- 禁用文档生成: `-Ddocs=disabled`

## 依赖

- 无外部运行时依赖

## 功能验证

```bash
# 检查库文件
ls ~/usr/local/lib/libvfn*.so*

# 验证pkg-config
pkg-config --modversion libvfn
```

## 参考

- 官网: https://github.com/linux-nvme/libvfn
- 源码: https://github.com/linux-nvme/libvfn/archive/refs/tags/v5.1.0.tar.gz
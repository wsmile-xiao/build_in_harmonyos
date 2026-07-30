# FFTW

## 简介
FFTW (Fastest Fourier Transform in the West) 是一个高性能的离散傅里叶变换 (DFT) 库，支持一维和多维变换，自动适应硬件以达到最佳性能。

## OHOS 适配
- **构建系统**：当前配方直接使用上游 CMake，不修改 `config.guess`/`config.sub`
- **CMake 兼容**：设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
- **产物**：默认 `shared=False` 安装 `libfftw3.a`；`shared=True` 安装共享库，两种模式均包含头文件、pkg-config 与 CMake 配置文件

## 依赖
- 编译工具: clang, cmake
- 无额外库依赖

## 功能验证
```bash
# 检查库文件
ls -la $HOME/usr/local/lib/libfftw3*
pkg-config --modversion fftw3
```

## 参考
- 官网: https://www.fftw.org/
- 源码: https://www.fftw.org/fftw-3.3.10.tar.gz

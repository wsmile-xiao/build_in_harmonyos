# FFTW

## 简介
FFTW (Fastest Fourier Transform in the West) 是一个高性能的离散傅里叶变换 (DFT) 库，支持一维和多维变换，自动适应硬件以达到最佳性能。

## OHOS 适配
- **Autotools 构建失败**：config.guess/config.sub 无法识别 OHOS，即使更新后仍有问题
- **推荐 CMake 构建**：设置 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 即可编译成功
- 预编译包包含：libfftw3.so、头文件、pkg-config 文件、cmake 配置文件

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
- 官网: http://www.fftw.org/
- 源码: http://www.fftw.org/fftw-3.3.10.tar.gz

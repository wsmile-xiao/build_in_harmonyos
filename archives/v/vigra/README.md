# vigra

## 简介
VIGRA (Vision with Generic Algorithms) 是通用的 C++ 图像分析库，提供多维数组、图像处理、滤波、分割等算法，核心为头文件库，`vigraimpex` 负责图像文件导入导出。

## OHOS 适配
- **构建系统**: CMake (`WITH_VIGRANUMPY=OFF`, `BUILD_DOCS=OFF`, `BUILD_TESTS=ON`)
- **依赖**: zlib/libpng/libjpeg-turbo/libtiff/fftw（必需）；hdf5/openexr/boost/lemon 可选且默认关闭
- **产物**: `libvigraimpex` + 头文件 `include/vigra/*`
- **测试**: 上游 ctest 53 项（最小依赖下 `ctest -N` 口径，全选项为 58）+ test_package 消费者测试

## 依赖
- zlib 1.3.1.1
- libpng 1.6.58
- libjpeg-turbo 3.2.0
- libtiff 4.7.2
- fftw 3.3.10

## 功能验证
```bash
pkg-config --modversion vigra  # 若安装 pkg-config 文件
```

## 参考
- 上游: https://github.com/ukoethe/vigra
- 文档: https://ukoethe.github.io/vigra/

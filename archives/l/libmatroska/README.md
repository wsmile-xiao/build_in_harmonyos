# libmatroska

Matroska 媒体容器格式库，用于读写 MKV/WebM 文件。

## 功能概述

- 提供 Matroska 容器格式的读写接口
- 支持 MKV (Matroska Video) 和 WebM 格式
- 处理 EBML (Extensible Binary Meta Language) 数据结构

## OHOS 适配要点

1. **CMake 配置**：需设置 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 以兼容旧版本 CMakeLists
2. **纯静态库**：本项目只编译静态库 (libmatroska.a)，无动态库
3. **依赖处理**：需要 libebml >= 1.4.3 作为前置依赖

## 依赖关系

- libebml >= 1.4.3 (必需)
- cmake >= 3.1.2

## 编译步骤

```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

## 参考资料

- 官网：https://matroska.org
- 源码：https://github.com/Matroska-Org/libmatroska
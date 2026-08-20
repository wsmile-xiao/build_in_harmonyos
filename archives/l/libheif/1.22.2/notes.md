# libheif 1.22.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：https://github.com/strukturag/libheif/archive/refs/tags/v1.22.2.tar.gz
2. 解压到工作目录
3. 创建 build 目录并执行 cmake 配置
4. make 编译
5. make install DESTDIR staging 安装
6. 打包生成预编译包
7. make install 本地安装
8. pkg-config 验证

### cmake 配置参数

```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=ON \
  -DWITH_EXAMPLES=OFF \
  -DWITH_GDK_PIXBUF=OFF \
  -DBUILD_TESTING=OFF \
  -DWITH_LIBDE265=OFF \
  -DWITH_X265=OFF \
  -DWITH_AOM_DECODER=OFF \
  -DWITH_AOM_ENCODER=OFF \
  -DWITH_X264=OFF \
  -DWITH_DAV1D=OFF \
  -DENABLE_PLUGIN_LOADING=OFF \
  -DWITH_LIBSHARPYUV=OFF
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | manifest.yaml 构建 system 错误记录为 autotools | 历史记录错误 | 修正为 cmake，添加 configure_options |
| 2 | clean_verify.py 不支持 cmake | 脚本限制，只支持 autotools | 手动完成 G0 干净构建验证 |

## 源码修改

无源码修改，所有编解码器通过 cmake 参数禁用。

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- pkg-config: 0.29.2
- TIFF: 4.7.1
- JPEG: 62
- ZLIB: 1.3.1
- PNG: 1.6.39

## 验证结果

```bash
$ pkg-config --modversion libheif
1.22.2

$ pkg-config --libs libheif
-L/storage/Users/currentUser/usr/local/lib -lheif

$ pkg-config --cflags libheif
-I/storage/Users/currentUser/usr/local/include
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libheif-1.22.2-ohos-aarch64.tar.gz | 3379KB | 预编译包 |
| libheif.so | 2279936 字节 | 共享库 |

## 注意事项

1. libheif 默认需要编解码器依赖（libde265/x265/aom 等），本版本禁用所有编解码器，仅提供 HEIF 文件格式基础支持
2. 若需要完整功能，需先编译安装相应的编解码器依赖
3. clean_verify.py 目前不支持 cmake 构建系统，需要手动完成 G0 干净构建验证
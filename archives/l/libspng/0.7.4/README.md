# libspng 0.7.4 - OpenHarmony 预编译包

## 软件描述
libspng 是一个用于读写 PNG 格式文件的 C 语言库。它旨在用更简单、更现代的 API 替代 libpng，同时保持高性能。

- 官网：https://libspng.org/
- 许可证：BSD-2-Clause

## 构建信息
- 版本：0.7.4
- 构建系统：CMake（因 meson 不可用而使用替代方案）
- 平台：OpenHarmony aarch64
- 编译器：Clang 15.0.4
- 构建日期：2026-05-18

## 依赖关系
- zlib 1.3.2（必需）

## 安装方法

### 使用预编译包
```bash
tar xf libspng-0.7.4-ohos-aarch64.tar.gz
# 文件位于 lib/ 和 include/ 目录中
```

### 从源码构建
```bash
cmake -DCMAKE_INSTALL_PREFIX=/安装路径 \
      -DSPNG_SHARED=ON \
      -DSPNG_STATIC=ON \
      -DZLIB_ROOT=/zlib路径
make
make install
```

## 包含文件
- `lib/libspng.so` - 动态库（76KB）
- `lib/libspng_static.a` - 静态库（70KB）
- `include/spng.h` - 头文件
- `lib/cmake/spng/` - CMake 配置文件
- `lib/pkgconfig/libspng.pc` - pkg-config 文件

## 使用示例
```c
#include <spng.h>

// 解码 PNG 文件
spng_ctx *ctx = spng_ctx_new(0);
spng_set_png_file(ctx, fp);
spng_decode_image(ctx, out, out_size, SPNG_FMT_RGBA8, 0);
spng_ctx_free(ctx);
```

## 已知问题
- 完整测试套件需要 meson 和 libpng，本次使用手动测试验证核心功能
- 因 GitHub 网络限制，源码从 Gitee 镜像获取

## 测试结果
详见 `reports/test-report.md`（11项测试全部通过）

## 参考资料
- 源码：https://github.com/randy408/libspng
- 镜像：https://gitee.com/mirrors/libspng
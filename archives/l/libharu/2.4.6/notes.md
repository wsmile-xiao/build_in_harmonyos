# libharu 2.4.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 状态: published

## 编译步骤
```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release ..
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案
- CMake 警告缺少 zlib/libpng（非阻塞）

## 验证结果
```bash
ls ~/usr/local/lib/libhpdf.so
# 输出: libhpdf.so
```

## 交付物
| 文件 | 说明 |
|------|------|
| libharu-2.4.6-ohos-aarch64.tar.gz | 预编译包 (520 KB) |

## 注意事项
- PNG/ZLIB 支持可选，不影响 PDF 生成核心功能

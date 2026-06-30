# libmediainfo 26.05 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装依赖：libzen 0.4.41（预编译包）、zlib 1.3.1（已安装）
2. 下载源码：https://mediaarea.net/download/source/libmediainfo/26.05/libmediainfo_26.05.tar.xz
3. 解压 tarball（嵌套源码结构，需要完整解压 MediaInfoLib 目录）
4. 配置 cmake：
   ```bash
   cd MediaInfoLib/Project/CMake
   mkdir build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
            -DCMAKE_PREFIX_PATH=$HOME/usr/local \
            -DZLIB_ROOT=$HOME/usr/local
   ```
5. 编译：make -j4
6. 安装到 staging：make install DESTDIR=$TEST_PREFIX
7. 安装到本地：make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 找不到 zlib | PKG_CONFIG_PATH 未设置 | 设置 PKG_CONFIG_PATH 并使用 cmake 参数指定路径 |
| 2 | 源码目录缺少 Source 目录 | init-build 提取嵌套源码不完整 | 手动解压完整 tarball 到 MediaInfoLib 目录 |
| 3 | 找不到 md5.c 等源文件 | CMakeLists.txt 期望相对路径 | 从 Project/CMake 目录运行 cmake |

## 源码修改

无补丁，源码无需修改。

## 依赖版本

- zlib 1.3.1
- libzen 0.4.41

## 验证结果

```bash
# 验证静态库安装
ls -lh ~/usr/local/lib/libmediainfo.a
# 输出: 94MB 静态库文件

# 验证头文件安装
ls ~/usr/local/include/MediaInfo/MediaInfo.h
# 输出: 头文件已安装

# pkg-config 验证
pkg-config --modversion libmediainfo
# 输出: 26.05
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmediainfo.a | 94MB | 静态库 |
| MediaInfo.h | 16KB | 头文件 |

## 注意事项

1. libmediainfo 是静态库，无可执行文件
2. 编译需要从 Project/CMake 目录运行 cmake
3. 需要设置 PKG_CONFIG_PATH 或使用 cmake 参数指定依赖路径
4. 源码嵌套结构：tarball 包含 MediaInfoLib/Project/CMake 目录
---

**编译结束**: 2026-05-26 18:14
**最终状态**: built

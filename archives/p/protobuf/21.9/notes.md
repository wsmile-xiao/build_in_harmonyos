# protobuf 21.9 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

由于 Autotools 构建在 HMDFS 文件系统上遇到 config.status 创建临时文件的权限问题，
切换到 CMake 构建：

```bash
# 配置 CMake（添加 C++ 标准库链接选项）
cmake .. \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -Dprotobuf_BUILD_TESTS=OFF \
  -Dprotobuf_WITH_ZLIB=OFF \
  -DCMAKE_CXX_FLAGS="-stdlib=libc++" \
  -DCMAKE_EXE_LINKER_FLAGS="-L/data/service/hnp/... -lc++_static -lc++abi -lunwind"

# 编译
make -j$(nproc)

# 安装到 staging
make install DESTDIR=/storage/Users/currentUser/test-install-protobuf-21.9

# 安装到本地
make install

# 验证
/storage/Users/currentUser/usr/local/bin/protoc --version
# 输出: libprotoc 3.21.9
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: source directory already configured | 源码目录之前有配置缓存 | 清理旧配置文件后重新配置 |
| 2 | config.status: Permission denied | HMDFS 文件系统权限限制 | 切换到 CMake 构建系统 |
| 3 | ld.lld: undefined symbol: std::__n1::... | 缺少 C++ 标准库链接 | 添加 -lc++_static -lc++abi -lunwind |
| 4 | ZLIB 库未找到 | 系统缺少 ZLIB 预编译包 | 禁用 ZLIB 支持 (-Dprotobuf_WITH_ZLIB=OFF) |

## 源码修改

无补丁，使用原始源码编译。

## 依赖版本

- CMake: 4.1.2
- Clang: 15.0.4
- libc++_static: 鸿蒙 SDK 内置

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/protoc --version
libprotoc 3.21.9

$ ls -la /storage/Users/currentUser/usr/local/lib/
libprotobuf-lite.a  (3.6MB)
libprotobuf.a       (25.8MB)
libprotoc.a         (30.4MB)

$ ls -la /storage/Users/currentUser/usr/local/bin/
protoc              (软链接)
protoc-3.21.9.0     (15.3MB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libprotobuf-lite.a | 3.6MB | 轻量级库 |
| libprotobuf.a | 25.8MB | 完整库 |
| libprotoc.a | 30.4MB | 编译器库 |
| protoc-3.21.9.0 | 15.3MB | protobuf 编译器 |

## 注意事项

1. HMDFS 文件系统上的 Autotools 构建可能遇到权限问题，建议使用 CMake
2. 链接时必须指定 libc++ 静态库路径和链接选项
3. ZLIB 支持可通过 cmake 选项禁用，避免依赖问题
---

**编译结束**: 2026-05-28 17:51
**最终状态**: built

# libmatroska 1.7.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://codeload.github.com/Matroska-Org/libmatroska/tar.gz/refs/tags/release-1.7.1
2. 安装依赖 libebml 1.4.5 预编译包
3. CMake 配置: `cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5`
4. 构建: `make -j2`
5. 安装到 staging: `make install DESTDIR=/storage/Users/currentUser/test-install-libmatroska-1.7.1`
6. 安装到本地: `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本兼容性警告 | CMakeLists.txt 要求 3.1.2，当前 CMake 4.1.2 不兼容旧版本 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | 缺少依赖 libebml | libmatroska 需要 EBML 1.4.3+ | 安装预编译包 libebml 1.4.5 |

## 源码修改

无补丁，源码无需修改即可编译。

## 依赖版本

- libebml: 1.4.5（预编译包）
- cmake: 4.1.2
- clang: 15.0.4

## 验证结果

```bash
$ pkg-config --modversion libmatroska
1.7.1
$ pkg-config --libs libmatroska
-L/storage/Users/currentUser/usr/local/lib -lmatroska
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmatroska.a | 1.9MB | 静态库 |

## 注意事项

- 这是纯静态库项目，无动态库
- 需要 libebml 1.4.3 或更高版本
- CMake 配置时需要添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 以避免版本兼容性问题
---

**编译结束**: 2026-06-02 10:10
**最终状态**: built

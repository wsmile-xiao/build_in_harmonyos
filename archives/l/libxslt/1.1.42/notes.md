# libxslt 1.1.42 适配笔记

## 编译环境
- 构建系统: cmake（原源码支持 autotools 和 cmake，但 autotools 的 configure 脚本有 PKG_CHECK_MODULES 宏展开问题）
- 编译日期: 2026-05-21
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 初始化：使用本地 tar.gz 文件（file:///storage/Users/currentUser/tmp/libxslt-1.1.42.tar.gz）
2. 创建 LibXml2Config.cmake：由于 libxml2 通过 autotools 编译，没有 CMake 配置文件，手动创建
3. CMake 配置：
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
            -DCMAKE_PREFIX_PATH=/storage/Users/currentUser/usr/local \
            -DLIBXSLT_WITH_PYTHON=OFF \
            -DLIBXSLT_WITH_CRYPTO=OFF \
            -DLIBXSLT_WITH_TESTS=OFF
   ```
4. 编译：`make -j2`
5. 安装：
   - Staging: `make install DESTDIR=/storage/Users/currentUser/test-install-libxslt-1.1.42`
   - 系统: `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools configure 脚本 PKG_CHECK_MODULES 宏未展开 | 缺少 pkg.m4 文件，导致宏无法正确展开 | 改用 CMake 构建系统 |
| 2 | CMake 找不到 LibXml2Config.cmake | libxml2 通过 autotools 编译，未生成 CMake 配置 | 手动创建 LibXml2Config.cmake 文件 |
| 3 | runtest 测试程序链接失败 (xmlFormatError undefined) | xmlFormatError 是 libxml2 内部函数，不对外导出 | 禁用测试 (-DLIBXSLT_WITH_TESTS=OFF) |
| 4 | autogen.sh 删除 conf* 时误删 configure.ac | 不小心执行了 rm -rf conf* | 从 .orig 目录恢复 configure.ac |

## 源码修改

无补丁，但创建了额外的配置文件：
- `/storage/Users/currentUser/usr/local/lib/cmake/LibXml2/LibXml2Config.cmake` - 手动创建的 libxml2 CMake 配置文件

## 依赖版本

- libxml2: 2.11.9（已安装）
- clang: 15.0.4
- cmake: 4.1.2

## 验证结果

```bash
# 检查安装文件
ls -la /storage/Users/currentUser/usr/local/include/libxslt/
ls -la /storage/Users/currentUser/usr/local/lib/pkgconfig/libxslt.pc

# pkg-config 验证
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --modversion libxslt  # 输出: 1.1.42
pkg-config --cflags libxslt      # 输出: -I/storage/Users/currentUser/usr/local/include -I/storage/Users/currentUser/usr/local/include/libxml2
pkg-config --libs libxslt        # 输出: -L/storage/Users/currentUser/usr/local/lib -lxslt -lxml2

# 检查共享库
ls -la /storage/Users/currentUser/usr/local/lib/libxslt.so    # 403904 bytes
ls -la /storage/Users/currentUser/usr/local/lib/libexslt.so   # 133568 bytes
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libxslt.so | 403904 | 主库共享库 |
| libexslt.so | 133568 | 扩展库共享库 |
| libxslt.pc | 271 | pkg-config 配置文件 |
| libexslt.pc | 284 | exslt pkg-config 文件 |
| libxslt/*.h | 21个文件 | 头文件目录 |

## 注意事项

1. **构建系统选择**：libxslt 源码同时支持 autotools 和 cmake，本编译使用 cmake 因 autotools 的 PKG_CHECK_MODULES 宏展开问题
2. **Python 绑定**：已禁用 Python 绑定（-DLIBXSLT_WITH_PYTHON=OFF）
3. **Crypto 支持**：已禁用 crypto 支持（-DLIBXSLT_WITH_CRYPTO=OFF）
4. **测试程序**：已禁用测试程序编译（-DLIBXSLT_WITH_TESTS=OFF），因 runtest 需要使用 libxml2 内部函数
5. **依赖关系**：libxslt 依赖 libxml2，需确保 libxml2 已正确安装并设置 PKG_CONFIG_PATH
# leptonica 1.87.0 适配笔记

## 编译环境
- 构建系统: cmake（因autogen.sh失败，libtoolize脚本shebang路径问题）
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. **源码下载**: 从GitHub下载 leptonica 1.87.0
   - URL: https://github.com/DanBloomberg/leptonica/archive/refs/tags/1.87.0.tar.gz
   
2. **构建系统选择**: 
   - autogen.sh失败（libtoolize shebang路径错误，期望bash在/storage/Users/currentUser/usr/local/bin/bash，实际在/data/service/hnp/bin/bash）
   - 改用cmake构建系统
   
3. **cmake配置**: 
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release
   ```
   - 找到的依赖：ZLIB 1.3.1, PNG 1.6.39, JPEG 62, TIFF 4.7.1, OpenJPEG 2.5.2
   - 未找到：GIF, WebP（可选依赖）
   - BUILD_PROG: OFF（未编译测试程序）
   
4. **编译**: 
   ```bash
   make -j$(nproc)
   ```
   - 编译成功，生成静态库 libleptonica.a (4.8M)
   
5. **Staging安装**: 
   ```bash
   make install DESTDIR=/storage/Users/currentUser/tmp/test-install-leptonica-1.87.0
   ```
   
6. **本地安装**: 
   ```bash
   make install
   ```
   - 安装路径：/storage/Users/currentUser/usr/local
   - 库文件：libleptonica.a
   - 头文件：leptonica/*.h
   - pkg-config：lept.pc

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autogen.sh失败 | libtoolize脚本shebang路径错误（期望/storage/Users/currentUser/usr/local/bin/bash，实际bash在/data/service/hnp/bin/bash） | 改用cmake构建系统（源码包含CMakeLists.txt） |
| 2 | cmake警告"System is unknown" | 鸿蒙系统不在cmake已知平台列表中 | 忽略警告，cmake仍能正常工作 |

## 源码修改

无补丁，使用cmake构建系统替代autotools。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| zlib | 1.3.1 | 预编译 |
| libpng | 1.6.39 | 预编译 |
| libjpeg | 62 | 预编译 |
| libtiff | 4.7.1 | 预编译 |
| openjpeg | 2.5.2 | 预编译 |

## 验证结果

```bash
# pkg-config验证
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --modversion lept
# 输出: 1.87.0

# 库文件验证
ls -lh /storage/Users/currentUser/usr/local/lib/libleptonica.a
# 输出: -rw-rw---- 1 20001006 file_manager 4.8M 2026-05-27 12:42 libleptonica.a

# 文件类型
file /storage/Users/currentUser/usr/local/lib/libleptonica.a
# 输出: current ar archive
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libleptonica.a | 4.8M | 静态库（主库） |
| lept.pc | - | pkg-config文件 |
| LeptonicaConfig.cmake | - | cmake配置文件 |
| leptonica/*.h | - | 头文件（约40个） |

## 注意事项

1. **构建系统**: 本次使用cmake构建，autotools失败
2. **纯库软件**: leptonica是纯库软件，无可执行二进制文件，无需运行--version验证
3. **可选依赖**: GIF和WebP未安装，不影响核心功能
4. **静态库**: 生成静态库而非动态库（可能与cmake配置或平台有关）
---

**编译结束**: 2026-05-27 12:56
**最终状态**: built

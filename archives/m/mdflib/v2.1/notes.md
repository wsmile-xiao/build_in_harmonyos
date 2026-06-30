# mdflib v2.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-23
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. 下载源码: `curl -kL -o mdflib-v2.1.0.tar.gz https://codeload.github.com/ihedvall/mdflib/tar.gz/refs/tags/v2.1.0`
2. init-build: `ohc-run.py init-build mdflib v2.1 --url=... --no-download`
3. CMake 配置:
   ```bash
   cmake .. \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DMDF_BUILD_SHARED_LIB=ON \
     -DMDF_BUILD_SHARED_LIB_NET=OFF \
     -DMDF_BUILD_SHARED_LIB_EXAMPLE=OFF \
     -DMDF_BUILD_DOC=OFF \
     -DMDF_BUILD_TOOL=OFF \
     -DMDF_BUILD_TEST=OFF \
     -DCMAKE_CXX_STANDARD=17 \
     -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
     -DEXPAT_INCLUDE_DIR=$DEFAULT_PREFIX/include \
     -DEXPAT_LIBRARY=$DEFAULT_PREFIX/lib/libexpat.so
   ```
4. 编译: `make -j2`
5. 安装: `make install DESTDIR=$TEST_PREFIX` (staging) + `make install` (本地)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | strerror_r 返回类型不匹配 | musl libc 的 strerror_r 返回 int（POSIX），代码假设返回 char*（GNU） | 改为 POSIX 兼容写法：直接调用 strerror_r 不使用返回值 |
| 2 | CMake 找不到 EXPAT 库 | libexpat 仅有 .so 无 .a，FindEXPAT 未自动发现 | 手动指定 -DEXPAT_LIBRARY 和 -DEXPAT_INCLUDE_DIR |

## 源码修改

### mdflib/src/platform.cpp
- **行 43-46**: `strerror_r` 返回值类型不匹配
- **修复**: 将 `auto* dummy = strerror_r(...)` 改为直接调用 `strerror_r(...)` 忽略返回值
- **原因**: musl libc 实现的是 POSIX 版 strerror_r（返回 int），非 GNU 版（返回 char*）

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1 | 压缩支持（MDF 数据块解压） |
| expat | 2.7.1 | XML 解析（元数据读写） |

## 验证结果

```bash
# 静态库
file libmdf.a → ar archive
llvm-nm libmdf.a | grep -c " T " → 1378 个导出符号

# 动态库
file libmdflibrary.so → ELF shared object, 64-bit LSB arm64
llvm-readelf -d libmdflibrary.so | NEEDED → libexpat.so, libc++_shared.so, libc.so

# 头文件
find include -name "*.h" | wc -l → 42 个头文件
```

## 交付物

| 文件 | 说明 |
|------|------|
| libmdf.a | 静态库（核心 MDF 读写功能） |
| libmdflibrary.so | 动态库（封装层，依赖 libmdf.a） |
| include/mdf/*.h | 核心头文件（25 个） |
| include/mdflibrary/*.h | 封装层头文件（17 个） |
| lib/cmake/mdflib/ | CMake 配置文件（4 个） |

## 功能测试

mdflib 自带的 Google Test 测试套件 (`mdflib_test/`) 依赖 Boost filesystem/system/locale/program_options 编译库，当前环境仅有 Boost 头文件，无法编译。

改为编写独立 C++ 测试程序 (`reports/test_mdflib.cpp`)，直接链接 libmdf.a 验证核心 API 功能：

```
编译: clang++ -std=c++17 -fPIC -O2 -I<source>/include -I<prefix>/include \
  test_mdflib.cpp -L<prefix>/lib -lmdf -lexpat -lz -o test_mdflib

结果: 8 通过, 0 失败, 共 8 项
  [1] 创建 MDF3 文件对象 ... PASS
  [2] 创建 MDF4 文件对象 ... PASS
  [3] MDF3 文件写入 ... PASS (978 bytes)
  [4] MDF4 文件写入 ... PASS (1368 bytes)
  [5] MDF3 文件读取验证 ... PASS (v3.30)
  [6] MDF4 文件读取验证 ... PASS (v4.20)
  [7] 创建 BusLogger 写入器 ... PASS
  [8] FinalizeMeasurement 空测量 ... PASS (416 bytes)
```

## 注意事项

- mdflib 是纯库项目，无可执行文件，make check 无测试目标
- 动态库 libmdflibrary.so 依赖 libexpat.so，部署时需确保 expat 可用
- .NET 支持、MDF Viewer 工具、Google Test 均已关闭（不适用本平台）
- CMake 检测到平台为 unknown（HarmonyOS），不影响编译
- canmessage.h 未安装到 ~/usr/local/include/mdf/，编译测试程序需额外指定源码 include 路径
---

**编译结束**: 2026-06-23 16:15
**最终状态**: published

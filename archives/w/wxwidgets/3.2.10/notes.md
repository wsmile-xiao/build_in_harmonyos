# wxwidgets 3.2.10 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **初始化编译环境**：使用 `ohc-run.py init-build wxwidgets 3.2.10` 下载源码并创建归档骨架

2. **CMake 配置**：
   ```bash
   export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:$LD_LIBRARY_PATH
   cmake "$BUILD_SRC_DIR" \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_SYSTEM_NAME=OHOS \
     -DwxBUILD_SHARED=OFF \
     -DwxBUILD_SAMPLES=OFF \
     -DwxBUILD_TESTS=OFF \
     -DwxUSE_GUI=OFF \
     -DCMAKE_C_COMPILER=clang \
     -DCMAKE_CXX_COMPILER=clang++
   ```

3. **编译**：`cmake --build . -j2`

4. **安装到 staging**：`DESTDIR=$TEST_PREFIX cmake --install . --prefix $DEFAULT_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools 构建 config.status 失败 | HMDFS 文件系统对临时文件创建有权限限制 | 使用 CMake 构建方式替代 autotools |
| 2 | CMake 找不到 GTK3 | wxWidgets 默认需要 GTK/X11，鸿蒙不支持 | 设置 `wxUSE_GUI=OFF` 构建 base toolkit（无 GUI） |
| 3 | 链接器 lld 找不到 libxml2.so.16 | OHOS SDK 的 lib 目录不在 LD_LIBRARY_PATH 中 | 设置 `LD_LIBRARY_PATH` 包含 OHOS SDK 的 lib 目录 |

## 源码修改

无补丁，使用 CMake 构建方式成功编译。

## 依赖版本

| 软件 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1 | 压缩支持 |
| expat | 2.8.2 | XML 解析 |
| curl | 8.15.0 | 网络请求（用于 wxWebRequest） |
| libiconv | 系统内置 | 字符编码转换 |

## 验证结果

```bash
# Staging 验证
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/bin/
# 输出：wx-config -> /storage/Users/currentUser/usr/local/lib/wx/config/base-unicode-static-3.2

ls -la $TEST_PREFIX/$DEFAULT_PREFIX/lib/
# 输出：
# libwx_baseu-3.2-OHOS.a (基础库，6.8MB)
# libwx_baseu_net-3.2-OHOS.a (网络库，1.0MB)
# libwxregexu-3.2.a (正则表达式库，372KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libwx_baseu-3.2-OHOS.a | 6.8MB | wxWidgets 基础库（静态） |
| libwx_baseu_net-3.2-OHOS.a | 1.0MB | wxWidgets 网络库（静态） |
| libwxregexu-3.2.a | 372KB | wxWidgets 正则表达式库（静态） |
| wx-config | - | 配置工具（软链接） |
| wxWidgetsConfig.cmake | - | CMake 配置文件 |

## 注意事项

1. **无 GUI 限制**：wxWidgets 在鸿蒙上不支持 GUI 功能（GTK/X11/Wayland 不可用），只能构建 base toolkit
2. **静态库推荐**：使用 `wxBUILD_SHARED=OFF` 避免动态库的 ELF 签名问题
3. **LD_LIBRARY_PATH**：CMake 构建前必须设置正确的 LD_LIBRARY_PATH，包含 OHOS SDK 的 lib 目录
4. **库名标识**：生成的静态库名包含 `-OHOS` 标识，如 `libwx_baseu-3.2-OHOS.a`

---

**编译结束**: 2026-05-29 19:12
**最终状态**: built

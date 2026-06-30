# E100 — 共享库路径硬编码为相对路径

## 错误特征

编译成功，但运行时二进制文件无法加载共享库：

```
Error loading shared library ../libheif/libheif.so: (needed by /path/to/binary)
Error relocating /path/to/binary: symbol_name: symbol not found
```

使用 `readelf -d <binary>` 检查发现 NEEDED 字段包含相对路径：

```
0x0000000000000001 (NEEDED)             Shared library: [../libheif/libheif.so]
```

即使 RUNPATH 包含 `$ORIGIN/../lib/libheif`，也无法匹配相对路径的 NEEDED。

## 触发条件
- 构建系统: cmake
- 阶段: linking/runtime
- 库文件安装在子目录（如 `lib/libheif/` 而非 `lib/`）

## 根因分析

CMake 编译时，库文件位于构建目录的子目录中（如 `build/libheif/libheif.so`），链接器将这个相对路径硬编码到二进制文件的 NEEDED 字段。

安装后的目录结构：
```
bin/heif-info
lib/libheif.so         # 顶层库
lib/libheif/libheif.so # 子目录库
```

但二进制文件期望的路径是相对于 `bin/` 的 `../libheif/libheif.so`，与实际安装路径不一致。

## 解决方案

### 推荐方案（重新编译）

修改 CMakeLists.txt，确保库安装到顶层 lib 目录：

```cmake
# 修改前（错误）
install(TARGETS heif LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}/libheif)

# 修改后（正确）
install(TARGETS heif LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
```

或者强制设置 `CMAKE_INSTALL_LIBDIR` 为顶层目录。

### 回退方案（patchelf）

如果无法重新编译，尝试使用 patchelf 替换 NEEDED 字段：

```bash
patchelf --replace-needed "../libheif/libheif.so" "libheif.so" <binary>
```

注意：在 HMDFS 文件系统上，patchelf 操作可能被拒绝。

### 禁止做法
- ❌ 在 CMake install 命令中使用相对路径作为 LIBRARY DESTINATION
- ❌ 将库安装到子目录（如 `lib/subdir/`）然后期望二进制通过 RPATH 找到

## 验证

检查 NEEDED 字段是否正确：

```bash
readelf -d <binary> | grep NEEDED
# 期望输出：Shared library: [libheif.so] 或 [libheif.so.X]
# 错误输出：Shared library: [../libheif/libheif.so]
```

运行二进制验证库加载：

```bash
<binary> --version
# 成功：输出版本信息
# 失败：Error loading shared library ...
```

## 关联条目
- 相关: R1-参数最少化, R20-DESTDIR模式
- 发现于: libheif-1.18.2 编译

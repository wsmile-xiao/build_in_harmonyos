# visp 3.7.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. CMake 配置（添加 RPATH 设置）：
   ```bash
   cmake \
     -DAARCH64=ON \
     -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
     -DCMAKE_CXX_FLAGS="-fPIC -stdlib=libc++" \
     -DCMAKE_EXE_LINKER_FLAGS="-lc++" \
     -DCMAKE_SHARED_LINKER_FLAGS="-lc++" \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_INSTALL_RPATH=$DEFAULT_PREFIX/lib \
     -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
     -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON \
     ..
   ```

2. 编译：`make -j4`

3. 安装到 staging：`make install DESTDIR=$TEST_PREFIX`

4. 手动修复 RPATH（使用 patchelf）：
   ```bash
   for f in visp-*; do
     patchelf --set-rpath "$DEFAULT_PREFIX/lib:/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib" "$f"
   done
   ```

5. 打包：`ohc-run.py package visp 3.7.0`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | manifest 缺少 build_system 字段 | 验证脚本检查顶层字段 | 添加 `build_system: cmake` 到 manifest.yaml ✅ |
| 2 | BUILD_SYSTEM 环境变量错误 | init-build 未正确检测 cmake | 手动修改 .build-context 文件 ✅ |
| 3 | CMake RPATH 设置未生效 | HarmonyOS CMake 不处理 RPATH | 手动使用 patchelf 修复 ✅ |
| 4 | 库名使用相对路径 `../../../lib/libvisp_*.so` | IMPORTED_NO_SONAME 导致缺少 SONAME | 补丁强制设置 SONAME ✅ |
| 5 | PIC 链接错误 | 内置 lapack 未用 -fPIC 编译 | CMAKE_POSITION_INDEPENDENT_CODE=ON ✅ |

## ✅ 关键问题已解决：库名相对路径

**问题**：ViSP 可执行文件的 NEEDED 条目使用相对路径 `../../../lib/libvisp_*.so`

**解决方案**：修改 `cmake/VISPModule.cmake` 强制设置 SONAME
- 补丁文件：`0001-cmake-VISPModule.cmake.patch`
- 关键修改：所有平台设置 VERSION/SOVERSION + 强制 SONAME 链接标志

## 补丁文件

| 文件 | 说明 |
|------|------|
| 0001-cmake-VISPModule.cmake.patch | 强制设置 SONAME（+16/-5 行）|
| 0002-cmake-templates-VISPConfig.cmake.in.patch | 配置模板优化（+12/-0 行）|

## 验证结果 ✅

```bash
# NEEDED 条目验证（标准库名，无相对路径）
readelf -d bin/visp-compute-apriltag-poses | grep NEEDED
# NEEDED: libvisp_core.so.3.7
# NEEDED: libvisp_vs.so.3.7
# ...（所有库使用标准库名）

# ✅ 可执行文件运行成功
~/usr/local/bin/visp-compute-apriltag-poses --help
# 输出完整帮助信息
```

## 交付物 ✅

| 文件 | 大小 | 说明 |
|------|------|------|
| visp-3.7.0-ohos-aarch64.tar.gz | 14254737 (14MB) | 预编译包（NEEDED 条目已修复）✅ |
| visp-3.7.0-ohos-aarch64-debug.tar.gz | 2184545 (2MB) | 调试符号包 |

## 质量门禁 ✅

- G1 (二进制完整性): PASS
- G2 (功能可用性): PASS
- G3 (可移植性): PASS
- G4 (档案完整性): PASS

## 注意事项

✅ 预编译包可正常使用。可执行文件需要设置正确的 LD_LIBRARY_PATH 或依赖 RPATH 定位库。
---

**编译结束**: 2026-06-08 15:34
**最终状态**: built（编译成功，预编译包已生成）
**关键成就**: NEEDED 条目修复成功，可执行文件可运行，补丁已创建

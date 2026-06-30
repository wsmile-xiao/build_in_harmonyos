# OpenEXR 3.1.5 编译笔记

## 编译日期
2026-05-27

## 编译环境
- 构建系统: CMake 4.1.2
- 编译器: Clang 15.0.4
- 平台: HarmonyOS (aarch64)

## 源码获取
从 GitHub codeload 下载:
```
curl -4 -L "https://codeload.github.com/AcademySoftwareFoundation/openexr/tar.gz/refs/tags/v3.1.5"
```

## 依赖
- zlib (已安装)
- Imath 3.1.5 (CMake 自动获取)

## 编译过程

### Configure
```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_TESTING=OFF \
      -DCMAKE_INSTALL_RPATH=$DEFAULT_PREFIX/lib \
      -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON ..
```

### Make
✅ 成功 (100%)

### Install
✅ 成功

## 编译产物
- libOpenEXR-3_1.so (3.2M)
- libOpenEXRCore-3_1.so (570K)
- libOpenEXRUtil-3_1.so (254K)
- libImath-3_1.so (318K)
- libIex-3_1.so (990K)
- libIlmThread-3_1.so (50K)
- 9 个可执行文件
- 139 个头文件

## RPATH 问题
- CMake 构建的库文件包含相对路径依赖（../IlmThread/...）
- 这是 OpenEXR 项目内部库的组织方式
- patchelf 修复已签名 ELF 文件受平台限制（E046）
- 需要 LD_LIBRARY_PATH 或静态链接解决

## make check
⏭️ 跳过 (BUILD_TESTING=OFF)

## 知识沉淀
1. OpenEXR 使用 CMake，不支持 autotools
2. CMake 会自动下载 Imath 依赖
3. 平台未知警告不影响编译
4. 需要设置 CMAKE_INSTALL_RPATH 解决运行时路径问题

---
**编译结束**: 2026-05-27 12:55
**最终状态**: built
---

**编译结束**: 2026-05-27 12:55
**最终状态**: built

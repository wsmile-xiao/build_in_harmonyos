# libzip 1.11.4 — 适配笔记

## 平台
- 目标: OpenHarmony (aarch64)
- 构建系统: cmake

## 编译步骤
1. 安装依赖: zlib 1.3.1 (cmd-pkgs)
2. cmake 配置: -DCMAKE_INSTALL_PREFIX=... -DBUILD_SHARED_LIBS=ON -DBUILD_DOC=OFF
3. make -j2
4. make install

## 产物
- libzip.so (199KB)
- zip.h 头文件
- zipcmp, zipmerge, ziptool 工具
- CMake 配置文件 (libzip-config.cmake)

## 注意事项
- 构建系统是 cmake，不是 autotools
- nihtest 未安装，回归测试不可用

---

# Conan 配方补充（2026-07-30）

> 以上为 2026-04 手工编译路径的原始记录，**原样保留**。以下为本次新增的 Conan 配方说明。

# libzip 1.11.4 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 liblibzip.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
built（CI conan create + test 通过）

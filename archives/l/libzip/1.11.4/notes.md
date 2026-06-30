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

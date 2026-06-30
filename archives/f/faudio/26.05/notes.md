# faudio 26.05 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. init-build: 下载源码（通过 gh-proxy.com 镜像下载，GitHub 直连超时）
2. CMake configure: 使用 HNP cmake（~/usr/local/bin/cmake 因权限被拒），设置 CMAKE_SYSTEM_NAME=Linux 和 CMAKE_C_COMPILER_WORKS=TRUE
3. make -j1 编译成功（24 个 .o 文件 → libFAudio.so.0.26.05）
4. make install DESTDIR=$TEST_PREFIX staging 安装成功
5. Staging 验证通过（libFAudio.so + 8个头文件 + pkg-config + cmake config）

CMake configure 命令：
```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_C_COMPILER_WORKS=TRUE \
  -DCMAKE_C_ABI_COMPILED=TRUE \
  -DBUILD_SDL3=OFF \
  -DBUILD_SHARED_LIBS=ON \
  -DBUILD_UTILS=OFF \
  -DBUILD_TESTS=OFF \
  -DFAUDIO_INSTALL=ON \
  -DCMAKE_C_STANDARD=99 \
  ..
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络无法直连 GitHub | 使用 gh-proxy.com 镜像下载 |
| 2 | CMake 不识别 HarmonyOS | cmake 无 HarmonyOS 平台定义 | 设置 CMAKE_SYSTEM_NAME=Linux |
| 3 | CMake 编译器检测失败 | 鸿蒙安全机制导致 cmake 内部测试执行 make 时 permission denied | 设置 CMAKE_C_COMPILER_WORKS=TRUE 和 CMAKE_C_ABI_COMPILED=TRUE |
| 4 | ~/usr/local/bin/cmake permission denied | 未通过安全弹窗的本地 cmake 二进制 | 使用 /data/service/hnp/bin/cmake（已签名的 HNP 版本） |
| 5 | FAudio 默认构建 SDL3 后端 | BUILD_SDL3=ON 为默认值 | 设置 -DBUILD_SDL3=OFF 使用已安装的 SDL2 |

## 源码修改

无源码修改。FAudio 原始源码在鸿蒙环境下通过上述 CMake 参数可成功编译。

## 依赖版本

- SDL2: 2.30.10（已通过预编译包安装到 ~/usr/local）
- libc: musl/鸿蒙 libc

## 验证结果

```bash
pkg-config --modversion FAudio → 0.26.05
pkg-config --libs FAudio → -L/storage/Users/currentUser/usr/local/lib -lFAudio
pkg-config --cflags FAudio → -I/storage/Users/currentUser/usr/local/include
llvm-readelf -d libFAudio.so.0.26.05 → NEEDED: libSDL2-2.0.so.0, libc.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libFAudio.so.0.26.05 | 280KB | 共享库 |
| libFAudio.so.0 | → libFAudio.so.0.26.05 | SONAME 软链接 |
| libFAudio.so | → libFAudio.so.0 | 开发软链接 |
| 8个头文件 | - | F3DAudio.h, FACT.h, FACT3D.h, FAPO.h, FAPOBase.h, FAPOFX.h, FAudio.h, FAudioFX.h |
| FAudio.pc | - | pkg-config 文件 |
| FAudioConfig.cmake | - | CMake 配置文件 |

## 注意事项

- FAudio 是纯库项目，无可执行文件，G4 门禁中"无二进制文件"是预期行为
- 编译时需要使用 HNP cmake（/data/service/hnp/bin/cmake），而非本地编译的 cmake
- 需显式设置 -DBUILD_SDL3=OFF 来使用 SDL2，否则默认会尝试构建 SDL3 后端
---

**编译结束**: 2026-05-26 11:33
**最终状态**: built

# frei0r-plugins 3.1.3 适配笔记

## 编译环境
- 构建系统: cmake (out-of-source build)
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `python3 ohc-run.py init-build frei0r-plugins 3.1.3 --url=https://github.com/dyne/frei0r/archive/refs/tags/v3.1.3.tar.gz`
2. 创建 toolchain 文件 `$HOME/tmp/ohos-toolchain.cmake` (CMAKE_SYSTEM_NAME=Linux)
3. `cd $BUILD_SRC_DIR/build && cmake -DCMAKE_TOOLCHAIN_FILE=$HOME/tmp/ohos-toolchain.cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DWITHOUT_OPENCV=ON -DWITHOUT_GAVL=ON ..`
4. `make -j2` → 成功 (159 plugins built)
5. `make install DESTDIR=$TEST_PREFIX` → 成功 (157 .so files + headers + frei0r.pc)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake configure failed: "System is unknown to cmake, create: Platform/HarmonyOS" | cmake 4.1.2 不认识 HarmonyOS 系统，导致 try_compile 测试失败 | 创建 toolchain 文件设置 CMAKE_SYSTEM_NAME=Linux |
| 2 | OpenCV not found | OpenCV 未预装 | -DWITHOUT_OPENCV=ON 禁用 OpenCV 相关插件 (facebl0r, facedetect) |
| 3 | gavl not found | gavl 未预装 | -DWITHOUT_GAVL=ON 禁用 gavl 相关插件 |
| 4 | std::future 不可用 | musl libc 限制 | kaleid0sc0pe 自动启用 -DNO_FUTURE |

## 源码修改

无需修改源码。仅需提供 cmake toolchain 文件。

## 依赖版本

- cairo 1.18.4 (预编译包)
- freetype 2.14.3 (预编译包)

## 验证结果

frei0r-plugins 是插件库，无可执行二进制。编译产出 157 个 .so 插件文件。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| frei0r-plugins-3.1.3-ohos-aarch64.tar.gz | TBD | 预编译包 |
| ohos-toolchain.cmake | 0.2KB | cmake toolchain 文件 |

## 注意事项

- cmake toolchain 文件（ohos-toolchain.cmake）需随补丁一起保存，用于 G0 干净构建验证
- frei0r-plugins 无 bin/ 目录，只有 lib/frei0r-1/ 下的 .so 插件文件
- PKG_CONFIG_PATH 需包含 ~/usr/local/lib/pkgconfig 才能找到 cairo
---

**编译结束**: 2026-08-06 12:11
**最终状态**: published

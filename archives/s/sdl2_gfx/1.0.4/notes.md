# sdl2_gfx 1.0.4 适配笔记

## 编译环境
- 构建系统: autotools（实际手动编译）
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 先编译SDL2 v2.30.10静态库：
   ```bash
   # SDL2需编译为静态库（musl libc缺少pthread_setcanceltype，无法编译共享库）
   cmake -DSDL_SHARED=OFF -DSDL_STATIC=ON \
         -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
   make -j$(nproc)
   make install
   ```
2. 下载SDL2_gfx 1.0.4源码并解压
3. 修改config.guess和config.sub添加HarmonyOS识别
4. autotools因HMDFS文件系统权限问题(config.status无法写入)，改用手动编译：
   ```bash
   # 手动编译所有源文件
   clang -fPIC -O2 -I$HOME/usr/local/include/SDL2 \
         -D_GNU_SOURCE=1 -D_REENTRANT \
         -c SDL2_gfxPrimitives.c SDL2_rotozoom.c SDL2_framerate.c SDL2_imageFilter.c
   # 生成共享库
   clang -shared -o libSDL2_gfx.so.2.0.0 *.o \
         -L$HOME/usr/local/lib -lSDL2 -lm
   # 生成静态库
   ar rcs libSDL2_gfx.a *.o
   ```
5. 安装到DESTDIR并制作预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess无法识别HarmonyOS | HarmonyOS不在GNU config已知列表(E007) | 添加HarmonyOS检测分支(aarch64-unknown-linux-ohos) |
| 2 | autotools config.status权限问题 | HMDFS文件系统umask 077导致目录权限0700(E050) | 改用手动编译(clang -fPIC -O2)替代autotools |
| 3 | SDL2无法编译为共享库 | musl libc缺少pthread_setcanceltype | 编译SDL2为静态库(SDL_SHARED=OFF) |
| 4 | SDL2_gfx链接SDL2 | SDL2_gfx依赖SDL2头文件和库 | 先编译安装SDL2静态库 |

## 源码修改

- `0001-config.guess.patch`: 添加HarmonyOS系统识别(aarch64-unknown-linux-ohos)
- `0002-config.sub.patch`: 在linux-ohos系统名识别列表中添加ohos后缀

## 依赖版本

- SDL2 v2.30.10（静态库）

## 验证结果

```bash
# 验证共享库
$ file libSDL2_gfx.so.2.0.0
ELF shared library, aarch64

# 验证静态库
$ file libSDL2_gfx.a
current ar archive

# 头文件检查
$ ls include/SDL2/
SDL2_gfxPrimitives.h  SDL2_rotozoom.h  SDL2_framerate.h  SDL2_imageFilter.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sdl2_gfx-1.0.4-ohos-aarch64.tar.gz | 1.9MB | 预编译包（共享库+静态库+头文件） |
| sdl2_gfx-1.0.4-ohos-aarch64-debug.tar.gz | 388KB | 调试符号包 |

## 注意事项

1. SDL2必须先以静态库方式编译安装，SDL2_gfx才能正确链接
2. autotools在HMDFS文件系统上有权限问题，建议使用手动编译方式
3. 本库提供图形绘制基本功能（线、圆、多边形等）和图像旋转缩放功能

---

**编译结束**: 2026-05-25 23:15
**最终状态**: built
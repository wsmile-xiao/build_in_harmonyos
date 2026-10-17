# lbreakouthd 1.2.3 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带生成 configure，2026-06-22）
- 编译日期: 2026-09-20
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin）
- 状态: built（conan create 验证通过后可标 published）
- 产物: 单一可执行 `lbreakouthd`（src/Makefile.am bin_PROGRAMS）+ levels/themes 数据 + po 翻译

## 编译步骤

```bash
# 1. 依赖注入环境（conan ohpcd 包: sdl2/sdl2_image/sdl2_mixer/sdl2_ttf/gettext/libintl）
#    PATH 加 sdl2-config 与 gettext 工具 bin；
#    CPPFLAGS/LDFLAGS 指各包 include/lib；PKG_CONFIG_PATH 指各包 lib/pkgconfig
./configure --prefix=$DEFAULT_PREFIX
make -j1
make check            # 上游无测试目标，仅 automake 空 check-am=all-am（rc=0）
make install DESTDIR=$TEST_PREFIX
# 无头冒烟: SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 12 lbreakouthd
#   -> 打印版本横幅、完成 SDL/config/hiscores/theme 初始化、菜单循环存活（rc=124），不崩溃
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: unable to guess system type / Invalid configuration aarch64-linux-ohos | config.guess/config.sub 不认识 HarmonyOS（E007） | 打补丁：config.guess 加 `*:HarmonyOS:*:*` 分支输出 aarch64-unknown-linux-ohos；config.sub 加 linux-ohos 三元组/OS/内核列表 |
| 2 | config.status: confXXXXXX/subs1.awk: Permission denied | configure 用 `umask 077` 建临时目录，HMDFS setgid 下生成 drwx--S--- 不可写（E046） | configure 中 `umask 077` → `umask 022`（SDL2 配方同款修复） |
| 3 | SDL_image.h: unknown type name 'SDL_Texture/SDL_Renderer' 等 20 错 | src/sdl.h 先含 SDL_image.h 再含 SDL.h；SDL_image.h 内引号 `"SDL.h"` 在大小写不敏感 FS 上经 `-I.` 命中项目自身 src/sdl.h（环形包含） | src/sdl.h 调整 include 顺序，SDL.h 放最前（补丁 0005） |
| 4 | tools.h: unknown type name 'uint' | OHOS libc 的 sys/types.h 不被 stdio/dirent 等传递包含，`uint` 未定义（上游仅 WIN32 下 typedef） | tools.h 显式 `#include <sys/types.h>`（补丁 0006） |
| 5 | 链接: undefined reference to FT_*（freetype 等） | 静态 libSDL2_ttf.a 需 freetype，libSDL2_image.a 需 tiff/webp/jpeg/z，configure 的 LIBS 不含传递库 | 配方用 AutotoolsDeps（env LIBS 被 configure 继承，实测 conftest 收到 -lfreetype）+ LDFLAGS -L |
| 6 | 无头运行 SIGSEGV（renderer 为 NULL） | dummy 视频驱动无加速渲染器，SDL_CreateRenderer(ACCELERATED) 返回 NULL，上游不处理 | sdl.cpp 回退 SDL_RENDERER_SOFTWARE（补丁 0004，通用可移植修复） |
| 7 | sdl2-config 在 OHOS 交叉环境缺失（预判失败点） | 上游 configure.ac 硬编码 `sdl2-config --cflags/--libs` | 实际 ohpcd sdl2 包自带自包含 sdl2-config（bin/），配方 generate() 将其 bin 加入 PATH 即可 |

## 源码修改（6 个补丁）

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | config.guess | HarmonyOS uname 识别 → aarch64-unknown-linux-ohos |
| 0002 | config.sub | 接受 aarch64-unknown-linux-ohos 三元组 |
| 0003 | configure | umask 077→022（HMDFS 临时目录可写） |
| 0004 | src/sdl.cpp | 软件渲染器回退（无加速驱动/无头环境） |
| 0005 | src/sdl.h | SDL.h 先于 SDL_image.h 包含 |
| 0006 | src/tools.h | #include <sys/types.h> 提供 uint |

## 依赖版本

- sdl2/2.30.10（ohpcd，静态 libSDL2.a + bin/sdl2-config）
- sdl2_image/2.6.0（libSDL2_image.a，传递 libtiff/libwebp/libjpeg/z）
- sdl2_mixer/2.8.1（libSDL2_mixer.a，裁剪后仅 WAV/MP3）
- sdl2_ttf/2.24.0（libSDL2_ttf.a，传递 freetype）
- gettext/0.22.5（libintl.a + msgfmt/msgmerge 工具；NLS 本次关闭，英文运行）
- libintl/0.26.1

## 验证结果

```bash
# 上游测试清点（R51）: tarball 无 tests/ 目录；Makefile.am 无 TESTS/check_PROGRAMS；
#   make check -> "Nothing to be done for 'check-am'" rc=0（automake 空目标）
# 无头冒烟 3/3 通过: SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 15 lbreakouthd
#   rc=124（菜单循环存活）、输出含 "lbreakouthd 1.2.3" 横幅与 "fell back to software renderer"
# 产物: arm64 ELF, NEEDED libfreetype.so.6/libc++_shared.so/libc.so（静态链 SDL2 全家）
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/l/lbreakouthd/1.2.3/conanfile.py | autotools 配方（AutotoolsDeps + AutotoolsToolchain） |
| conandata.yml | SourceForge 官方源 + sha256 + 6 补丁声明 |
| test_package/ | 无头冒烟测试（实质执行被测二进制） |
| commands.json | 软件级 tool 声明（R38） |
| src/lbreakouthd | 4.7MB arm64 可执行 |

## 注意事项

- NLS（gettext 翻译）本次未启用（AM_GNU_GETTEXT external 检测未找到 libintl，ENABLE_NLS=undef）；游戏英文运行不受影响。如需启用需让 gettext.m4 找到 -lintl。
- 运行需 SDL dummy 或真实渲染环境；无 GPU 加速时依赖补丁 0004 的软件渲染回退。
- 静态链 SDL2 系列，运行期仍需 libfreetype.so.6/libtiff.so.6/libwebp.so.7/libc++_shared.so（conanrun 环境自动提供）。
---

**编译结束**: 2026-09-20 22:18
**最终状态**: built

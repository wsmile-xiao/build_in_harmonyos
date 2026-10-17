# LBreakoutHD

## 简介

LBreakoutHD 是 LGames 出品的经典打砖块（Breakout）游戏的现代 HD 主题版本。玩法在传统打砖块基础上加入道具系统（激光、多球、加长挡板等）、Boss 战与关卡设计，含完整的关卡/主题数据与多语言翻译（po）。

## 依赖

基于 SDL2 全家桶，全部由 ohpcd 制品仓提供（conan requires）：

- sdl2/2.30.10（静态 libSDL2.a + bin/sdl2-config）
- sdl2_image/2.6.0（libSDL2_image.a，传递 libtiff/libwebp/libjpeg/z）
- sdl2_mixer/2.8.1（libSDL2_mixer.a）
- sdl2_ttf/2.24.0（libSDL2_ttf.a，传递 freetype）
- gettext/0.22.5 + libintl/0.26.1（NLS 本次未启用，英文运行）

## OHOS 适配要点

1. **config.guess/config.sub 补丁**（0001/0002）：autotools 无法识别 HarmonyOS 三元组，补丁让 configure 输出/接受 `aarch64-unknown-linux-ohos`（E007）。
2. **configure umask 补丁**（0003）：`umask 077` → `022`，修复 HMDFS setgid 目录下 configure 临时文件不可写（E046）。
3. **SDL 头文件包含顺序**（0005）：src/sdl.h 将 `SDL.h` 调整到 `SDL_image.h`/`SDL_ttf.h` 之前——后者内部引号 `"SDL.h"` 在大小写不敏感文件系统上经 `-I.` 命中项目自身 sdl.h，造成环形包含（E481）。
4. **uint 类型缺失**（0006）：src/tools.h 显式 `#include <sys/types.h>` 提供 `uint`（OHOS libc 不传递包含，E482）。
5. **软件渲染器回退**（0004）：src/sdl.cpp 在 `SDL_CreateRenderer`（加速）返回 NULL 时回退 `SDL_RENDERER_SOFTWARE`，适配无 GPU 加速/无头（dummy）环境（E483）。
6. **数据布局**：configure 使用 `--disable-install`，`--prefix` 只安装单一可执行 `lbreakouthd`；`levels/`、`themes/` 等数据由 conan 配方从构建目录 copy 到包内，保证运行期资源完整。

全部 6 个补丁均无 `__OHOS__` 平台宏（纯可移植修复，R8）。

## 验证

- 上游无测试目标（Makefile.am 无 TESTS/check_PROGRAMS、无 tests/ 目录，`make check` 为 automake 空目标 rc=0）。
- 无头冒烟测试 3/3 通过：`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 15 lbreakouthd`，进程存活至超时（rc=124），输出版本横幅与 "fell back to software renderer"。

## 参考

- 官网: https://lgames.sourceforge.net/LBreakoutHD/
- 源码: https://sourceforge.net/projects/lgames/files/lbreakouthd/
- 适配版本: 1.2.3（详见 `1.2.3/` 下 conanfile.py / notes.md / patches/）

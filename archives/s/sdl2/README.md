# SDL2

## 简介

SDL2（Simple DirectMedia Layer 2）是一个跨平台的多媒体库，提供音频、键盘、鼠标、游戏控制器和图形硬件的低级访问接口。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 2.30.0 | published | 2026-05-19 |
| 2.30.10 | published | 2026-08-24 |
| 2.32.10 | pending | 2026-08-25 |

## 依赖

- 无外部依赖（自包含库）

## 编译说明

SDL2 使用 CMake 构建，支持 autotools 作为备选方案。

### HarmonyOS 平台适配

- `pthread_setcanceltype` 通过 `HAVE_PTHREAD_SETCANCELTYPE` 能力探测选择，
  缺失时保持协作式线程退出路径。
- Windows 主机交叉编译必须在首次 compiler probe 前设置
  `CMAKE_SYSTEM_NAME=HarmonyOS`、真实 target triplet 与 sysroot。
- 2.32.10 使用能力探测启用 OHAudio 输出及 NativeWindow/EGL/GLES2 视频后端；源码补丁不新增名称含 `OHOS` 的条件宏。
- 普通 `SDL_CreateWindow` 的原生窗口路径必须由同进程 ArkUI Surface 提供，并在真机验证渲染交换与非 dummy 音频进展。

## 使用方法

```bash
# pkg-config
pkg-config --cflags sdl2
pkg-config --libs sdl2

# sdl2-config
sdl2-config --version
sdl2-config --cflags
sdl2-config --libs
```

## 相关链接

- 官网: https://www.libsdl.org/
- 源码: https://github.com/libsdl-org/SDL

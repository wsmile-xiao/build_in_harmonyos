# logstalgia

Web server access log visualization tool — replays or streams web server
access logs as a retro arcade game simulation (SDL2 + desktop OpenGL).

## 上游地址

- 主页：https://logstalgia.io/
- 仓库：https://github.com/acaudwell/Logstalgia

## 版本

- 1.1.4（2026-09-09 适配，HarmonyOS PC aarch64）

## OHOS 适配要点

- 图形栈：gl4es/1.1.6 提供桌面 GL 兼容层（libGL.so → GLES2），GLU/GLEW 由
  配方内 compat shim 提供（详见 1.1.4/notes.md）。
- 运行时需 `LIBGL_GLES=/system/lib64/libGLESv3.so`、
  `LIBGL_EGL=/system/lib64/libEGL.so`（conan runenv 已内置）。

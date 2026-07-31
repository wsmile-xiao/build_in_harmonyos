# EGL — Khronos EGL Desktop Implementation (Norbert Nopper)

## 简介
EGL 是 Norbert Nopper 维护的 Khronos EGL 1.5 桌面实现,提供跨平台 EGL 抽象层:
原生后端 WGL(Windows)/GLX+X11(Linux)/Wayland,并通过系统 libEGL/libGLESv2 转发 OpenGL ES。
上游仓库同时附带多个 HDR/colorspace 示例。

- 上游: https://github.com/McNopper/EGL
- 许可证: MIT
- 构建系统: CMake(C/C++17)
- 版本: 1.0.5

## OHOS 适配要点
- **仅接受 OHOS 平台**:`conanfile.py` 限定 `settings.os == "OHOS"`,其他平台直接报错退出。
- **新增 OHOS 后端** `src/egl_ohos.cpp`:通过 `dlopen("libEGL.so")` 转发系统 EGL 调用,
  不引入 X11/Wayland/Vulkan。`CMakeLists.txt` 用 `CMAKE_SYSTEM_NAME STREQUAL "OHOS"` 选择后端,
  链接 `CMAKE_DL_LIBS`,并跳过 `examples` 子目录。
- **静态构建**:产物为 `libEGL.a`,仅打包 `include/EGL`、`include/KHR` 头与静态库。
- **真实能力**:
  - 系统 EGL 配置枚举(`eglChooseConfig`/`eglGetConfigAttrib`)
  - pbuffer surface(`eglCreatePbufferSurface`/`eglDestroySurface`)
  - OpenGL ES context(`eglCreateContext`/`eglMakeCurrent`/`eglDestroyContext`)
  - `eglGetProcAddress`、`eglSwapBuffers`、`eglTerminate` 均转发系统 EGL。
- **明确不支持**:window surface 与 pixmap surface 在无原生窗口系统的 OHOS 后端下
  分别返回 `EGL_BAD_MATCH` 与 `EGL_BAD_NATIVE_PIXMAP`,不假装支持。

## 依赖
无 Conan 依赖。运行期依赖 OHOS 系统库 `/system/lib64/libEGL.so`(由 `dlopen` 加载)。

## 验证
`test_package/` 真实运行 EGL 生命周期:
`eglInitialize` → `eglBindAPI(EGL_OPENGL_ES_API)` →
选择 `EGL_PBUFFER_BIT` + `EGL_OPENGL_ES3_BIT` config →
创建 1×1 pbuffer(OHOS 真机 EGL 1.4 拒 ≥2px pbuffer) → 创建 ES3 context → `eglMakeCurrent` →
`eglGetProcAddress("glGetString")` → 解绑与销毁。

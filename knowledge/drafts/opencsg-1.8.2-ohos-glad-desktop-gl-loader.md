# 自带 glad 运行时 dlopen 桌面 GL 的库在 HarmonyOS 上的适配

> 草稿（DRAFT）。与同目录 `opencsg-1.8.2-ohos-glad-desktop-gl-loader.kv` 成对。

## 现象

用 OHOS 工具链 configure 时：

```text
CMake Error at .../FindPackageHandleStandardArgs.cmake:230 (message):
  Could NOT find OpenGL (missing: OPENGL_opengl_LIBRARY OPENGL_glx_LIBRARY)
Call Stack (most recent call first):
  src/CMakeLists.txt:36 (find_package)
```

但该目标其实**不链接任何 GL 库**——它自带一份私有 glad（符号收入库自身命名空间），
所有 GL 入口点都在运行时 `dlopen` 解析。

## 根因

1. **`find_package(OpenGL REQUIRED)` 是多余的**：CMakeLists 沿用了"传统 GL 程序"的写法，
   而链接行里没有 `OpenGL::GL`。HarmonyOS 的 sysroot 没有桌面 GL 开发包
   （无 `libGL.so` / `libGLX`），这个 REQUIRED 查找必然失败。
2. **加载器的库名候选不适配 OHOS**：glad 生成代码的非 Win32/Apple 分支只尝试
   `libGL.so.1` / `libGL.so`。而 HarmonyOS 提供的是：
   - `libGLv4.so`：**桌面 GL** 入口库，导出 `glBegin` / `glGetString` / ARB FBO /
     ARB·NV 遮挡查询等约 840 个 GL 符号；
   - `libEGL.so`：`eglGetProcAddress` 的所在地（不是 `libGL.so`）。

## 解决方案

两处平台适配，均不改变上游渲染逻辑：

1. `find_package(OpenGL REQUIRED)` → `find_package(OpenGL)`（可选）。目标不链接 GL，
   查找本无必要；其他平台仍会正常查找，行为向后兼容，补丁无需 `#ifdef __OHOS__`。
2. glad 加载器（POSIX 通用改写，**不引入 `__OHOS__` 等平台宏**，仅用 glad 自带的
   `GLAD_PLATFORM_APPLE` / `GLAD_PLATFORM_WIN32` 守卫；遵守 iron-rules R8 / preflight PF5）：
   - `glad_gl_dlopen_handle()` 的 `NAMES[]` 末尾追加 `"libGLv4.so"`（保留原候选在前作回退）；
   - `glad_gl_build_userptr()` 的过程地址助手改为 **GLX 优先、EGL 兜底**：先取
     `glXGetProcAddressARB`，取不到再取 `libEGL.so` 的 `eglGetProcAddress`；
     未命中的入口点由 `glad_gl_get_proc` 的 `dlsym` 兜底；
   - `libEGL.so` 的 handle 进程内常驻，防止承载入口点的库被提前卸载。

## 范围与限制

- 适用于**桌面 GL**（固定管线 `glBegin`/`glEnd`、ARB FBO、ARB/NV 遮挡查询）。
- 纯 GLES 设备需要额外的 GLES→桌面 GL 兼容路径，不在本方案范围。
- `dlopen` 失败通常是**静默**的（`gladLoaderLoadGL()` 返回 0，不报错），
  因此必须显式探测，不能只看"编译通过"。

## 验证要点

- 交叉编译后 `DT_NEEDED` 不应出现任何 GL 库（只有 C++ 运行时 / libc）。
- 产物中应能 `strings` 到 `libGLv4.so` / `libEGL.so` / `eglGetProcAddress`。
- 设备侧确认 `libGLv4.so`、`libEGL.so` 存在且导出所需符号。

## 适用范围

凡"自带 glad/glew 私有拷贝 + 运行时 dlopen 桌面 GL"的库（CAD/建模/可视化类渲染库），
在 HarmonyOS 上都要确认两点：CMake 的 GL 查找是否 REQUIRED、加载器候选是否包含
`libGLv4.so` 且过程地址助手取 `libEGL.so`。产物链接自查看
`opencsg-1.8.2-dt-needed-verification-for-runtime-dlopen-libs`。

## 证据（opencsg 1.8.2）

```text
本机交叉编译: configure 不再因 OpenGL 缺失失败；libopencsg.so.1.8.2 链接成功
DT_NEEDED:    libc++_shared.so, libc.so           ← 无 GL 链接依赖
字符串:       libGLv4.so / libEGL.so / eglGetProcAddress 均在
设备 shadow CI: conan create 通过；L0-L5 全通过
test_package:  [ok] libGLv4.so exports glGetString
               [ok] libEGL.so exports eglGetProcAddress
设备产物:     libopencsg.so 346560 bytes，885 个 OpenCSG 导出符号
```

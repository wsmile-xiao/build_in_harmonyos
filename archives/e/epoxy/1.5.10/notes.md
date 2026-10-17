# epoxy 1.5.10 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-20
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 源码
- 官方源（R39）：https://download.gnome.org/sources/libepoxy/1.5/libepoxy-1.5.10.tar.xz
- sha256（tar.xz）：072cda4b59dd098bba8c2363a6247299db1fa89411dc221c8b81b8ee8192e623
- （历史分支曾用 codeload GitHub tag tarball tar.gz，sha256 为 a7ced37f...；
  本配方按 R39 优先采用 download.gnome.org 官方镜像 tar.xz，需重新计算 sha256）

## 编译步骤

1. **下载官方源**（tar.xz，223KB）
   ```bash
   curl -fsSL -o libepoxy-1.5.10.tar.xz "https://download.gnome.org/sources/libepoxy/1.5/libepoxy-1.5.10.tar.xz"
   sha256sum libepoxy-1.5.10.tar.xz
   # 072cda4b59dd098bba8c2363a6247299db1fa89411dc221c8b81b8ee8192e623
   ```

2. **conan create**（配方：archives/e/epoxy/1.5.10/conanfile.py，profile：ohos-aarch64）
   ```bash
   conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
   ```
   meson 配置参数：`-Dx11=false -Dglx=no -Degl=auto -Dtests=false -Ddocs=false -Dwrap_mode=nodownload`。

3. **test_package**（真实 GL/EGL 派发测试，R34）
   ```bash
   # 经 epoxy 派发表做完整 EGL/GLES3 生命周期
   epoxy_has_egl() → eglGetDisplay → eglInitialize(1.4) → eglBindAPI(ES)
   → eglChooseConfig(ES3) → eglCreatePbufferSurface(1x1) → eglCreateContext(ES3)
   → eglMakeCurrent → epoxy_gl_version()==32 → epoxy_is_desktop_gl()==false
   → epoxy_egl_version()==14 → release/destroy/terminate
   # 15 项断言全部通过
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 生成 glx dispatch 编译失败 | OHOS 无 X11/GLX，<GL/glx.h> 不在 sysroot | `-Dx11=false -Dglx=no`（OHOS meson 系统名 harmonyos 默认 glx=auto 会启用） |
| 2 | 运行时 dlopen 失败 | OHOS 只有无版本号 libEGL.so/libGLESv2.so，没有 libEGL.so.1/libGLESv2.so.2/libGL.so.1 | 补丁 0001：POSIX 候选回退（先试 libEGL.so.1，无则 libEGL.so；libGLESv2.so.2→libGLESv2.so；libGL.so.1→libGL.so/libGLESv3.so） |
| 3 | epoxy_gl_version() 返回 0（stub） | OHOS libGLESv2.so 的 gl* 动态符号是 stub，调用返回 NULL；GL/GLES 函数必须经 eglGetProcAddress | 补丁 0001：gl_dlsym/gles1/2/3_dlsym 通用先走 epoxy_get_proc_address（eglGetProcAddress）再回退 dlopen/dlsym，OHOS stub 场景通用 |
| 4 | dispatch_common.h 平台分支落入 else | OHOS 应等同 Android（EGL 启用、GLX/WGL 禁用） | （0002 已合并至 0001：dispatch_common.h 的平台分支由 0001 的运行时 fallback 替代，无需单独宏） |
| 5 | Meson.compile() 不存在 | 本环境 conan 2.29.1 的 Meson 工具只有 build() | 配方改用 meson.build() |
| 6 | （历史 codeload）URL get() 报 BadZipFile | basename 无扩展名被误判为 zip（E276） | 本配方改用 download.gnome.org tar.xz，basename 带 .tar.xz 扩展名，get() 按扩展名正确解压，无需显式 filename |

## 源码修改

- `patches/0001-src-dispatch_common.c.patch`：OHOS 运行时库名映射 + GL/GLES 解析改走 eglGetProcAddress
- 补丁由 `refresh-patch --auto` 流程生成（与历史分支一致，aarch64 必需补丁）

## 依赖版本

无外部依赖（纯 meson 库）。

## 验证结果

```bash
conan-verify epoxy 1.5.10
# G0-G4 + L2/L4/L5 全部 PASS
# conan create: 成功
# test_package: [ ALL PASS ] epoxy 1.5.10 GL/EGL dispatch (15 checks)
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libepoxy.so.0.0.0 | 共享库（OHOS codesign，.codesign 段已写入） |
| lib/libepoxy.so.0, lib/libepoxy.so | SONAME/无版本软链 |
| include/epoxy/*.h | common.h/gl.h/egl.h + 生成的 gl_generated.h/egl_generated.h |
| lib/pkgconfig/epoxy.pc | epoxy_has_egl=1, epoxy_has_glx=0, epoxy_has_wgl=0 |

## 注意事项

1. OHOS 设备 EGL 1.4 只接受 1x1 pbuffer（eglCreatePbufferSurface 拒绝 >=2px），test_package 用 1x1。
2. 共享库必须 codesign（binary-sign-tool），否则动态加载失败。
3. 下游 gtk+ 3.24.38 依赖本包（archives/g/gtk+/3.24.38/manifest.yaml dependencies 含 epoxy/1.5.10）。
4. 本地构建验证无法真正发布到制品仓（发布需 CI release 流水线 conan upload），本地只能 conan create + 验证可被下游解析。状态如实标记为 built。
---

**编译结束**: 2026-08-20 13:39
**最终状态**: built

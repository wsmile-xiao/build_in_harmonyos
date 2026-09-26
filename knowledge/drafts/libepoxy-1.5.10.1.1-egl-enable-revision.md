# libepoxy EGL 启用修订（OHOS 无窗口 GL 分发）— 知识草稿

> 配对草稿：`libepoxy-1.5.10.1.1-egl-enable-revision.kv`
> 状态：draft（本任务 new_draft 决定，随 libepoxy 归档 PR 交付）
> 日期：2026-09-23

## 问题（真实证据）

gtk4/4.22.4-r1 R05 验收 quality_rework_required：gsk GL 用例失败
`GLX not supported` SIGTRAP。根因链：

1. ohpcd 已发布 libepoxy/1.5.10.1 构建选项 **egl=no**（X11 后端用 GLX，EGL 禁用）
2. 生成的 `epoxy.pc` 不声明 `epoxy_has_egl=1` → gtk4 meson 编译期无 `HAVE_EGL`
3. gtk4 gsk GL 无法走 mesa EGL/GLES2 surfaceless 路径（mesa 24.3.4.1.1 客户端栈
   已可独立创建 EGL/GLES2 surfaceless 上下文）

## 根因

- libepoxy 侧缺 EGL 分发表与 pkg-config 声明；`egl_generated_dispatch.c` 编译期
  强制 `#include "EGL/eglplatform.h"`（gen_dispatch.py），OHOS 无该头
- mesa package_info 未设 `pkg_config_name` → PkgConfigDeps 只生成 mesa.pc，
  meson `dependency('egl')` 找不到 → 需复制 mesa 包内 egl.pc 等并修正 prefix
- 运行期 epoxy 保守版本检查：无当前 display 时返回 14，EGL 1.5 平台入口
  （eglGetPlatformDisplay）须先建立当前 display

## 方案（R37 版本后缀 1.5.10.1.1）

1. **版本递增** 1.5.10.1 → 1.5.10.1.1（禁止覆盖已发布版本）
2. **egl=yes**（glx=yes/x11=true 保持）；conan create 内 tests=false
   （glx_static `-static` 链动态 libX11、glx_beginend 缺 libGL 会在 OHOS 链接
   失败），上游测试改由独立验证构建运行并计双口径台账
3. **mesa/24.3.4.1.1 transitive_headers=True** 提供 EGL/GLES 头
4. **复制 mesa 包内 egl.pc/glesv1_cm.pc/glesv2.pc** 到生成目录，replace
   `prefix=/` 为 mesa package_folder（glu 9.0.3 osmesa.pc 同款）
5. **进程级验证**：用 `eglGetProcAddress` 取 GLES2 函数（勿直调 epoxy GL 分发表，
   OHOS 无 libGL 时 dlopen libGL.so.1 abort）；EGL 1.5 平台入口先经
   eglGetDisplay+eglInitialize+eglMakeCurrent 建立当前 display

## 验证（真实证据）

- `nm libepoxy.a`：148 个 `epoxy_egl*` 符号（epoxy_eglInitialize/epoxy_eglChooseConfig/
  epoxy_eglCreateContext/epoxy_eglGetProcAddress + `epoxy_has_egl` T 符号）
- `epoxy.pc`：`epoxy_has_egl=1`、`epoxy_has_glx=1`
- 进程级 EGL/GLES2 surfaceless 消费者验证（仅链 libepoxy.a）exit 0：
  eglGetPlatformDisplay(SURFACELESS_MESA) via epoxy 成功、eglCreateContext(GLES2)
  + eglMakeCurrent(EGL_NO_SURFACE) 成功、eglGetProcAddress(glGetString) →
  `"OpenGL ES 3.2 Mesa 24.3.4"`
- 对照 1.5.10.1（egl=no）：无 epoxy_egl* 符号、epoxy.pc 无 epoxy_has_egl

## 适用边界

- 适用：任何依赖 GL/EGL 分发的库在 OHOS 的适配（gtk4 gsk GL、GDK GL、
  其他经 epoxy 消费 EGL 的组件）；版本已发布需启用 EGL 的增量修订
- 反例/不适用：需要桌面 GL/GLX 的场景（OHOS 无 libGL，epoxy GL 分发表 dlopen
  libGL.so.1 必然失败，应走 EGL/GLES2 surfaceless）；有 X 显示的完整桌面环境

## 查重（七轴摘要）

- exact_duplicate: false ｜ causal_duplicate: false（E527 根因是 GTK 无显示
  后端，本候选是 libepoxy egl=no）｜ trigger_overlap: 部分（同属 OHOS 无窗口
  GL 景象，触发点不同）｜ solution_overlap: false（E527=broadway 后端替代，
  本候选=EGL surfaceless 启用）｜ combination_novelty: true ｜
  boundary_novelty: true ｜ test_migration_novelty: true
- similar_to: E527（同 OHOS GL/GUI 生态，方案不同）；conflicts_with: none
- 决定：**new_draft**（可跨库复用于依赖 GL/EGL 的库）

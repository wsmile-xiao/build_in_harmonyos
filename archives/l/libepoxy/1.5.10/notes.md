# libepoxy 1.5.10 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-02
- 编译器: clang/clang++
- 状态: published

## 适配方案（Conan 配方）

### 1. 构建选项
OHOS 无窗口系统（无 X11/Wayland/GLX/EGL），禁用相关支持：
```bash
meson setup builddir -Dglx=no -Degl=no -Dx11=false -Dtests=false
```
- glx/egl 为 combo 选项（传 `no`），x11/tests 为 boolean（传 `false`）——注意选项类型，与 atk introspection 的教训一致。

### 2. R26 静态构建
配方默认 `shared=False`，通过 `tc.project_options["default_library"] = "static"` 设置
（**不是** `tc.configure_args`——MesonToolchain 无该属性，gdk-pixbuf 曾踩坑）。

### 3. llvm-ar/llvm-ranlib 注入
conan MesonToolchain 不把 ar/ranlib 写进 native file，meson 按裸名 `llvm-ar` 探测失败
（clang 工具链在 /data/service/hnp/bin）。与 cairo/pango/atk 一致：从 c 编译器同目录
推导 llvm-ar/llvm-ranlib 全路径注入 `conan_meson_native.ini` 的 `[binaries]` 段。

### 4. gen_dispatch.py 显式 python3 调用（补丁 0001）
上游 src/meson.build 的 custom_target 直接执行 gen_dispatch.py，设备文件系统
无法 shebang 直接执行 Python 脚本（E081 同类）。补丁在 command 前加 `'python3'`。

### 5. 源码镜像
conandata.yml 仅保留官方 GitHub URL；CI Mirror fallback 在构建时自动改写为
gh-proxy.com（与 pcalc 同型，无需在配方中手动声明镜像）。

## 测试
- test_package 编译 `#include <epoxy/gl.h>` 并真实调用 `epoxy_extension_in_string()`（纯字符串解析，
  验证 libepoxy 可链接、核心分发表字符串路径可用；`epoxy_gl_version()` 会 dlopen GL 库 abort，不能调用）
- `test()` 用 `self.run` 直接执行二进制（L0d），MANIFEST.yml 已声明（L0e）

## R40 图形库适配完整性标注（需人工确认）
libepoxy 属于 R40 点名的「图形/渲染」领域（OpenGL/EGL 函数指针分发库）。
本 PR 的适配边界如下，**GL 分发表在 OHOS 上的真实可用性未经真机验证**：
- OHOS 无窗口系统，配方整体禁用 `glx/egl/x11`（无鸿蒙图形栈适配补丁）
- test_package 仅覆盖「头文件可编译 + 链接可行 + 字符串工具可运行」最小子集
  （`epoxy_extension_in_string()` 纯字符串解析；`epoxy_gl_version()` 会 dlopen GL 库
  abort，不能调用），未创建 EGL/GL 上下文、未验证真实 GL dispatch 分发表行为
- 「编译通过 + 接口测试」不构成 GL 分发表可用性证明；如有真实 GL/EGL
  消费方（如 gtk+）在 OHOS 上落地，需另行真机验证后更新本标注

## 知识沉淀
- OHOS 无 OpenGL/EGL 库，GLX/EGL/X11 必须禁用
- HMDFS 不支持 Python 脚本 shebang 直接执行，需 python3 显式调用
- HMDFS 不支持 ln -sf 覆盖，需 rm -f && ln -s 模式（package() 中补齐 .so 符号链接）

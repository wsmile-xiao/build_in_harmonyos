# DRAFT-rust-gui-glutin-winit-ohos-free-unix-split

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-rust-gui-glutin-winit-ohos-free-unix-split.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

## 适用场景

Rust GUI 应用（winit/glutin/crossfont 栈）在 aarch64-unknown-linux-ohos target 编译时报：

```
error[E0432]: unresolved import `glutin::platform::x11`
  --> src/window_context.rs:16:23
   | use glutin::platform::x11::X11GlConfigExt;
   |                       ^^^ could not find `x11` in `platform`
note: found an item that was configured out
  --> glutin-0.32.3/src/platform/mod.rs:4:9
   | #[cfg(x11_platform)]
   |       ------------ the item is gated here

error[E0599]: no method named `x11_visual` found for enum `glutin::config::Config`
error[E0599]: no variant ... named `EglThenGlx` found for enum `DisplayApiPreference`
```

或反方向（零 feature 时）：

```
error: The platform you're compiling for is not supported by winit
  --> winit-0.30.13/src/platform_impl/mod.rs:78:1
   | compile_error!("The platform you're compiling for is not supported by winit");
```

## 根因

同一 GUI 栈两代 build.rs cfg_aliases 对 `target_env = "ohos"` 分裂：

| crate | free_unix 定义 | ohos 结果 | 平台模块 |
|---|---|---|---|
| glutin 0.32.3 | `all(unix, not(apple), not(android), not(ohos_platform))` | **排除** | x11/wayland 模块均编出 |
| winit 0.30.13 | `all(unix, not(apple), not(android), not(emscripten))` | 不排除 | wayland 模块可用 |

- glutin `egl_backend = all(feature="egl", any(windows, unix), not(apple))` —— 不排除 ohos，EGL 可用。
- 应用侧（alacritty 等）x11 门控只写 `not(any(macos, windows))`——OHOS 上为 true，引用被编出的 glutin x11 API → E0432/E0599。
- 零 feature 时 winit 因 `x11_platform||wayland_platform` 均 false → compile_error。

## 解法

```
cargo build --release --locked -j 2 --no-default-features --features wayland
```

关闭 x11 feature 后应用侧全部 x11 门控代码自动编出；winit wayland 后端 + glutin egl_backend 提供窗口/GL 路径。鸿蒙 PC 即 Wayland 合成器体系，x11 在 OHOS 上无意义，无功能损失。0 源码补丁。

## 实证

alacritty 0.17.0 三轮（2026-10-07/08 设备）：
- default(wayland+x11)：E0432×2 + E0599×4 六连败；
- `--no-default-features`：winit compile_error；
- `--features wayland`：rc=0（2m43s / 6m32s / 冷缓存 15m31s 三次），上游测试 262/263 通过。

## 兜底

应用存在**无 feature 门控**的 x11/GLX 引用时：源码补丁路线——补 `#[cfg(all(feature = "x11", not(target_env = "ohos")))]` 守卫（R8 禁空壳 stub）。

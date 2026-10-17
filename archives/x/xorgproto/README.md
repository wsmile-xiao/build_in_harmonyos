# xorgproto - X11 Protocol Headers

## 简介
xorgproto 提供 X Window System 协议的头文件和 pkg-config 配置文件，是编译 X11 相关库的基础依赖。

## 功能
- 提供 X11 核心协议头文件 (X.h, Xproto.h 等)
- 提供 X11 扩展协议头文件 (Xext, Xrender, Xrandr 等)
- 提供 pkg-config 文件用于编译依赖管理

## OHOS 适配
- 使用 meson 构建系统替代 autotools（避免 HMDFS 权限问题）
- 纯头文件包，无需 ELF 签名
- 约 209 个文件（29 个 pkg-config + 151 个头文件）

## 安装
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- xorgproto 2024.1
```

## 使用
```bash
# pkg-config 验证
pkg-config --modversion xproto

# 编译时依赖
pkg-config --cflags xproto
```

## 2025.1 Conan dependency recipe

- Dependency Issue: #1280.
- Packages 156 public headers, including compiler-probed `X11/Xpoll.h`, 29
  non-legacy pkg-config modules, and 11 protocol specification documents.
- Compiles 83 independent public-header consumer tests and runs one
  package-metadata workflow covering all installed pkg-config modules.
- Keeps the single upstream keysym verification entry separate and reports its
  explicit exit-77 result as SKIP when Python `libevdev` is unavailable.
- Submits knowledge draft E229 to run compile-only Conan consumer tests directly
  with the profile compiler when CMake is unavailable on the target PC.
- Submits knowledge draft E230 to keep the generated C template visible to CI's
  L0c test-source suffix gate without adding an empty marker file.
- Submits knowledge draft E231 to reproduce target-sensitive public headers that
  are installed by upstream build definitions but absent from the source tree.

## 依赖
- 无外部依赖（纯头文件包）

## 许可证
MIT License

## 更多信息
- 官方网站: https://www.x.org/
- 源码: https://gitlab.freedesktop.org/xorg/proto/xorgproto

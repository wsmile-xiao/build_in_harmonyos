# libxcb - X C Bindings Library

## 简介

libxcb 是 X11 协议的 C 语言绑定库，提供对 X Window System 的底层访问接口；libX11 内部也依赖它。

## 功能概述

- X 协议 C 绑定（连接、事件、请求）
- 按扩展生成协议头文件与实现（依赖 xcb-proto + c_client.py）
- 通过 libXau / libXdmcp 处理认证与 XDMCP 路径

## OHOS 适配

- configure：HMDFS 下 umask 调整、bash shebang 替换
- 旧版 config.guess 不识别 HarmonyOS：仅在 OHOS 下补充 `--build/--host`
- Conan 的 `xcb-proto.pc` 需补回 `xcbincludedir` / `pythondir`，并设置 `PYTHONPATH`

## 依赖关系

| 依赖 | 版本 | 用途 |
|------|------|------|
| xcb-proto | 1.17.0 | 协议 XML 与代码生成 |
| libxau | 1.0.11 | Xauthority |
| libxdmcp | 1.1.5 | XDMCP |
| xorgproto | 2025.1 | 公共头（如 Xfuncproto.h） |
| xtrans | 1.4.0 | X 传输层源（向 libX11/libXt/libXmu 透传） |

## 参考资料

- 官网：https://xcb.freedesktop.org/
- 源码：https://gitlab.freedesktop.org/xorg/lib/libxcb
- 许可证：MIT

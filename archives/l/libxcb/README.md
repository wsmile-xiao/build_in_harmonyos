# libxcb - X C Bindings Library

## 简介
libxcb 是 X11 协议的 C 语言绑定库，提供对 X Window System 的底层访问接口。

## OHOS 适配
- 需要手动编译依赖：xcb-proto, libxau, libxdmcp
- 使用 c_client.py 生成协议头文件
- 仅编译核心协议（xproto, bigreq, xc_misc）

## 安装
库已安装到 ~/usr/local，包含：
- libxcb.a (静态库)
- libxcb.so.1.1.16 (共享库)
- xcb/xcb.h 等头文件

## 许可证
MIT License

# libXext 1.7.0 编译记录

## 编译环境
- 平台: HarmonyOS
- 编译器: clang 15.0.4
- 构建系统: 手动编译（autotools configure 不可用）

## 依赖
- libX11 1.8.7
- libxcb 1.16
- xorgproto 2024.1

## 编译步骤
1. 手动编译所有 .c 源文件（使用 -fPIC）
2. 链接动态库 libXext.so.6.4.0
3. 创建符号链接
4. 创建 pkg-config 文件

## 安装位置
- 库文件: ~/usr/local/lib/libXext.so.6.4.0
- 头文件: ~/usr/local/include/X11/extensions/
- pkg-config: ~/usr/local/lib/pkgconfig/xext.pc

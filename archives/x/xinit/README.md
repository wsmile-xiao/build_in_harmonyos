# xinit

X Window System初始化程序，用于启动X服务器和客户端会话。

## 功能

- `xinit`: X Window System初始化工具
- `startx`: X会话启动脚本

## 编译版本

- **1.4.4** (2026-06-02): HarmonyOS平台适配版本

## 依赖

需要完整的X11库链：
- libX11
- xproto
- xcb-proto
- libxcb
- xtrans
- xorgproto
- util-macros

## 使用

```bash
startx -- :0
```

## 源码

- URL: https://download.savannah.nongnu.org/releases/xinit/xinit-1.4.4.tar.gz

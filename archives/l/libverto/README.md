# libverto

libverto 是一个异步事件循环抽象库，提供循环中立的异步 API，允许库暴露异步接口并将主循环的选择权交给应用程序。支持多种后端实现：glib、libevent、libev 等。

## OHOS 适配

### 已知问题
- **平台识别**: config.guess 无法识别 HarmonyOS 系统
- **三元组验证**: config.sub 不支持 `aarch64-unknown-linux-ohos` 三元组
- **umask 权限**: configure 脚本中 `umask 077` 导致 HMDFS UID 映射权限问题

### 解决方案
- 添加 HarmonyOS case 分支到 config.guess
- 添加 ohos 操作系统白名单到 config.sub（3处修改）
- 修改 configure 中 umask 077 为 umask 022

## 依赖

### 运行时依赖
- glib 2.84.0
- libevent 2.1.12

### 编译依赖
- automake 1.16.5
- autoconf 2.72
- libtool 2.4.7
- pkg-config 0.29.2

## 功能验证

```bash
# 检查库文件
ls ~/usr/local/lib/libverto*.so*

# 验证pkg-config
pkg-config --modversion libverto
pkg-config --modversion libverto-glib
pkg-config --modversion libverto-libevent
```

## 参考

- 官网: https://github.com/latchset/libverto
- 源码: https://github.com/latchset/libverto/releases/download/v0.3.2/libverto-0.3.2.tar.gz
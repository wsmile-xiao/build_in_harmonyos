# render 0.9.12 适配笔记

## 编译环境
- 构建系统: autotools (configure/make)
- 编译日期: 2026-05-26
- 编译器: clang/clang++ (aarch64-unknown-linux-ohos target)
- 状态: built

## 编译步骤

1. init-build render 0.9.12
2. 应用 ohos 补丁: config.guess/config.sub
3. track-edit add config.guess/config.sub
4. refresh-patch --auto render 0.9.12
5. configure --prefix=/usr/local --host=aarch64-unknown-linux-ohos
6. 修改 config.status umask 077->000 (解决临时目录权限问题)
7. 运行 config.status 生成 Makefile/config.h
8. make -j2
9. make install DESTDIR=test-install-render-0.9.12

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 ohos | 原始版本不包含 HarmonyOS 支持 | 添加 ohos 识别补丁 (+13/-0, +6/-2) |
| 2 | config.status 临时目录权限被拒绝 | umask 077 + HMDFS setgid 导致 drwx--S--- | 修改 config.status umask 077->000 |
| 3 | X11/Xlibint.h 头文件未找到 | x11.pc prefix 为空 | 创建修正版 x11.pc 并加入 PKG_CONFIG_PATH |

## 源码修改

- 0001-config.guess.patch: 添加 ohos 识别 (+13/-0)
- 0002-config.sub.patch: 添加 ohos 子系统识别 (+6/-2)

## 依赖版本

- xorgproto 0.11.1 (renderproto)
- libX11 1.8.7, libxcb 1.16, libXau (from vpx-extract)
- xproto, kbproto (from usr/local)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libXrender.so.1.3.0 | 51KB | 共享库 |
| libXrender.a | 51KB | 静态库 |
| Xrender.h | - | 头文件 |
| xrender.pc | 296B | pkg-config 文件 |

## 注意事项

- config.status umask 077 权限问题是 HMDFS 特性导致，每次 configure 后需手动修改
- x11.pc prefix 为空，需通过 PKG_CONFIG_PATH 中的修正版覆盖
- 纯库项目（无可执行二进制），G2 警告为正常现象
---

**编译结束**: 2026-05-27 00:04
**最终状态**: built

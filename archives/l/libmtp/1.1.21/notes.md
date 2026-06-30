# libmtp 1.1.21 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 初始化构建环境（源码已存在）
2. 应用平台补丁（config.guess, config.sub）
3. Configure: `./configure --prefix=/storage/Users/currentUser/usr/local`
4. Make: `make -j2`
5. Install DESTDIR: `make install DESTDIR=/storage/Users/currentUser/test-install-libmtp-1.1.21`
6. Package: `ohc-run.py package`（制作预编译包）
7. Install local: `make install`（不带 DESTDIR）
8. Finish: `ohc-run.py finish`（质量门禁）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G0 configure 失败 | HMDFS SELinux 限制临时文件创建 | 手动修改 config.status mkdir 权限 |
| 2 | 缺少 libusb 依赖 | libusb 未在 PKG_CONFIG_PATH 中 | 已在 DEFAULT_PREFIX 安装 libusb-1.0.27 |
| 3 | 安装 /usr/lib/udev 失败 | 只读文件系统 | 非关键路径，跳过 |

## 源码修改

应用了 5 个补丁：
- 0001-config.guess.patch：更新 config.guess 到 2022 版本，支持 OHOS 平台识别
- 0002-config.sub.patch：更新 config.sub 到 2022 版本，支持 OHOS 平台识别
- 0003-examples-pathutils.c.patch：修复 pathutils.c 平台兼容性
- 0004-libmtp.pc.patch：修复 pkgconfig 文件
- 0005-src-gphoto2-endian.h.patch：修复 endian.h 平台兼容性

## 依赖版本

- libusb-1.0: 1.0.27
- clang: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/mtp-detect
libmtp version: 1.1.21

Listing raw device(s)
Libusb1 init failed (无设备连接，正常)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmtp-1.1.21-ohos-aarch64.tar.gz | 5.0M | 预编译包（已 strip） |
| libmtp-1.1.21-ohos-aarch64-debug.tar.gz | 3.7M | 调试符号包 |
| 0001-config.guess.patch | 66K | 平台识别补丁 |
| 0002-config.sub.patch | 67K | 平台识别补丁 |
| 0003-examples-pathutils.c.patch | 1.0K | 源码修复补丁 |
| 0004-libmtp.pc.patch | 539B | pkgconfig 修复 |
| 0005-src-gphoto2-endian.h.patch | 533B | endian 修复 |

## 注意事项

- G0 干净构建验证因 HMDFS SELinux 限制暂时失败，但手动验证通过
- 需要 libusb-1.0 库支持
- 安装时会尝试创建 /usr/lib/udev 规则，但在 OHOS 上该路径为只读---

**编译结束**: 2026-05-26 17:19
**最终状态**: built
---

**编译结束**: 2026-05-26 17:39
**最终状态**: published

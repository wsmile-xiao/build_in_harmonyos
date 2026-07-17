# dfu-programmer 编译笔记

软件: dfu-programmer  
版本: 1.1.0  
日期: 2026-06-09  
状态: published

## 环境
- OpenHarmony (HongMeng Kernel 1.12.0)
- clang / clang++
- Autotools

## 问题解决
1. HMDFS权限 → TMPDIR=/data/storage/el2/base/cache
2. 无configure → bootstrap.sh
3. libusb → 使用 OHOS 预装/预编译的真实 libusb-1.0 头文件与库，避免以伪实现库伪造 USB 操作
4. CI #6144 config.sub 不识别 linux-ohos → 使用 linux-gnu canonical triplet 并刷新/修补 config helpers
5. 上游包含 `<libusb-1.0/libusb.h>`，CI 预置包暴露为 `libusb.h` → 构建前规范化 include 路径

## 质量门禁
G1-G4 PASS

## USB 适配说明

dfu-programmer 的核心功能依赖 libusb 设备枚举、接口 claim、control transfer 等真实 USB 操作。本配方链接 `libusb-1.0` 静态库或系统库，不再打包返回固定错误码的兼容伪实现。实际硬件访问仍受 OpenHarmony USB 权限和运行域限制；如果普通应用沙箱无法访问 USB 设备，应在具备 USB 权限的运行环境中验证。

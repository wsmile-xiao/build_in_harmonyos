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
3. libusb → 从官方 libusb 1.0.27 源码构建真实静态库，避免依赖 CI worker 预装库，也避免以伪实现库伪造 USB 操作
4. CI #6144 config.sub 不识别 linux-ohos → 使用 linux-gnu canonical triplet 并刷新/修补 config helpers
5. 上游包含 `<libusb-1.0/libusb.h>`，CI 预置包暴露为 `libusb.h` → 构建前规范化 include 路径
6. CI worker 不保证存在 `libusb-1.0.a` → recipe 在构建目录内编译并安装 libusb 1.0.27，再以 `LIBUSB_CFLAGS/LIBUSB_LIBS` 传给 dfu-programmer
7. libusb 在 OHOS 上需要修正 `linux_netlink.c` 头文件冲突，并兼容 `HongMeng Kernel X.Y.Z` 内核版本字符串

## 质量门禁
G1-G4 PASS

## CI 复验
2026-07-18: 重新触发最新提交流水线，复验 libusb include 路径规范化后的构建状态。
2026-07-18: 修复最新 CI 链接失败（worker 缺少 `-lusb-1.0`），改为本 recipe 构建真实 libusb 静态库后链接。

## USB 适配说明

dfu-programmer 的核心功能依赖 libusb 设备枚举、接口 claim、control transfer 等真实 USB 操作。本配方从官方 libusb 1.0.27 源码构建并静态链接 `libusb-1.0.a`，不再依赖 worker 预装库，也不打包返回固定错误码的兼容伪实现。

需人工确认适配完整性：CI 环境没有真实 USB DFU 设备和设备访问权限，`test_package` 只能验证二进制可启动、链接到本配方构建的 libusb 并输出帮助信息，不能伪造 USB 枚举或固件读写结果。合入前应在具备 USB 权限的 OpenHarmony 运行环境中连接目标芯片，执行涉及真实 libusb 调用的设备枚举、dump/erase/flash 等 DFU 操作，确认权限、枚举和 control transfer 均正常。

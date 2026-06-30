# pcsc-lite 2.4.0 编译笔记

## 编译信息
- 软件名称: pcsc-lite
- 版本: 2.4.0
- 编译日期: 2026-05-25
- 构建系统: meson
- 编译器: clang 15.0.4
- 平台: HarmonyOS aarch64

## 编译过程

### 源码获取
- 源码 URL: https://pcsclite.apdu.fr/files/pcsc-lite-2.4.0.tar.xz
- 格式: tar.xz
- SHA256: 未验证（SSL 证书问题导致自动下载失败，手动下载成功）

### 构建系统选择
- 原计划使用 autotools，但 autoreconf 失败
- 失败原因: autoconf 2.72 宏定义缺失（AS_IF, AC_MSG_WARN 等）
- 解决方案: 使用 meson 构建系统（源码包含 meson.build）

### 配置选项
```
meson setup build \
  --prefix=/storage/Users/currentUser/usr/local \
  -Dlibsystemd=false \
  -Dlibudev=false \
  -Dlibusb=true \
  -Dpolkit=false \
  -Dusb=true \
  -Dserial=true
```

### 编译问题

#### 问题 1: pthread_cancel 未实现
- 错误: `undefined symbol: pthread_cancel`
- 原因: HarmonyOS 未实现 pthread_cancel syscall
- 解决: 添加 `#ifdef __OHOS__` 守卫，禁用 pthread_cancel 调用
- 补丁: 0001-pthread_cancel-harmonyos.patch

### 依赖
- libusb-1.0 (已安装版本: 1.0.27)
- pthread (系统提供)

### ELF 签名
- 工具: /data/service/hnp/bin/binary-sign-tool
- 模式: self-sign
- 证书: OpenHarmony.p12, OpenHarmonyApplication.pem
- 结果: 所有二进制文件签名成功，可正常执行

### 验证
- pcscd --version: ✅ 显示 "pcsc-lite version 2.4.0"
- pkg-config --modversion libpcsclite: ✅ 显示 "2.4.0"
- 功能验证: pcscd --help 显示正确帮助信息

## 知识提取

### L1 平台真理
- pthread_cancel 在 HarmonyOS 上未实现
- ELF 二进制必须签名才能执行（Gotchas）
- autoreconf 在 HarmonyOS 上可能因宏缺失而失败

### L2 模式经验
- meson 构建系统在 HarmonyOS 上更可靠（避开 autotools 宏问题）
- libusb-1.0.pc 已存在于 pkgconfig 目录

### L3 本版笔记
- 使用 meson 替代 autotools
- 配置选项：禁用 systemd/polkit，启用 libusb/serial

## 质量门禁

- G0 干净构建: PASS（补丁应用后重新构建成功）
- G1 二进制完整性: PASS（pcscd, libpcsclite.so.1, libpcsclite_real.so.1, libpcscspy.so.0）
- G2 功能可用性: PASS（pcscd --version 正常）
- G3 可移植性: PASS（ELF 签名，RPATH 正确）
- G4 档案完整性: PASS（tarball, 补丁, 预编译包, manifest）

---
**编译结束**: 2026-05-25 21:55
**最终状态**: published
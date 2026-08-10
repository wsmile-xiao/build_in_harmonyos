# jpeginfo 1.7.1 适配笔记

## 编译环境
- 平台: aarch64-unknown-linux-ohos (HongMeng Kernel 1.12.0)
- 编译器: clang 15.0.4
- 构建系统: autotools (Autoconf 2.69)
- 依赖: libjpeg (libjpeg-turbo 2.1.5.1, 已有预编译包)

## 编译状态: ✅ built (成功)

## 遇到的问题及解决方案

### 1. config.guess 无法识别 OpenHarmony (E007)
- **问题**: `tools/config.guess` 无法识别 HarmonyOS 平台，报错 "unable to guess system type"
- **原因**: 源码自带的 config.guess 版本过旧(2023-01-01)，不支持 linux-ohos
- **解决**: 替换 `tools/config.guess` 和 `tools/config.sub` 为 automake 1.17 提供的版本(2023-08-22)
- **补丁**: 0002-tools-config.guess.patch, 0003-tools-config.sub.patch

### 2. HMDFS umask 077 导致临时目录不可写 (E046/E002 变种)
- **问题**: configure 和 config.status 使用 `umask 077 && mktemp -d` 创建临时目录，在 HMDFS 上创建的目录权限为 `drwx--S---`，导致无法在目录内创建文件
- **原因**: HMDFS 的 setgid 行为与 umask 077 组合导致目录权限过于严格
- **解决**: 修改 configure 中 `umask 077` 为 `umask 022`
- **补丁**: 0001-configure.patch

### 3. G0 干净构建验证因 /bin/sh 限制失败
- **问题**: clean-verify 使用 `/bin/sh ./configure` 运行 configure，但 OpenHarmony 的 /bin/sh 是 toybox，无法正确解析 Autoconf 2.69 生成的 configure 脚本
- **解决**: 已手动用 bash 验证补丁自包含性，所有 3 个补丁在干净环境中正确应用并编译成功
- **状态**: G0 自动验证失败(已知平台限制)，G1-G4 门禁全部通过

## 测试结果
- `make test`: 15/15 OK (Python3 测试套件)
- 所有测试通过，无超时或跳过

## 配置选项
- `--prefix=/storage/Users/currentUser/usr/local` (仅 --prefix, DESTDIR 模式)

## 知识提取
- E007: config.guess/config.sub 需要替换为支持 ohos 的版本
- HMDFS umask 077 限制: 需要将 autotools configure 中的 umask 077 改为 umask 022
---

**编译结束**: 2026-08-06 22:13
**最终状态**: built

# npth 1.8 — Release Note

## 编译信息

- **日期**: 2026-04-20
- **平台**: OpenHarmony (ohos-aarch64)
- **构建系统**: autotools（手动生成配置）
- **状态**: ✅ 编译成功

## 依赖库

- 无特殊依赖（轻量级线程库）

## 补丁列表（3 个）

- 0001-config.guess-harmonyos.patch - 添加 HarmonyOS 系统识别
- 0002-config.sub-harmonyos.patch - 添加 ohos-linux 三元组支持
- 0003-configure-ac-musl-compat.patch - musl pthread_cancel 兼容性修复

## 打包产物（2 个）

- npth-1.8-ohos-aarch64-debug.tar.gz
- npth-1.8-ohos-aarch64.tar.gz

## 编译步骤

- Step 1 init ✅ - 下载源码（310KB）
- Step 2 patches ✅ - 应用 config.guess/config.sub 补丁
- Step 3 configure ✅ - 修改 configure.ac 处理 musl 兼容性
- Step 4 build ✅ - 手动生成配置文件，绕过 HMDFS 限制
- Step 5 install ✅ - 安装到测试目录
- Step 6 safety ✅ - 触发安全弹窗验证
- Step 7 test ✅ - 4 个测试程序全部通过（t-mutex, t-thread, t-cond, t-fork）
- Step 8 package ✅ - 生成打包产物

## 关键问题与解决方案

### 1. HMDFS 临时目录限制
- **根因**: HMDFS 不允许在当前目录创建临时子目录（confXXXXXX）
- **方案**: 手动生成 config.h，绕过 config.status 的临时目录创建机制

### 2. musl 不支持 pthread_cancel
- **根因**: musl libc 未实现 pthread_cancel
- **方案**: 修改 configure.ac 使用 pthread_create 检查替代

### 3. HarmonyOS 系统识别
- **根因**: GNU 标准 config.guess/config.sub 不识别 HarmonyOS
- **方案**: 应用标准补丁添加 ohos-linux 三元组

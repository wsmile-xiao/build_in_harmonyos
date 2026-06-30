# libburn

libburn 是由 libburnia-project.org 开发的开源光盘读写库，提供 CD/DVD/BD 光盘的刻录、读取、格式化和擦除功能。其命令行前端 cdrskin 提供了 cdrecord 兼容的刻录接口。

## 功能特性

- CD/DVD/BD 光盘刻录与读取
- 光盘格式化与擦除
- 多会话（multi-session）支持
- CD-TEXT 信息读写
- cdrskin 命令行工具（cdrecord 兼容模式）

## 鸿蒙平台适配说明

### 已编译版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.5.6 | published | 2026-06-01 |

### 平台适配要点

- 需替换 config.guess/config.sub 以支持 HarmonyOS 平台检测（ohos 三元组）
- HMDFS 文件系统不支持 chmod，需移除 config.status 中 `umask 077` 以避免 Permission denied
- 无物理光驱环境下 API 调用正常（设备扫描返回 0 设备，不崩溃）

### 交付物

- 预编译包: `libburn-1.5.6-ohos-aarch64.tar.gz` (3.1MB)
- 调试包: `libburn-1.5.6-ohos-aarch64-debug.tar.gz`
- 主要组件: cdrskin (命令行工具), libburn.so.4 (共享库), libburn.a (静态库), libburn.h (头文件)

## 参考

- 官网: https://libburnia-project.org
- 源码: https://files.libburnia-project.org/releases/libburn-1.5.6.tar.gz
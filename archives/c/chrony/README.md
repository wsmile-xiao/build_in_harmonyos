# chrony

chrony 是 Network Time Protocol (NTP) 的实现，提供时钟同步守护进程 `chronyd` 和命令行客户端 `chronyc`。

## 官方资源

- 主页：https://chrony-project.org/
- 源码：https://chrony-project.org/releases/chrony-4.8.tar.gz
- 许可证：GPL-2.0-only

## OpenHarmony 适配

HarmonyOS PC arm64 构建复用 Linux 兼容的时间与套接字 API。配方通过 `--host-system=Linux` 指定 chrony 平台后端，并禁用依赖不可用设备或特权服务的 RTC、PHC、PPS、privdrop 与 timestamping 功能。

## 工具

- `chronyc`：chrony 命令行客户端
- `chronyd`：时钟同步守护进程

当前版本 `4.8` 已通过 Conan OHOS arm64 构建、测试包和本地 CI 模拟验证。

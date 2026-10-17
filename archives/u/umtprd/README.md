# umtprd

轻量纯 C 实现的 USB MTP responder 守护进程（用户态，对接 FunctionFS/GadgetFS）。

通过设备 USB 口提供 MTP 文件传输；`res/umtprd.conf` 为示例配置
（守护进程默认读 `/etc/umtprd/umtprd.conf`，可用 `-conf` 覆盖）。

## 版本索引

| 版本 | 状态 | 备注 |
|------|------|------|
| 1.6.8 | built | OHOS 适配（零补丁；上游无测试套件，消费者冒烟 5 断言） |

零 conan 依赖（仅需 OHOS libc/sysroot）。

# libkysdk-base

openKylin / Kylin Team 的 Kylin SDK 基础库，把“程序开发常用能力”打包成一组共享库与配套 CLI。

- 上游仓库：https://gitee.com/openkylin/libkysdk-base
- 许可证：LGPL-3.0-or-later
- OHOS 适配版本：见 `3.0.1.3/`（`notes.md` 记录适配过程、补丁理由与已知限制）

## 模块

| 模块 | 产物 | 说明 |
|---|---|---|
| config | libkyconf | 配置文件读写（ini/json/xml/gsettings 结构化） |
| conf2 | libkyconf2 + kconf2 / conf2-compile / conf2-sync-{system,session} | 配置中心与跨进程 D-Bus 同步；conf2-compile 把 yaml 编译进 sqlite |
| log | libkylog | 分级日志、文件轮转、mqueue 异步刷新、stdout |
| timer | libkytimer | timerfd + epoll 定时器 |
| utils | libkyutils / libkydatastruct | 容量进制转换 / 跳表容器 |
| gsettings | libkygsetting | GSettings 读写封装 |
| diagnostics | libkydiagnostics | 埋点与诊断上报（openssl 摘要 + dbus） |

## 依赖（OHOS / conan 制品仓）

`glib/2.84.0.1`、`gtk/3.24.43`、`dbus/1.14.10`、`sqlite3/3.53.4`、`openssl/3.5.6.1`、
`yaml-cpp/0.9.0`、`qtbase-sql-dbus/6.11.1`，并用 `expat/2.8.2.1` override 统一 gtk/dbus 链的 expat 版本。

> 本适配**不依赖 libsystemd**：全库唯一用法（`src/log/write.c` 的 `sd_journal_send`）
> 已改为 CMake 能力探测 + POSIX `syslog(3)` 回退（OHOS 无 journald）。

## 使用

```bash
conan install --requires=libkysdk-base/3.0.1.3 -r=ohpcd -pr:h=<ohos-aarch64>
```

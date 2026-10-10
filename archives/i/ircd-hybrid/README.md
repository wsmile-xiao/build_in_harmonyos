# ircd-hybrid

ircd-hybrid 是一款模块化 Internet Relay Chat（IRC）服务器，支持 IRC 客户端接入、可加载模块和 TLS。

## 功能概述

- 提供 IRC 服务端 daemon `ircd`，并通过动态模块提供用户、昵称、消息及 PING/PONG 等协议功能。
- 附带 `mkpasswd` 口令工具。
- 支持通过配置文件设置监听地址、端口、认证、模块和 TLS。

## OHOS 适配

- 当前归档版本针对 HarmonyOS PC aarch64 构建，使用 OHOS Clang 与系统 libc。
- 保留上游 Autotools 构建方式，启用 OpenSSL TLS，并安装 ircd-hybrid 模块。
- HarmonyOS 上需要由运行环境提供配置文件、日志、PID 文件及可写临时目录；设备服务管理和开机启动配置由集成方负责。
- 当前版本的上游发布包没有随包注册的自动化测试；版本级测试报告记录了 Conan 消费者测试和已知验证限制。

## 依赖关系

| 类型 | 依赖 |
|---|---|
| 编译依赖 | `openssl/3.5.8.1` |
| 运行依赖 | HarmonyOS 系统接口；TLS 使用随 Conan 依赖提供的 OpenSSL |

## 参考资料

- 官网与上游项目：https://www.ircd-hybrid.org/
- SourceForge 源码发布页：https://sourceforge.net/projects/ircd-hybrid/

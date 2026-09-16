# nagios

Nagios Core — 经典开源 IT 基础设施监控系统（GPL-2.0-or-later，C 语言，autoconf 构建）。

## 简介

Nagios Core 提供主机/服务监控守护进程、状态统计工具与 CGI Web 界面后端：

- **bin/nagios** — 监控守护进程（调度检查、告警通知、事件处理）
- **bin/nagiostats** — 运行状态统计工具
- **sbin/\*.cgi** — 19 个 CGI 程序（status/tac/extinfo/cmd 等，标准 stdio CGI 协议，无需独立 web 服务器进程即可运行）
- **share/** — Web 界面静态资源（stylesheets/html，供 web 服务器挂载）

## OHOS 适配

- 构建：conan（openssl/3.5.6 + gd/2.3.3.1 依赖链）
- config.guess/config.sub 识别 HarmonyOS（aarch64-unknown-linux-ohos）
- statusmap.cgi 的 rindex() 改 strrchr()（musl libc 无 BSD 遗留符号）
- 上游 init 脚本/systemd unit 不安装（OHOS 无 systemd；daemon 可通过 hdc shell 启动或由集成方封装服务配置）
- CGI 组件保留（纯 stdio 程序，交叉构建/测试均无障碍，statusmap/trends/histogram 需要 gd 图形库）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 4.5.14 | published | 首次适配，上游测试全绿（t/ 478 + t-tap 6702） |

## 上游

- 项目主页: https://www.nagios.org
- 源码: https://github.com/NagiosEnterprises/nagioscore

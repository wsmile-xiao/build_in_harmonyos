# Alpine Wall (awall)

> 可扩展防火墙配置工具：将声明式 JSON 策略翻译为 iptables/ip6tables 规则集。

## 简介

awall 是 Alpine Linux 的防火墙配置框架，提供 zone/service/ipset/custom-chain 等高层
抽象，用户通过 JSON 策略文件描述想要的防火墙行为，awall 将其翻译为完整的
iptables/ip6tables 规则集并支持 `list`/`translate`/`activate`/`diff` 等命令。

纯 Lua 实现（noarch），无 C 编译，安装即文件复制。

## OHOS 适配要点

- 纯 Lua noarch 包：Makefile 仅做文件复制安装，无编译；conan 配方 build 空 + package 复制。
- awall-cli shebang 为 `#!/usr/bin/lua`，OHOS 无此路径，调用须显式 `lua5.5 <pkg>/usr/sbin/awall`。
- 运行时依赖宿主 Lua 模块：lua-alt-getopt / lua-schema / lua-cjson / lua-pc / lua-stringy / lua-posix（未发布制品仓，仅声明 lua/5.5.0）。
- `usr/share/awall/modules` 是符号链接，conan 打包时重建相对链接。
- Lua 5.5 兼容补丁：`optfrag.combinations()` 改用 `select('#', ...)` 计数，修复含 nil 空洞表 `#` 返回 0 导致的 ipsec zone 规则丢失。

## 排除与替代

- `activate`/`fallback`/`flush` 需内核 netfilter 与 root 权限，OHOS 桌面环境不适用；`list`/`translate`/`diff` 纯文本可用。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| lua | 5.5.0 | 唯一 conan 声明依赖（制品仓已发布） |
| lua-alt-getopt / lua-schema / lua-cjson / lua-pc / lua-stringy / lua-posix | - | 宿主 Lua 模块，未发布制品仓，运行时需自行提供 |

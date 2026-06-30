# libndp - IPv6 邻居发现协议库

libndp 是 IPv6 邻居发现协议（Neighbor Discovery Protocol）的 C 语言实现库。

## 功能特性
- 提供 IPv6 NDP 协议的完整封装
- 支持 NDP 消息的发送和接收
- 提供 ndptool 命令行工具

## 版本历史
| 版本 | 状态 | 发布日期 |
|------|------|----------|
| v1.7 | published | 2026-05-29 |

## 项目信息
- 官方网站: http://www.libndp.org/
- 源码仓库: https://github.com/jpirko/libndp
- 作者: Jiri Pirko <jiri@resnulli.us>

## 许可证
LGPL-2.1-or-later

## 编译依赖
- autoconf
- automake
- libtool

## 使用方法
```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libndp v1.7

# 使用库文件
gcc -o myapp myapp.c -lndp

# 使用 ndptool 工具
ndptool --help
```
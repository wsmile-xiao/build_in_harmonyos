# libnatpmp

NAT Port Mapping Protocol (NAT-PMP) 库，用于自动配置NAT网关的端口映射。

## 基本信息

- **主页**: http://miniupnp.free.fr/libnatpmp.html
- **GitHub**: https://github.com/miniupnp/libnatpmp
- **许可证**: BSD-3-Clause
- **语言**: C
- **构建系统**: 自定义Makefile（非autotools）

## 描述

libnatpmp 是一个轻量级的NAT-PMP客户端库，提供以下功能：
- 自动发现NAT网关的公网IP地址
- 请求NAT网关创建TCP/UDP端口映射
- 请求NAT网关删除端口映射
- 获取端口映射请求的超时时间

## API

核心函数：
- `initnatpmp()` — 初始化NAT-PMP会话
- `closenatpmp()` — 关闭NAT-PMP会话
- `sendpublicaddressrequest()` — 请求公网IP地址
- `sendnewportmappingrequest()` — 请求新端口映射
- `readnatpmpresponseorretry()` — 读取NAT-PMP响应
- `getnatpmprequesttimeout()` — 获取请求超时时间
- `strnatpmperr()` — 错误码转字符串

## 已编译版本

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 20230423 | published | 2026-06-04 | Makefile项目，3个补丁 |

## 鸿蒙适配说明

1. **构建系统**: 上游为自定义Makefile，非autotools。需要创建configure wrapper以支持G0验证流程
2. **CC覆盖**: Makefile中CC硬编码为gcc，改为CC?=gcc允许环境变量覆盖
3. **DESTDIR支持**: 上游Makefile不支持DESTDIR，已添加以符合R20铁律
4. **VERSION文件**: 上游发布包缺失VERSION文件，需手动补建
5. **符号链接**: ln -s -f改为rm -f && ln -s以符合R5铁律
6. **平台兼容**: uname -s在HarmonyOS返回"HarmonyOS"，Makefile条件分支兼容

## 依赖

- 无外部库依赖
- 仅需 libc.so（系统C库）
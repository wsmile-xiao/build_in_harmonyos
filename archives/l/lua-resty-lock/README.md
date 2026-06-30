# lua-resty-lock

## 简介
lua-resty-lock 是 OpenResty 的一个 Lua 库，用于实现基于 ngx.shared.DICT 的简单互斥锁。它提供了非阻塞的锁机制，适用于 OpenResty/Nginx 环境下的并发控制。

## 功能特性
- 基于 ngx.shared.DICT 实现
- 非阻塞锁机制
- 支持锁超时和自动释放
- 纯 Lua 实现，无需 C 模块

## 使用场景
- 并发请求控制
- 资源竞争保护
- 分布式锁（配合 shared dict）
- API 调用限制

## 已编译版本
- 0.09 (2026-06-11) - [查看详情](0.09/)

## 安装方法
使用 cmd-pkgs 公共安装脚本：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lua-resty-lock 0.09
```

## 依赖
- Lua 5.4+
- OpenResty/Nginx (ngx.shared.DICT)

## 许可证
BSD 2-Clause License
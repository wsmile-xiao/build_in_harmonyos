# wbox

Wbox 是一个用 ANSI C 编写的小型 HTTP 测试工具（作者 Salvatore 'antirez' Sanfilippo），
用于在命令行里做 HTTP 客户端的基准测试与压力测试，也可以把一个目录直接当作免配置的
HTTP 服务器对外提供文件。

## 功能概述

- **客户端模式**：对指定 URL 连续发起 HTTP 请求，逐次打印响应码、接收字节数与耗时，
  退出时给出 min/avg/max 耗时统计
  - `compr` 校验 gzip/deflate 压缩、`timesplit` 分段耗时、`showhdr`/`dump` 显示报文、
    `head`/`http10`/`close`/`wait`/`host`/`referer`/`cookie` 等请求构造选项
- **并发客户端**：`clients <n>` 通过 `fork()` 派发并发客户端
- **服务器模式**：`wbox servermode webroot <path> [serverport <port>]` —— 免配置
  静态文件服务器（默认端口 8081，`maxclients` 限制并发），带目录索引页
- **退出码契约**：`0` 成功 / `1` 参数错误 / `2` DNS 解析失败 / `3` 连接失败 /
  `4` I/O 错误 / `5` 提前 EOF

## OHOS 适配

- 构建系统为**纯 Makefile**（无 `configure`/无生成文件），OHOS clang 直接编译，
  **零补丁**，编译期仅出现一条上游自身的 `-Wunused-but-set-variable` 告警
  （`wbox.c:1186`，与平台无关，未修）。
- 依赖只有 libc/POSIX（socket、fork、signal、getaddrinfo），**无第三方依赖**，
  因此配方 `requirements()` 为空。
- 实测 OHOS 平台行为正常：回环 socket、`fork()` 每连接子进程、SIGINT 统计输出、
  退出码契约（连接被拒 → 3）均与 Linux 一致。
- `test_package/test_wbox_ohos.sh` 为鸿蒙特有测试：ELF64/AArch64/PIE/musl/NX 校验，
  以及 servermode + client 端到端（HTTP 200 + payload 比对、404、`clients 2` 并发、
  退出码 3）。

## 依赖关系

- 编译依赖：无（仅工具链 libc）
- 运行依赖：无（静态语义上的单文件 CLI，动态链接 OHOS musl libc）

## 参考资料

- 上游官网/文档：<https://www.hping.org/wbox/>
- 源码包：`wbox-5.tar.gz`（sha256 `1589d85e83c8ee78383a491d89e768ab9aab9f433c5f5e035cfb5eed17efaa19`）
- 许可证：New BSD（3-Clause）

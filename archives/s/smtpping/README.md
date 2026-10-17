# smtpping - SMTP 服务器延迟/吞吐测量工具

## 简介
smtpping（Halon Security）是一个小型 C++ 命令行工具，用于测量 SMTP 服务器的
延迟、延迟抖动与吞吐量：每次探测完成一轮完整 SMTP 事务
（banner → HELO → MAIL FROM → RCPT TO → DATA → QUIT），逐阶段统计
min/avg/max 往返时间，类似 SMTP 版 ping。支持 MX/A/AAAA 自动解析、
多进程并发（`-P`）、CHUNKING（BDAT）与速率统计（`-r`）。

## 功能
- 单机 SMTP 延迟探测：`smtpping test@example.com`（自动查 MX，回退 A/AAAA）
- 指定服务器：`smtpping test@example.com @10.2.0.31`
- 吞吐/并发：`smtpping -P50 -r -w0 test@example.com @10.2.0.31`
- 报文大小（`-s`）、自定义 HELO/发件人（`-H`/`-S`）、RFC822 文件发送（`-f`）
- 输出各阶段（connect/banner/helo/mailfrom/rcptto/data/datasent/quit）统计

## OHOS 适配
- 构建系统：CMake（上游 `CMakeLists.txt`，C++ + POSIX socket，无第三方依赖）
- **2 个补丁（OHOS 解析器 API 兼容）**：
  - `0001-resolver.cpp.patch`：`res_ninit/res_nquery/res_nclose` →
    `res_query()` + 全局 `h_errno`（OHOS 只有经典非重入 API）
  - `0002-resolver.hpp.patch`：删除 `struct __res_state` 成员并补 `<netdb.h>`
- 配方注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游声明
  `cmake_minimum_required(VERSION 2.8)`，CMake ≥4.0 已移除 <3.5 兼容；
  上游 v1.1.5 用同款修法，故源码零改动）
- 交付产物：`bin/smtpping` + `man/man1/smtpping.1` + `licenses/LICENSE`
- 上游无自动化测试套件（无 tests/ 目录、CMakeLists 无 `enable_testing()`/
  `add_test()`），适配后补全消费者 E2E（`test_package/`：mock SMTP 服务器
  回环全事务 + CLI 契约 + 负路径，15 条断言）

## 依赖关系
```
smtpping/1.1.4 (cmake, C++)
└─ 无第三方依赖（仅 POSIX socket / getopt / semaphore + libc++）
```

## 参考资料
- 上游仓库：https://github.com/halon/smtpping（原 halonsecurity/smtpping）
- 源码包：https://github.com/halon/smtpping/archive/refs/tags/v1.1.4.tar.gz
- 适配记录：`1.1.4/notes.md`
- 相关知识：E516（OHOS libc 解析器状态差异同族）

## 许可证
GPL-2.0-or-later（见上游 LICENSE）

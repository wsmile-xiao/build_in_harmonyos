# libasyncns

## 软件简介

libasyncns 是一个轻量级的异步 DNS 解析库，提供非阻塞的域名查询功能。

**官方网站**: http://0pointer.de/lennart/projects/libasyncns/

**核心特性**:
- 异步 DNS 解析（A/AAAA 记录）
- 支持并发域名查询
- 简洁的 C API
- 基于 fork + pipe 实现异步

## 鸿蒙平台适配

**当前版本**: 0.8
**适配状态**: ✅ 完全可用
**测试评级**: ⭐⭐⭐⭐⭐ (5/5)

### 功能验证

| 功能项 | 状态 | 说明 |
|-------|------|------|
| DNS 解析 | ✅ | IPv4 地址解析成功 |
| 并发查询 | ✅ | 多域名同时解析 |
| 异步机制 | ✅ | asyncns_wait 正常工作 |
| 静态库 | ✅ | 可正常链接 |
| 动态库 | ✅ | 运行时加载成功 |

### 应用场景

- 需要异步 DNS 解析的应用程序
- 网络服务后台查询域名
- 批量域名解析工具
- 非阻塞网络客户端

### 使用方法

```c
#include <asyncns.h>

// 初始化
asyncns_t *asyncns = asyncns_new(10);

// 发起查询
asyncns_query_t *q = asyncns_getaddrinfo(asyncns, "example.com", NULL, &hints);

// 等待结果
asyncns_wait(asyncns, -1);

// 获取结果
struct addrinfo *ai;
int ret = asyncns_getaddrinfo_done(asyncns, q, &ai);

// 清理
freeaddrinfo(ai);
asyncns_free(asyncns);
```

### 编译链接

```bash
# 静态库
clang app.c ~/usr/local/lib/libasyncns.a -I~/usr/local/include -pthread

# 动态库
clang app.c -lasyncns -I~/usr/local/include -L~/usr/local/lib \
  -Wl,-rpath,~/usr/local/lib -pthread
```

### 已知限制

1. IPv6 DNS 解析需网络环境支持
2. 并发查询建议不超过 20 个
3. 需要网络权限才能解析域名

## 版本历史

- **0.8** (2009-10-16): 当前适配版本
  - 平台识别补丁 (config.guess/config.sub)
  - 源码适配补丁 (asyncns.c/asyncns-test.c)

## 依赖关系

**编译依赖**: 无
**运行依赖**:
- pthread (线程库)
- 网络库（系统提供）

## 文档

- 详细测试报告: `reports/test-report.md`
- 编译笔记: `notes.md`
- 补丁说明: `patches/` 目录

---
**维护者**: OpenHarmony 三方库适配团队
**更新日期**: 2026-05-30
# tinyproxy 1.11.3 — HarmonyOS 预编译包

> 轻量级 HTTP/HTTPS 代理服务器，适用于小型网络环境
> 本包为 HarmonyOS (aarch64) 平台预编译版本

---

## 📦 软件简介

Tinyproxy 是一个小巧高效的 HTTP/SSL 代理守护进程，采用 GPL 许可证发布。
它特别适用于小型网络场景——大型代理服务器可能过于消耗资源或存在安全风险。

Tinyproxy 的核心特性是**缓冲连接**机制：它先高速接收服务器的响应数据，
再以客户端可接受的最大速率转发，有效缓解网络迟缓问题。
如果你需要为小型网络共享互联网连接，且仅允许 HTTP 请求通过，
Tinyproxy 是网络管理员的优秀工具。

**上游项目**: [https://tinyproxy.github.io/](https://tinyproxy.github.io/)

---

## 📋 编译信息

| 项目 | 值 |
|------|-----|
| 版本 | 1.11.3 |
| 平台 | HarmonyOS (aarch64-unknown-linux-ohos) |
| 内核 | HongMeng Kernel |
| 编译器 | clang / clang++ (系统自带) |
| 构建系统 | autotools (configure + make) |
| 许可证 | GNU GPL |
| 二进制大小 | 113,088 字节 (strip后) |
| 动态依赖 | libc.so (仅1个，musl libc) |
| 编译日期 | 2026-05-26 |

---

## ✅ 已编译功能

| 功能 | 说明 |
|------|------|
| XTinyproxy Header | Via 头部注入，标记代理经过 |
| Filtering | URL/域名过滤，可配置黑白名单 |
| Transparent Proxy | 透明代理，配合防火墙规则自动代理 |
| Reverse Proxy | 反向代理，映射外部请求到内部服务 |
| Upstream Proxy | 上游代理级联，支持多级代理链 |

---

## 🔧 补丁说明

本预编译包在源码基础上应用了以下补丁，均为 HarmonyOS 平台适配所需：

1. **0001-config.guess-harmonyos-support.patch**
   - 添加 HarmonyOS 系统识别支持（两处修改）
   - §2.1: 在初始 case 中加入 `HarmonyOS` 识别
   - §2.2: 在主 case 块中加入 `*:HarmonyOS:*:*)` 输出正确的 triplet

2. **0002-config.sub-ohos-vendor-alias.patch**
   - config.sub 已内置 `ohos*` vendor 别名（Savannah 上游版本）
   - 此补丁仅确保使用最新版本

3. **0003-configure.ac-timestamp.patch**
   - 设置 configure.ac 时间戳，避免 aclocal-1.16 重建触发
   - HMDFS 沙箱环境无法运行 aclocal，需绕过

4. **0004-man-pages.patch**
   - man 手册页时间戳修正

> **核心经验**: HarmonyOS HMDFS 文件系统上 mktemp 创建的临时目录不可写，
> 需使用固定路径替代。详见知识图谱 E105/E106。

---

## 🚀 安装与使用

### 安装

```bash
# 解压预编译包到目标路径
tar xzf tinyproxy-1.11.3-ohos-aarch64.tar.gz -C /path/to/install

# 默认安装路径
# /storage/Users/currentUser/usr/local/bin/tinyproxy
# /storage/Users/currentUser/usr/local/etc/tinyproxy/tinyproxy.conf
# /storage/Users/currentUser/usr/local/share/tinyproxy/
```

### 启动

```bash
# 使用默认配置启动（守护进程模式）
tinyproxy

# 使用自定义配置启动
tinyproxy -c /path/to/tinyproxy.conf

# 前台运行（调试模式）
tinyproxy -d

# 查看版本
tinyproxy -v
```

### 配置示例

```bash
# 最小化配置示例
Port 8888            # 代理监听端口
Listen 127.0.0.1     # 仅监听本地
Allow 127.0.0.1      # 仅允许本地访问
ConnectPort 443      # 允许 CONNECT 隧道端口
ConnectPort 80       # 允许 HTTP CONNECT
ViaProxy "tinyproxy" # Via 头部标识
```

### 客户端使用

```bash
# HTTP 代理
curl -x http://127.0.0.1:8888 http://example.com

# HTTPS 代理（CONNECT 隧道）
curl -x http://127.0.0.1:8888 https://example.com

# 环境变量方式
export http_proxy=http://127.0.0.1:8888
export https_proxy=http://127.0.0.1:8888
```

---

## ✅ 测试验证

全部 **13 项功能测试通过**，包括：

- HTTP 代理转发 (状态码 200)
- HTTPS CONNECT 隧道 (状态码 200)
- Via 头部注入 (符合 RFC 7230)
- 并发连接处理 (3/3 成功)
- ACL 访问控制 (生效)
- 错误处理与页面模板
- 优雅停机 (SIGTERM 正常退出)
- 日志系统 (完整记录)

详见 `reports/test-report.md`

---

## 📂 包内容

```
tinyproxy-1.11.3-ohos-aarch64/
├── bin/tinyproxy                    # 主程序 (113KB)
├── etc/tinyproxy/tinyproxy.conf     # 配置文件 (329行)
├── share/tinyproxy/
│   ├── debug.html                   # 调试错误页面
│   ├── default.html                 # 默认错误页面
│   └── stats.html                   # 统计页面模板
└── share/man/
    ├── man5/tinyproxy.conf.5        # 配置文件手册
    └── man8/tinyproxy.8             # 程序手册
```

---

## ⚠️ 已知限制

1. **`--version` 不支持**: 使用 `-v` 获取版本号，`--version` 返回错误
2. **非 root 运行**: HarmonyOS 沙箱环境无法 root 运行，UID/GID 切换功能未验证
3. **透明代理**: 需要 iptables/netfilter 支持，沙箱环境无法验证
4. **过滤功能**: 需编写过滤规则文件后测试，本次仅验证编译特性启用

---

## 📁 归档目录结构

```
archives/t/tinyproxy/1.11.3/
├── manifest.yaml          # 版本元数据清单
├── notes.md               # 编译过程笔记
├── README.md              # 本文件（中文说明）
├── .knowledge-done        # 知识整理完成标记
├── .verify-passed         # 验证门禁通过标记
├── patches/               # 平台适配补丁
├── packaging/             # 预编译包
│   ├── tinyproxy-1.11.3-ohos-aarch64.tar.gz        # 生产包
│   └── tinyproxy-1.11.3-ohos-aarch64-debug.tar.gz  # 调试包
└── reports/
    ├── quality-report.md  # 编译质量报告
    └── test-report.md     # 功能测试报告
```

---

## 📄 许可证

Tinyproxy 采用 **GNU General Public License** 发布。
详见源码包中的 `COPYING` 文件。

---

*本文档由 OpenDesk 编译智能体自动生成*
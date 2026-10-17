# nutcracker (twemproxy)

轻量级高性能 Redis/Memcached 协议代理（daemon 工具），Twitter 开源，C 语言实现。

## 简介

twemproxy（nutcracker）是一个快速、轻量的 TCP 代理，支持 Redis 与 Memcached
协议，通过 YAML 配置文件定义服务器池与哈希/分发策略（fnv1a_64/ketama 等），
降低客户端直连大量后端实例的连接数，并提供自动摘除故障节点能力。

## 版本信息

### 0.5.0（当前版本）
- **编译日期**: 2026-09-12
- **编译器**: clang 15.0.4（target aarch64-unknown-linux-ohos）
- **平台**: HarmonyOS (OpenHarmony PC)
- **架构**: aarch64
- **构建系统**: GNU Autotools（含 vendored libyaml 0.2.5 递归构建）
- **异步事件后端**: epoll（HAVE_EPOLL）
- **上游测试**: make check 967/967（test_all）+ vendored libyaml 2/2

## 功能特性

- Redis / Memcached 协议代理
- 一致性哈希（ketama）、取模等分发策略
- YAML 配置（`-c`），`-t` 配置预校验
- 故障节点自动摘除（auto_eject_hosts）
- 多进程 / 统计端口（`-s`）

## 使用方法

```bash
# 查看版本
nutcracker -V

# 校验配置文件
nutcracker -t -c /path/to/nutcracker.yml

# 前台运行
nutcracker -c /path/to/nutcracker.yml

# 以 daemon 方式运行
nutcracker -c /path/to/nutcracker.yml -d -p /path/to/nutcracker.pid
```

最小配置示例（`nutcracker.yml`）：

```yaml
alpha:
  listen: 127.0.0.1:22121
  hash: fnv1a_64
  distribution: ketama
  auto_eject_hosts: true
  redis: true
  server_retry_timeout: 2000
  server_failure_limit: 1
  servers:
   - 127.0.0.1:6379:1
```

## 安装

使用 cmd-pkgs 公共安装脚本安装预编译包：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- nutcracker 0.5.0
```

## 已知问题

1. **vendored libyaml**：上游 0.5.0 递归构建内置 libyaml 0.2.5（AC_CONFIG_SUBDIRS），
   不消费系统/制品仓 libyaml；配方中声明 libyaml/0.2.5 依赖保证清单完整。
2. **HMDFS 限制**：脚本类产物需 `bash script` 方式执行（noexec/权限归一化）。
3. **平台**：仅验证 ohos-aarch64（profile ohos-aarch64）。

## 参考

- 上游仓库: https://github.com/twitter/twemproxy
- 官方文档: https://github.com/twitter/twemproxy/blob/master/README.md

---
*最后更新: 2026-09-12*
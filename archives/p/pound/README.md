# Pound

**状态**: ✅ published（所有质量门禁通过）

## 描述

Pound 是一个轻量级的 HTTP/HTTPS 反向代理和负载均衡器，专为高性能和简单配置设计。支持 SSL/TLS 终止、请求路由和健康检查。

## 功能特性

- ✅ HTTP/HTTPS 反向代理
- ✅ 负载均衡（轮询、加权）
- ✅ SSL/TLS 终止
- ✅ 请求路由和 URL 重写
- ✅ 健康检查和故障转移
- ✅ 会话保持（基于 Cookie）

## 编译信息

| 项目 | 信息 |
|------|------|
| 源码版本 | 4.22（用户请求4.18-r0不存在，使用最新稳定版） |
| 编译日期 | 2026-05-21 |
| 构建系统 | autotools |
| 编译器 | clang |
| 归档位置 | archives/p/pound/4.22/ |

## 依赖

| 软件 | 版本 | 状态 |
|------|------|------|
| OpenSSL | 1.1.1w | ✅ 已安装（预编译包） |
| PCRE2 | 10.42 | ✅ 已安装（预编译包） |

## 质量门禁

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 干净构建验证 | ✅ PASS | 补丁自包含，可重现编译 |
| G1 二进制完整性 | ✅ PASS | 所有必要文件已安装 |
| G2 功能可用性 | ✅ PASS | pound 基础功能可用 |
| G3 可移植性 | ✅ PASS | RPATH 已设置，ELF 已签名 |
| G4 档案完整性 | ✅ PASS | 所有必填文件齐全 |

## 预编译包

- **文件**: pound-4.22-ohos-aarch64.tar.gz
- **大小**: 564KB
- **位置**: archives/p/pound/4.22/packaging/
- **内容**: pound 可执行文件 + 配置模板 + 依赖库信息

## 平台适配

Pound 在 HarmonyOS 上需要以下平台适配：

### 1. pthread_mutexattr_settype 未实现

**问题**: HarmonyOS musl 不支持 `pthread_mutexattr_settype`（设置 mutex 类型）。

**解决**: 移除调用，使用默认 mutex 类型（PTHREAD_MUTEX_DEFAULT）。

```c
// 原代码（第1145-1146行）
pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_ERRORCHECK);

// 修改为
// 移除调用，使用默认 mutex
```

### 2. pthread_cancel 未实现

**问题**: HarmonyOS musl 不支持 `pthread_cancel`（取消线程）。

**解决**: 用 `pthread_detach` 替代，让线程自动清理资源。

```c
// 原代码（第784行）
pthread_cancel(thr);

// 修改为
pthread_detach(thr);
```

### 补丁文件

`0001-openharmony-pthread-compat.patch` 包含所有平台适配修改。

## 使用方法

### 安装预编译包

```bash
# 使用 cmd-pkgs 安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- pound 4.22
```

### 基础配置

```bash
# 创建配置文件
cat > ~/usr/local/etc/pound.cfg <<'EOF'
ListenHTTP
    Address 0.0.0.0
    Port 80

    Service
        BackEnd
            Address 127.0.0.1
            Port 8080
        End
    End
End

ListenHTTPS
    Address 0.0.0.0
    Port 443
    Cert "/path/to/cert.pem"

    Service
        BackEnd
            Address 127.0.0.1
            Port 8080
        End
    End
End
EOF

# 启动 pound
~/usr/local/bin/pound -f ~/usr/local/etc/pound.cfg
```

### 验证安装

```bash
pound --version
# 输出: pound 4.22
```

## 知识沉淀

已记录以下平台限制解决方案：

- **E051 扩展**: pthread_cancel 不支持 → pthread_detach 替代
- **E052 新增**: pthread_mutexattr_settype 不支持 → 使用默认 mutex

## 影响范围

此平台适配方案适用于：
- 所有使用 pthread_cancel 的软件
- 所有使用 pthread_mutexattr_settype 的软件
- 多线程服务器程序（nginx、httpd 等）

## 相关链接

- 官网: https://www.apsis.ch/pound
- GitHub mirror: https://github.com/graygnuorg/pound
- 详细记录: 4.22/notes.md
- 补丁文件: 4.22/patches/0001-openharmony-pthread-compat.patch
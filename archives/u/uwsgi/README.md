# uWSGI

## 简介

uWSGI是一个快速、自我修复、开发者友好的WSGI服务器，主要用于部署Python Web应用。它是一个完整的Web应用服务器，支持多种协议和语言。

## 特性

- **多语言支持**：Python、Ruby、Perl、Lua等
- **多种协议**：WSGI、HTTP、FastCGI、SCGI、WebSocket等
- **高性能**：异步I/O、多进程、多线程模式
- **插件系统**：可扩展的插件架构
- **进程管理**：Master-Worker架构，自动重启

## HarmonyOS适配说明

### 当前编译状态

- **版本**: 2.0.24
- **配置**: nolang（核心功能，无语言插件）
- **状态**: published ✅

### 功能限制

**nolang配置限制**：
- ❌ 不支持Python应用模块（无法运行Python WSGI应用）
- ✅ 核心功能完整可用（HTTP服务、socket、插件等）
- ✅ 18个核心插件可用（nagios, http, syslog, router等）

### 关键适配点

1. **系统识别**：uwsgiconfig.py需要添加HarmonyOS识别
   ```python
   if uwsgi_os in ('Linux', 'HarmonyOS'):
   ```

2. **Python库路径**：Python sysconfig返回错误路径，需使用nolang配置

3. **线程取消**：PTHREAD_CANCEL宏已定义，重定义触发警告但不阻塞

### 依赖库

- libxml2/2.12.5 - XML配置支持
- zlib/1.3.1 - 压缩支持
- gettext/0.22 - libintl（运行时依赖）

## 使用方法

### 安装

通过cmd-pkgs安装预编译包：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- uwsgi 2.0.24
```

或手动安装：
```bash
tar xzf uwsgi-2.0.24-ohos-aarch64.tar.gz -C ~/usr/local
```

### 基本使用

```bash
# 版本检查
uwsgi --version

# 查看插件列表
uwsgi --plugins-list

# 启动HTTP服务器
uwsgi --http :9090 --master --workers 2

# 查看配置
uwsgi --show-config
```

## 已编译版本

| 版本 | 状态 | 配置 | 说明 |
|------|------|------|------|
| 2.0.24 | published | nolang | 核心功能，无Python插件 |

## 注意事项

1. **如需Python支持**：需要重新编译，解决sysconfig路径问题
2. **依赖库路径**：确保LD_LIBRARY_PATH包含依赖库路径
3. **pcre支持**：当前版本缺少pcre，无内部路由功能

## 参考资料

- 官网: https://uwsgi-docs.readthedocs.io/en/latest/
- 源码: https://github.com/unbit/uwsgi
- HarmonyOS编译归档: archives/u/uwsgi/2.0.24/
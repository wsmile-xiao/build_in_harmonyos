# netcat

GNU netcat - 网络瑞士军刀

## 软件简介

GNU netcat 是一个功能强大的网络工具，被称为"网络瑞士军刀"。它可以：
- 读写 TCP/UDP 网络连接
- 端口扫描和数据传输
- 创建简单的网络服务
- 测试网络连通性

## 版本历史

| 版本 | 编译日期 | 状态 | 说明 |
|------|---------|------|------|
| 0.7.1 | 2026-05-21 | published | GNU netcat 传统版本 |

## 使用方式

安装预编译包：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- netcat 0.7.1
```

验证安装：
```bash
netcat --version
# 输出: netcat (The GNU Netcat) 0.7.1
```

基本使用：
```bash
# 客户端模式（连接远程主机）
nc hostname port

# 服务端模式（监听端口）
nc -l -p port

# 端口扫描
nc -z hostname port1-port2
```

## 功能特性

- TCP/UDP 连接支持
- 端口扫描
- 数据传输
- 调试模式
- 超时设置

## 平台兼容性

- HarmonyOS aarch64
- 动态链接 musl
- 无需额外依赖库

## 相关命令

- `nc`: netcat 的软链接（传统名称）
- `ncat`: nmap 的增强版 netcat（需要单独安装）

## 参考资料

- GNU netcat 官网: http://netcat.sourceforge.net/
- OpenBSD netcat: https://www.openbsd.org/
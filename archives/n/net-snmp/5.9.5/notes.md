# net-snmp 5.9.5 适配笔记

## 编译环境
- 构建系统: Autotools
- 编译日期: 2026-05-20
- 编译器: clang 15.0.4
- 状态: built

## 依赖
- openssl/1.1.1w

## 配置选项
```bash
./configure --prefix=$HOME/usr/local \
            --with-openssl=$HOME/usr/local \
            --with-defaults \
            --disable-embedded-perl \
            --without-ethtool
```

## 遇到的问题

### HarmonyOS 头文件冲突
- 问题：linux/socket.h 与 sys/socket.h 的 sockaddr_storage 重定义
- 解决：定义 __kernel_sa_family_t 并阻止 _UAPI_LINUX_SOCKET_H 宏

## 知识提取
- HarmonyOS SDK 头文件需要特殊处理以避免重定义冲突
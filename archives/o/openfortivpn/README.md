# openfortivpn

openfortivpn是一个开源的Fortinet VPN客户端，用于连接Fortinet SSL VPN。

## 描述

openfortivpn是一个替代Fortinet官方FortiClient SSL VPN客户端的开源实现。它通过PPP over SSL隧道连接到Fortinet VPN服务器，无需使用Fortinet专有的客户端软件。

## 鸿蒙适配说明

在鸿蒙系统上编译openfortivpn需要解决以下问题：

1. **E051: pthread_cancel不可用**
   - 鸿蒙内核不支持pthread_cancel syscall
   - 需要使用#ifdef __OHOS__守卫跳过pthread_cancel调用
   - 线程取消功能被禁用，使用pthread_join等待线程自然结束

2. **E011: HMDFS umask限制**
   - HMDFS文件系统的umask 077会导致临时目录不可写
   - 需要修改configure脚本中的umask 077为umask 022

3. **TMPDIR workaround**
   - 由于HMDFS权限限制，建议在$TMPDIR中构建
   - 避免在HMDFS挂载的home目录中执行configure

## 依赖

- openssl >= 1.0.2
- pkg-config
- automake >= 1.16
- autoconf >= 2.72

## 版本列表

| 版本 | 状态 | 发布日期 | 补丁数 |
|------|------|---------|--------|
| 1.24.1 | published | 2026-05-28 | 2 |

## 参考

- 官方网站: https://github.com/adrienverge/openfortivpn
- 知识条目: E051, E011
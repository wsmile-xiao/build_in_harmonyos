# BOSixNet (bosixnet)

## 简介

BOSixNet 让动态 DNS 主机名与 hosts 记录在局域网上保持一致。它由两半组成：
`bosixnet-daemon` 客户端守护进程（POSIX shell 脚本）与 `bosixnet-webui`
C++ FastCGI Web 界面（基于 FastCGI Developer Kit）。

## OHOS 适配

- 版本: `bosixnet/2.0`（上游 release tag `v2.0`）
- 构建系统: CMake；关闭 systemd / SysVinit 集成（无传统 init 的 HarmonyOS PC）
- fcgi 依赖: 远端 ohpcd 无 fcgi/2.4.7 配方，conanfile 直接从 cmd-pkgs 获取
  OHOS aarch64 预编译包并按 sha256 校验
- 安装路径: 上游硬编码 `/etc/bosixnet/` → `${CMAKE_INSTALL_PREFIX}/etc/bosixnet/`
- CMake 政策: `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游声明 `cmake_minimum_required(2.8)`，
  CMake >=4 已移除 <3.5 兼容）

## 依赖

- fcgi 2.4.7（cmd-pkgs 预编译包）

## 功能验证

```bash
bosixnet_webui -v   # 打印版本并退出（上游输出 Version: 1.7, 上游硬编码）
bosixnet_daemon     # 客户端守护进程脚本
```

## 参考

- 官网: https://github.com/tehnick/bosixnet
- 源码: https://github.com/tehnick/bosixnet/archive/refs/tags/v2.0.tar.gz
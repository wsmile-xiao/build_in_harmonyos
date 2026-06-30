# libnetfilter_cttimeout — OpenHarmony 预编译包

## 软件简介
libnetfilter_cttimeout 是 libnetfilter 库的一部分，用于管理连接跟踪超时设置。
它是 Linux netfilter/iptables 系统的辅助库，用于配置网络连接的超时参数。

## 快速安装

```bash
# 下载预编译包后解压安装
tar xzf libnetfilter_cttimeout-1.0.0-ohos-aarch64.tar.gz
cd libnetfilter_cttimeout-1.0.0-ohos-aarch64
sh install-libnetfilter_cttimeout-1.0.0.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 | 构建系统 |
|------|------|--------|----------|
| 1.0.0 | ✅ built | 0 | autotools |

## 库文件

安装后可用的库：
- `libnetfilter_cttimeout.so` - 主库
- 相关头文件

## 使用说明

该库用于配合 libnetfilter_conntrack 使用，主要功能：
- 设置连接跟踪超时参数
- 自定义网络连接超时策略

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- 需要 libmnl 库支持
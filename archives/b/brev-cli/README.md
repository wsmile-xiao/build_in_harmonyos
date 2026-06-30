# Brev CLI

## 简介
Brev CLI 是一个云开发环境连接工具，用于管理和访问远程开发环境。

## 编译信息
- 最新版本：0.6.326
- 构建系统：Go + Makefile
- 支持平台：Linux (arm64)

## 功能特点
- 云开发环境管理
- SSH 连接配置
- 工作空间管理
- GPU 硬件探测（可选，需要 NVML）

## 使用说明
```bash
# 解压预编译包
tar xzf brev-cli-0.6.326-ohos-aarch64.tar.gz -C ~/usr/local

# 运行
~/usr/local/bin/brev version
```

## 注意事项
- 鸿蒙系统需要 ELF 签名才能执行二进制
- NVML GPU 探测功能在纯 Go 编译中被禁用

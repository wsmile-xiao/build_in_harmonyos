# ipatool

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/majd/ipatool/blob/main/LICENSE)

## 描述

`ipatool` is a command line tool that allows you to search for iOS apps on the App Store and download a copy of the app package, known as an _ipa_ file.

## 编译版本

- **2.3.0** - 2026-06-08 - Go modules (built)

## 安装

```bash
# 从预编译包安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ipatool 2.3.0
```

## 功能

- **auth**: Authenticate with the App Store
- **download**: Download iOS app packages from the App Store
- **search**: Search for iOS apps on the App Store
- **purchase**: Obtain a license for an app
- **list-versions**: List available versions of an app
- **get-version-metadata**: Get metadata for a specific app version

## 用法示例

```bash
# 认证
ipatool auth login --email your@email.com

# 搜索应用
ipatool search "App Name"

# 下载应用
ipatool download --appid 123456789

# 查看版本
ipatool --version
```

## 运行依赖

- Apple ID (需要 App Store 访问权限)

## 编译依赖

- Go >= 1.23.0

## 官方资源

- **GitHub**: https://github.com/majd/ipatool
- **License**: MIT
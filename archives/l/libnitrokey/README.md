# libnitrokey

## 简介

libnitrokey 是 Nitrokey USB 安全令牌的通信库，提供对 Nitrokey 设备的底层访问接口。

## 功能概述

- 支持多种 Nitrokey 设备型号
- 提供密码管理、OTP 生成、加密存储等功能

## OHOS 适配

### 适配要点
- CMakeLists.txt 需修改 cmake_minimum_required(VERSION 3.1) → 3.5
- 内嵌 hidapi 子模块，无外部 HID 库依赖

## 依赖

无外部依赖，内嵌 hidapi 子模块。

## 参考

- GitHub: https://github.com/Nitrokey/libnitrokey

# Pixiewps — OpenHarmony 编译档案

## 软件简介
Pixiewps 是一款用 C 语言编写的离线 WPS 暴力破解工具，利用部分软件实现中伪随机数生成器（PRNG）熵值低或不存在的问题，通过所谓的 "pixie-dust attack" 破解 WPS PIN。仅用于教育目的。

## 功能概述
- 离线 WPS PIN 暴力破解（pixie-dust attack）
- 多线程并行计算（pthread）
- 支持 RTL819x、Ecos Simple 等多种 PRNG 模式
- 可选 OpenSSL 加速（本次适配未启用）
- 从被动捕获（M1-M7）恢复 WPA-PSK（--mode 3）

## OHOS 适配要点
- 纯 Makefile 项目，无 configure 步骤，`make` 直接构建
- 加密库（libtomcrypt + tomsfastmath）已内置源码树，无外部 Conan 依赖
- R33: CC 通过 make 命令行变量传递（从 Conan conf 获取），不依赖 shell 环境变量
- 仅需系统 pthread（musl libc 内置）
- R38/E082: 构建产物为可执行二进制，package() 中调用 binary-sign-tool 进行 ELF 签名
- 命令行工具，需声明 commands.json（R38）

## 依赖关系
- 系统库: pthread（musl libc 内置）
- 加密库: libtomcrypt + tomsfastmath（源码内置，非外部依赖）

## 参考资料
- [Pixiewps GitHub](https://github.com/wiire-a/pixiewps)
- [Pixiewps Wiki](https://github.com/wiire-a/pixiewps/wiki)

## conan

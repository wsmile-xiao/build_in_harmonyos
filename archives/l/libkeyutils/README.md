# libkeyutils

## 简介
Linux 内核密钥管理工具库（keyutils），提供 keyctl 系统调用的用户空间接口。

## OHOS 适配
- 构建系统：plain Makefile（无 configure/autotools）
- `-Drindex=strrchr`：musl libc 不声明 BSD 的 rindex() 别名，映射到标准 strrchr()
- 禁用 `-Werror`（clang/musl 产生新警告）
- 编译器路径从 Conan conf 获取 (R33)

## 依赖
- 无外部依赖

## 版本 1.6.3
- 状态：built

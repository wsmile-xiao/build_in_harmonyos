# GNU Make

GNU Make 是一个自动化构建工具，用于控制程序编译和构建过程。

## 版本

- **4.4.1** (2026-05-18) - 编译成功 ✅

## 描述

Make 是一个工具，用于从源代码自动生成可执行程序和库。它通过读取 Makefile 文件来确定哪些部分程序需要重新编译，并发出命令来重新编译它们。

## 官方网站

https://www.gnu.org/software/make/

## 许可证

GPL-3.0+

## 分类

构建工具 (build-tools)

## 编译说明

make 是基础构建工具，在鸿蒙系统上编译需要：
1. 修改 config.guess 支持 HarmonyOS 系统识别
2. 修改 config.sub 支持 linux-ohos kernel-os 组合
3. 使用 ld.bfd 替代 lld 链接器
4. 创建 clang wrapper 自动签名 ELF 文件
5. 解决 mktemp 临时目录权限问题
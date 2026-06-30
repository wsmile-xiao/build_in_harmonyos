# b43-fwcutter

## 软件描述
b43-fwcutter 是一个从 Broadcom 43xx 驱动文件中提取固件的工具。

## 版本
- 019 (2026-06-30 编译，published)

## 构建系统
- 简单 Makefile（非 autotools，无 configure 脚本）

## 依赖
- 无第三方依赖（仅依赖标准 C 库）

## 编译参数
- `CC=clang`
- `CFLAGS=-fPIC -O2 -std=c99 -Wall -pedantic -D_BSD_SOURCE -DFWCUTTER_VERSION_=019`
- `LDFLAGS=-static`（R26: 终端工具静态链接）

## 补丁
- `0001-Makefile.patch`: 移除 install 目标 root 权限标志，添加 DESTDIR 支持

## 验证
- `b43-fwcutter --version` → "b43-fwcutter version 019"
- 静态链接：无动态段（完全静态）
- 安全特性：NX + RELRO
- conan-verify 8 道门禁全部通过

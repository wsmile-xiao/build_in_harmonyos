# tag

## 简介

tag 是一个向 stdin 数据流添加前缀标记的小型 C 命令行工具：把消息、日期（%d）、主机名（%h）或行号（%l）作为每行的前缀 stamp 输出，适合给日志流打标。

## 功能概述

- 消息前缀：`echo world | tag hello` → `hello world`
- 日期戳：`%d` 展开为 `YYYY-MM-DD HH:MM:SS`
- 主机名：`%h` 展开为本机主机名
- 行号：`%l` 按行递增（%05d）
- 内存占用极小，适合长时间运行的进程

## OHOS 适配

- 仅产出 `bin/tag` 可执行文件，无库产物（package_type=application）。
- 上游 `make install` 依赖 `install` 工具，配方改为 Conan copy() 直接搬运构建产物。
- 上游无测试套件，test_package 对打包二进制做真实 stdin 打标功能验证。

## 依赖关系

- 编译依赖：无（仅 libc，Makefile 直接 $(CC) 编译）
- 运行依赖：无

## 参考资料

- 上游仓库：https://github.com/mafintosh/tag
- 版本：0.1（上游 git tag 0.1.0）

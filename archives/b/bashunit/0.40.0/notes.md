# bashunit 0.40.0 适配笔记

## 编译环境

- 构建系统: custom（单文件 Bash CLI）
- 编译日期: 2026-07-13
- 编译器: 不适用
- 状态: built

## 编译与安装

官方 release 资产是完整的 `bashunit` Bash 脚本，不包含 configure、Makefile 或 C/C++ 源码。配方按 application 类型直接下载带 SHA256 校验的官方资产，运行 `bash -n` 语法检查，再复制到 Conan 包的 `bin/` 并设置可执行权限。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 报 `not a gzip file` | 初始化器按 URL 默认推断 tar.gz，但上游资产是无压缩单文件 | 保持官方 URL，在 Conan `source()` 中使用 `download()` 按文件下载，不做解压 |
| 2 | 探索安装阶段 `install: command not found` | OHOS toybox 不提供 GNU install 命令 | 使用 `mkdir`、`cp`、`chmod` 完成隔离安装验证 |

两个错误均已先查询知识图谱；安装命令缺失命中 E098。单文件资产误解压没有得到相关匹配，因此通过 `graph add --draft` 生成并完善 E214 草稿，配方按已确认的源码形态处理。

## 源码修改

无源码修改，无补丁。

## 依赖版本

无 Conan 编译依赖。运行时需要 Bash；它属于该纯 Bash CLI 的解释器要求。

## 验证结果

```text
bash -n bashunit                         PASS
./bashunit --version                    bashunit - 0.40.0
staging 中 bashunit --version           bashunit - 0.40.0
官方资产 SHA256                         PASS
Conan test_package                      执行 --version 和真实 assert_same 测试
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/bashunit | 官方 0.40.0 单文件 Bash CLI |
---

**编译结束**: 2026-07-13 20:47
**最终状态**: built

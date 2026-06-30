# Subversion

Apache Subversion（SVN）是一个开源的版本控制系统。

## 描述

Subversion 是一个现代化的版本控制系统，支持：
- 目录版本控制
- 原子提交
- 版本化元数据
- 高效的分支和标签
- 合并跟踪
- 文件锁定

## 已编译版本

| 版本 | 状态 | 日期 | 平台 |
|------|------|------|------|
| 1.14.5 | published | 2026-05-25 | aarch64-unknown-linux-ohos |

## 依赖

- apr/1.7.6
- apr-util/1.6.3
- expat/2.7.1
- zlib/1.3.1
- openssl/1.1.1w

## 安装工具

- svn - 命令行客户端
- svnadmin - 仓库管理工具
- svnserve - SVN 服务器
- svnlook - 仓库检查工具
- svnsync - 仓库同步工具
- 其他：svnbench, svndumpfilter, svnfsfs, svnmucc, svnrdump, svnversion

## 补丁说明

1. **configure.patch** - TMPDIR 环境变量支持（解决 HMDFS 临时目录问题）
2. **config.guess.patch** - HarmonyOS 平台识别更新
3. **config.sub.patch** - ohos-linux 三元组支持
4. **gen-make.opts.patch** - 构建选项调整

## 平台注意事项

- HMDFS 不支持在当前目录创建子目录，需使用 TMPDIR
- config.guess/config.sub 更新到 2023 版本以支持 HarmonyOS
- SQLite amalgamation 需要单独下载并放置在源码目录

## 参考

- 官网：https://subversion.apache.org/
- 文档：https://subversion.apache.org/docs/
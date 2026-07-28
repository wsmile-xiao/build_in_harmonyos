# mr (myrepos) — Multiple Repository management tool

## 概述

mr (myrepos) 是一个纯 Perl 脚本工具，用于管理多个版本控制仓库。
它可以在一组仓库上执行 checkout、update、status、commit、push 等操作，
就像操作一个组合仓库一样。支持 git、svn、mercurial、bzr、darcs、cvs、fossil 等版本控制系统。

## 版本

- 上游版本: 1.20180726
- 许可证: GPL-2.0-or-later
- 上游 URL: https://myrepos.branchable.com/
- 作者: Joey Hess

## 构建说明

- 类型: Perl 脚本（无需 C/C++ 编译）
- 构建系统: makefile（make build 生成 man 页，make install 安装）
- 编译器: 不适用
- 目标平台: OHOS aarch64

## 功能

- `mr` — 管理多个版本控制仓库的主命令
- `mr update` — 更新所有已注册的仓库
- `mr commit` — 提交所有已注册仓库的更改
- `mr status` — 查看所有已注册仓库的状态
- `mr register` — 注册当前仓库到 ~/.mrconfig
- `mr help` — 显示帮助信息
- `webcheckout` — 从网页检出仓库

## 依赖

- 运行时: perl
- 构建时: pod2man（生成 man 手册页）

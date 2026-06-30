# dash-shell

Debian Almquist Shell — 严格遵循 POSIX 标准、追求体积与速度优化的轻量 shell。

## 简介

dash（Debian Almquist Shell）是从 ash（Almquist Shell）演化而来的轻量级 POSIX 兼容 shell，针对体积和执行速度进行了优化。它在众多 Debian 衍生系统中常被用作 `/bin/sh`。dash 严格遵循 POSIX shell 规范，不包含 bash 扩展功能。

## 主要特性
- POSIX 兼容 shell，体积极小
- Shell 脚本执行速度快
- 适合作为 `/bin/sh` 替代
- 支持：变量、函数、流程控制、管道、重定向、信号捕获、文件名展开

## 版本
0.5.13.2

## 许可证
BSD-3-Clause（版权：加州大学董事会、Herbert Xu）

## 主页
http://gondor.apana.org.au/~herbert/dash/

## 依赖
无（自包含软件）

## 编译信息
- 构建系统：autotools
- 编译器：clang (clang++)
- 平台：HarmonyOS (aarch64)，HongMeng Kernel 1.12.0
- 配置选项：`--prefix=/storage/Users/currentUser/usr/local`
- 补丁：4 个（config.guess、config.sub、configure、mkbuiltins — 全部仅平台相关）

## 已知平台限制
- HMDFS：`sort`/`cat` 从管道读取可能失败（Permission denied）；mkbuiltins 补丁中将管道输出重定向到临时文件绕过此问题
- HMDFS：`/tmp` 为只读；需使用 `TMPDIR=$HOME/tmp`
- dash 不支持 bash 特有的参数展开语法（如 `${x:0:4}`）——这是 POSIX 规范限制，非 bug
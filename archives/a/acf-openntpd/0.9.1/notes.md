
# acf-openntpd 0.9.1 适配笔记



## 编译环境



- 构建系统: custom

- 编译日期: 2026-08-11

- 软件类型: 纯 Lua/LSP ACF Web 管理模块

- 状态: published



## 上游信息



上游项目：



`https://gitlab.alpinelinux.org/acf/acf-openntpd`



上游 Makefile 的 `APP_DIST` 为：



`openntpd*`



安装目录为：



`/usr/share/acf/app/openntpd`



Conan 制品中统一为：



`share/acf/app/openntpd`



## 依赖



- acf-core/0.24.1



源码中的 `modelfunctions`、`acf.fs`、`acf.format` 等能力由 ACF 框架提供。



上游 Alpine 包同时声明 OpenNTPD 为运行时依赖，该模块通过 `/etc/ntpd.conf`、`ntpd` 进程和服务控制接口管理 OpenNTPD。



当前 Conan 制品仓无 `openntpd` recipe，因此本配方不将其声明为 Conan 构建依赖。



## 符号链接处理



上游源码包含 3 个悬空符号链接：



- `openntpd-expert-html.lsp -> ../expert-html.lsp`

- `openntpd-logfile-html.lsp -> ../logfile-html.lsp`

- `openntpd-status-html.lsp -> ../status-html.lsp`



这些链接指向 ACF 框架运行时提供的公共模板。



HarmonyOS PC 环境中 init-build 创建 `.work` 时无法跟随这些悬空链接，因此需要保留符号链接本身。



Conan `package()` 使用 Python 判断 `os.path.islink()` 并通过 `os.symlink()` 原样重建相对链接，与上游 `cp -a` 的语义保持一致。



## 源码修改



无源码 Patch。



## 测试



上游未提供独立测试套件。



test_package 验证：



1. `share/acf/app/openntpd` 目录存在；

2. 9 个 `openntpd*` 模块文件完整；

3. 3 个公共模板链接仍保持为符号链接。



测试不编译额外 C/C++ 程序。

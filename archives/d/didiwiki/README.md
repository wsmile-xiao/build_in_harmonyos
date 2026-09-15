# didiwiki

CiWiki（包名 didiwiki，沿用了上游旧名 DidiWiki）是一个小型个人 Wiki 引擎，纯 C 编写，
内建 HTTP 服务器，零外部依赖（仅 libc）。

- **官网**: https://sourceforge.net/projects/ciwiki/
- **许可证**: GPL-2.0-or-later（src 源码头文件声明 GPLv2 "or any later version"；tarball 内 COPYING/LICENSE 为 GPLv2 许可证文本）
- **分类**: web 服务器 / wiki 工具

## 软件描述

CiWiki 是 DidiWiki 的后续分支，面向个人笔记、Todo 等场景，编译后运行 `ciwiki` 即可用
浏览器访问维护 Wiki。主要功能：

- 内建 HTTP 服务器（默认 0.0.0.0:8000，`-l`/`-p` 可调）
- Wiki 文本渲染、页面历史与变更 RSS
- 用户注册/登录（可加密、可锁定）
- 文件上传与图片/文件展示
- 可选 sendmail 新用户通知脚本

注意：上游 3.0.x 发布名为 ciwiki，可执行名也是 `ciwiki`；didiwiki 是 Debian 源码包
沿用的历史名，两者归档字节相同。

## OHOS 适配

- 构建系统：autotools。tarball 自带生成的 configure，直接 configure+make；不要跑
  autogen（configure.ac 的 AM_CONFIG_HEADER 老宏已被现行 automake 移除）。
- configure 无 AC_CANONICAL_HOST，不需要 config.guess/config.sub 补丁。
- configure 的安全临时目录使用 umask 077，与设备默认 umask 冲突，已按 dash-shell
  先例放宽为 007（patches/0001-configure-umask.patch）。
- 零外部库，仅依赖 libc.so，无 OHOS 平台特定的代码分支需求。
- 上游无测试套件（无 tests/ 目录、Makefile.am 无 TESTS），L1 冒烟用 `ciwiki -v`
  验证版本输出。

## 依赖关系

- 编译依赖：无（clang/libc）
- 运行依赖：libc.so

## 参考资料

- 上游项目：https://sourceforge.net/projects/ciwiki/
- Debian 源码包：https://deb.debian.org/debian/pool/main/d/didiwiki/

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 3.0.5 | built | 2026-09-10 | Conan 包 didiwiki/3.0.5，L1 冒烟通过 |

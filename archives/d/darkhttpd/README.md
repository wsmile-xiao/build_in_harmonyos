# darkhttpd

darkhttpd 是一个轻量级、单文件、零依赖的 HTTP 服务器，使用 C 语言编写。

- **官网**: https://github.com/emikulic/darkhttpd
- **许可证**: BSD风格（见源码 COPYING 文件）
- **分类**: web服务器 / 网络工具

## 软件描述

darkhttpd 是一个极简 HTTP 服务器，全部源码仅一个 darkhttpd.c 文件，无外部依赖（仅需 libc）。功能包括：

- 静态文件服务（HTML/JSON/图片等）
- 自动目录列表生成
- HEAD请求支持
- HTTP基本认证（--auth参数）
- 反向代理转发（--forward参数）
- 守护进程模式（--daemon参数）
- 日志记录（--log/--syslog）
- 自定义MIME类型映射

## 适配说明

- **构建系统**: 简单Makefile（无configure脚本、无install目标）
- **编译方式**: `make CC=clang CFLAGS="-fPIC -O2"` + 手动cp安装
- **依赖**: 仅 libc.so（无第三方依赖）
- **测试**: 官方test.py因OHOS socket限制无法运行，手动HTTP功能测试18项全部通过

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 1.17 | built | 2026-06-16 | 预编译包已生成，核心功能验证通过 |

# fcgi2

FastCGI 2.x 参考实现：libfcgi / libfcgi++ C/C++ 库与 cgi-fcgi 调试工具。

## 功能概述

- **libfcgi**（C 库）：FastCGI 协议核心实现，提供 `FCGI_Accept`、`FCGX_Accept_r`、
  `FCGX_GetParam`、`FCGX_FPrintF` 等公开 API，支持 CGI 回退模式与 FastCGI
  多请求循环。
- **libfcgi++**（C++ 库）：`FCGX_Request` 面向对象封装（`fcgio.h`）。
- **cgi-fcgi**：命令行工具，用于启动/连接 FastCGI 应用进程（调试用）。

## OHOS 适配要点

- 构建系统：autotools。GitHub 官方 archive（tag tarball）**不包含 configure**，
  需 `autoreconf` 自举（`tool_requires automake/1.18 + libtool/2.5.4`）。
- OHOS 平台：`os=OHOS` 时追加 `--build=aarch64-unknown-linux-gnu` 跳过
  2007 年代 config.guess/sub 的三元组猜测（jwhois 先例）。
- E011 umask：自举生成的 configure 含 `umask 077`，HMDFS 上临时文件不可写，
  必须在 autoreconf **之后**替换为 `umask 022`（顺序不可反，gsl/cliquer 同款）。
- 产物：libfcgi / libfcgi++（.so/.a）+ cgi-fcgi（bin），无外部依赖
  （libfcgi 仅 libc；libfcgi++ 需 libstdc++）。
- 上游无测试套件（无 tests/ 目录、无 TESTS/check_PROGRAMS、无 CTest），
  消费者测试通过 test_package 以 CGI 回退模式实际调用 FCGI_Accept 验证。

## 历史版本

- 2.4.2：built（2026-09-14，本仓库首次适配）
- 2.4.7：built（2026-09-21，当前版本；修复 test_package 隐式声明等）

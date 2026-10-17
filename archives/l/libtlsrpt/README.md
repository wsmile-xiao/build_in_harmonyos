# libtlsrpt

## 简介

libtlsrpt 是 sys4 开源的底层 C 库，实现 TLSRPT（RFC 8460，SMTP TLS 报告）datagram 的生成。MTA（如 Postfix）在投递过程中调用它，把 TLS 握手成功/失败事件经本地 datagram 套接字发往 TLSRPT 收集服务（tlsrpt-collectd），最终汇总为发件域请求的 TLSRPT 报告。

## OHOS 适配

- 使用 Autotools 构建系统（configure + make + make install），release 包自带 configure
- 无外部编译依赖（自包含构建；FreeBSD/Gentoo 均确认无依赖）
- 上游无测试套件（Makefile.am 无 TESTS/check 目标，仅 demo.c 手动演示程序）
- test_package 自建消费者测试：版本查询、错误码辅助函数、投递请求/策略全生命周期
- 纯 C 库，非系统同名库，默认静态构建（shared=False，可选共享）

## 依赖

无外部编译依赖。

## 功能验证

```bash
# 验证 pkg-config
pkg-config --modversion libtlsrpt
# 输出: 0.5.1

# 验证静态库与头文件
ls <package>/lib/libtlsrpt.a
ls <package>/include/tlsrpt.h <package>/include/tlsrpt_version.h
```

## 参考

- 上游: https://github.com/sys4/libtlsrpt
- 规范: RFC 8460

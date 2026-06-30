# libmilter

libmilter 是 sendmail 的邮件过滤器库，用于开发第三方邮件过滤程序。

## 简介

libmilter 提供了一套 API，允许开发者编写邮件过滤器（milter），用于在邮件传输过程中进行各种检查和修改。常见应用包括：
- 病毒扫描
- 内容过滤
- 反垃圾邮件
- 邐揖记录

## 版本

- 8.18.2 (2026-05-28) - HarmonyOS 支持

## 编译特性

- 构建系统: sendmail Build (非 autotools)
- 编译产物: 静态库 (libmilter.a)
- 平台支持: HarmonyOS HongMengKernel 1.12.0 aarch64

## musl 兼容性

libmilter 依赖 sendmail 的 libsm 库，该库需要 musl libc 兼容性修复：
- sys_errlist/sys_nerr 在 musl 中不可用
- 使用标准 strerror() 函数替代

## 使用

编译后的静态库可直接链接到邮件过滤器程序：

```bash
# 链接示例
clang -o myfilter myfilter.c -lmilter -lpthread
```

头文件位于 `include/libmilter/` 目录：
- `libmilter.h` - 主头文件
- `mfapi.h` - API 定义
- `mfdef.h` - 宏定义
- `milter.h` - 基础定义

## 参考资源

- 官方文档: https://www.sendmail.org/
- API 文档: libmilter/docs/
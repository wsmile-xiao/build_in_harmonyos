# oSIP Library (libosip2)

## 简介

oSIP库是一个开源的SIP（Session Initiation Protocol）协议栈实现，由GNU项目维护。它提供了SIP消息的解析、生成和事务管理功能，是构建SIP应用程序的基础库。

oSIP分为两个主要模块：
- **libosip2**: SIP事务管理和对话管理
- **libosipparser2**: SIP消息解析和生成

## OHOS 适配

- oSIP使用标准autotools构建系统，支持configure/make/make install流程
- 需更新config.guess/config.sub以识别HarmonyOS平台（解决E007错误）
- HMDFS文件系统umask设置需修改configure中的umask 077为022（解决E011错误）
- 使用hints脚本替代补丁方案，规避HMDFS patch命令限制
- 无外部编译依赖，仅需标准C库、pthread和librt

## 依赖

无外部编译依赖。

运行时依赖：
- 标准C库（libc）
- POSIX线程库（libpthread）
- 实时扩展库（librt，用于clock_gettime）

## 功能验证

```bash
# 验证库文件已安装
pkg-config --modversion libosip2
# 预期输出：5.3.1

# 验证头文件
ls ~/usr/local/include/osip2/
ls ~/usr/local/include/osipparser2/

# 验证库文件
ls ~/usr/local/lib/libosip2.so
```

## 参考

- 官网: https://www.gnu.org/software/osip/
- 源码: https://ftp.gnu.org/gnu/osip/
- 文档: https://www.gnu.org/software/osip/documentation.html
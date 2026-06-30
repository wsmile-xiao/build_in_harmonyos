# liblksctp

## 简介
liblksctp (lksctp-tools) 是 Linux Kernel SCTP (Stream Control Transmission Protocol) 的用户空间工具和库。

## 版本
- 当前版本: 1.0.17

## 依赖
- 无外部依赖（基础系统库）

## 特性
- SCTP 协议用户空间库
- 提供 libsctp.so 和 libsctp.a
- 包含测试和诊断工具
- 支持 SCTP 多流和多宿特性

## 编译说明
- 构建系统: autotools
- 平台适配: config.guess/config.sub 补丁（OHOS 平台识别）
- 内核要求: 需要内核 SCTP 支持（可能未启用）

## 归档位置
`archives/l/liblksctp/1.0.17/`
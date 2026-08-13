# libsmb2

## 简介

libsmb2 是一个用于访问 SMB 共享的客户端库，支持 SMB2 和 SMB3 协议。纯 C 实现，不依赖 Samba，适合嵌入式和轻量级环境。

## OHOS 适配

- **构建系统**: 项目同时支持 CMake 和 autotools，推荐使用 CMake
- **平台检测**: CMake 输出 "System is unknown to cmake" 警告，不阻塞编译，编译器和头文件检测正常
- **源码修改**: 无需任何补丁即可编译通过
- **外部依赖**: 仅依赖 libc.so，无外部库依赖
- **Kerberos/GSSAPI**: 头文件缺失不影响核心功能，NTLM 认证足够使用
- **已知问题**: 上游 CMakeLists.txt 中 .pc 文件版本号硬编码为 6.1.0，实际版本以 git tag 为准

## 排除与替代

无。libsmb2 是纯库，无可执行命令需要排除。

## 依赖

### 编译依赖
- 无（纯 C 实现，仅需标准 C 编译器和 CMake）

### 运行依赖
- libc.so（系统自带）

### 可选依赖（本次未启用）
- krb5 / libgssapi: 用于 Kerberos 认证（NTLM 认证无需）

## 功能验证

编译后通过 20 项功能测试验证（详见 `6.2/reports/test-report.md`）：

- 库版本信息获取 (smb2_get_libsmb2Version)
- 上下文生命周期管理 (init/close/destroy/set/get 系列)
- SMB URL 解析 (smb2_parse_url)
- Windows 时间转换 (smb2_win_to_timeval/smb2_timeval_to_win)
- 多上下文独立性
- 错误处理 (smb2_set_error/smb2_get_error/nterror_to_str)
- UTF-16 编解码往返一致性
- 编译时符号链接验证

## 上游测试套件

上游 libsmb2 6.2 的 `tests/` 目录包含以下测试（由 autotools `make check` 执行）：

- **C 单元测试 (2个)**：`aes128ccm-test.c`（AES-128-CCM 加密验证）、`smb2-dcerpc-coder-test.c`（DCE-RPC 编解码验证）
- **Shell 集成测试 (13个)**：`test_0100_ls_basic.sh` ~ `test_900_dcerpc.sh`，涵盖 ls/mkdir/cp/cat/dcerpc 等功能，均需运行中的 SMB 服务端

**执行情况**：CMake 构建未集成 autotools 测试目标；shell 集成测试需要运行中的 SMB 服务端，鸿蒙环境未执行。通过 test_package 消费者测试替代验证核心 API 功能。

## 已编译版本

| 版本 | 状态 | 日期 | 构建系统 | 补丁 |
|------|------|------|---------|------|
| 6.2 | published | 2026-07-23 | cmake | 0 |

## 参考

- 源码仓库: https://github.com/sahlberg/libsmb2
- 许可证: LGPL-2.1-or-later

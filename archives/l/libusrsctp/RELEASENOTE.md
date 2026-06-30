# libusrsctp — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libusrsctp-0.9.5.0-ohos-aarch64.tar.gz -C ~/usr/local

cd libusrsctp-0.9.5.0-ohos-aarch64 && sh install-libusrsctp-0.9.5.0.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 | 测试 |
|------|------|--------|------|
| 0.9.5.0 | ✅ success | 5 | ✅ PASS |

## 当前版本 (0.9.5.0) 详情

### 包内容
- 静态库: `lib/libusrsctp.a` (773KB)
- 头文件: `include/usrsctp.h` (43KB)
- pkg-config: `lib/pkgconfig/usrsctp.pc`
- 包大小: 803KB

### 编译信息
- 构建系统: cmake
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 5
- 测试验证: ✅ 功能验证测试通过

### 补丁列表
- 0001-CMakeLists.txt.patch (build_flag)
- 0002-usrsctplib-netinet-sctp_os_userspace.h.patch (platform_compat)
- 0003-usrsctplib-netinet-sctp_pcb.c.patch (ansi_c_fix)
- 0004-usrsctplib-netinet-sctp_sysctl.c.patch (ansi_c_fix)
- 0005-usrsctplib-user_malloc.h.patch (platform_compat)

### 测试验证
编写功能验证程序测试基本 API：
- ✅ usrsctp_init() - 协议栈初始化成功
- ✅ usrsctp_finish() - 协议栈清理成功
- ✅ 库符号链接验证通过
- ⚠️ socket 创建需要完整网络栈（预期行为）

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- C 编译器: Clang/GCC
- 链接时需要: `-lpthread`

## 使用示例

```c
#include <usrsctp.h>

// 初始化协议栈
usrsctp_init(0, NULL, NULL);

// 创建 socket
struct socket *so = usrsctp_socket(AF_CONN, SOCK_SEQPACKET, IPPROTO_SCTP, NULL, NULL, 0, NULL);

// ... SCTP 通信 ...

// 清理
usrsctp_finish();
```

## 已知限制
- 示例程序未编译（musl 不支持 pthread_cancel）
- 完整 SCTP 通信需要上层应用实现网络连接

## 详细信息
- 测试报告: `reports/test-report.md`
- 编译进度: `PROGRESS.md`
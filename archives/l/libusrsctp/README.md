# libusrsctp 0.9.5.0 — OpenHarmony 编译记录

## 基本信息
- 软件: libusrsctp
- 版本: 0.9.5.0
- 构建系统: cmake
- 目标: ohos-aarch64
- 状态: partial（核心库可用，无测试套件）

## 软件介绍
libusrsctp 是用户态 SCTP（Stream Control Transmission Protocol）协议栈实现。SCTP 是一种传输层协议，提供可靠的数据传输，支持多流和多宿特性。

## 编译指导

### 前置条件
- cmake >= 3.5
- clang/llvm (ohos-sdk)
- 无依赖库

### 编译步骤
```bash
mkdir -p build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -Dsctp_build_programs=OFF \
      ..
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

### 重要参数说明
- `-Dsctp_build_programs=OFF`: 禁用示例程序（musl 不支持 pthread_cancel）
- `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`: cmake 版本兼容性

## 补丁清单

### 0001-CMakeLists.txt.patch
- 类型: build_flag
- 说明: 添加 POSIX/GNU 特性定义，禁用兼容性警告
- 修改: `-D_GNU_SOURCE`, `-D_POSIX_C_SOURCE=200809L`, `-Wno-sign-compare`, `-Wno-unused-but-set-variable`

### 0002-usrsctplib-netinet-sctp_os_userspace.h.patch
- 类型: platform
- 说明: 启用 POSIX 特性，添加 time.h 头文件
- 修改: `_GNU_SOURCE`, `_POSIX_C_SOURCE`, `<time.h>`

### 0003-usrsctplib-netinet-sctp_pcb.c.patch
- 类型: code_fix
- 说明: 修复 K&R 函数声明 → ANSI C
- 修改: `sctp_drain()` → `sctp_drain(void)`

### 0004-usrsctplib-netinet-sctp_sysctl.c.patch
- 类型: code_fix
- 说明: 修复 K&R 函数声明 → ANSI C
- 修改: `sctp_init_sysctls()` → `sctp_init_sysctls(void)`, `sctp_finish_sysctls()` → `sctp_finish_sysctls(void)`

### 0005-usrsctplib-user_malloc.h.patch
- 类型: platform
- 说明: 定义 BSD 类型缺失（musl 兼容性）
- 修改: `u_char`, `u_int`, `u_long`, `u_short`, `caddr_t`, `IFNAMSIZ`, `timercmp`, `timersub`, `timeradd`

## 已知限制

### 1. 示例程序不可用
- 原因: musl 不支持 `pthread_cancel`
- 影响文件: `programs/ekr_loop.c`, `programs/ekr_client.c`, `programs/ekr_loop_upcall.c`
- 解决方案: 禁用示例程序编译，用户可自行编写替代测试

### 2. 无内置测试套件
- 原因: 项目未集成 ctest/googletest
- 解决方案: 用户自行编写 SCTP socket 创建测试

### 3. 静态库编译
- 说明: 默认编译为静态库
- 影响: 需要静态链接到用户程序

## 功能验证

### 验证命令
```c
// 简单验证代码 (用户自行编写)
#include <usrsctp.h>

int main() {
    usrsctp_init(0, NULL, NULL);
    struct socket *sock = usrsctp_socket(AF_CONN, SOCK_STREAM, SCTP_SCTP_SOCKET, NULL, NULL, 0, NULL);
    if (sock) {
        printf("SCTP socket created successfully\n");
        return 0;
    }
    return 1;
}
```

编译测试:
```bash
gcc -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib -lusrsctp test_sctp.c -o test_sctp
./test_sctp
```

## 链接使用
```bash
# pkg-config 方式
pkg-config --cflags usrsctp
pkg-config --libs usrsctp

# 手动链接
-L$DEFAULT_PREFIX/lib -lusrsctp -pthread
```

## 参考资料
- 官方仓库: https://github.com/sctplab/usrsctp
- SCTP RFC: https://tools.ietf.org/html/rfc4960
# ortp

## 简介

oRTP 是一个 C 语言实现的 RTP 协议库（RFC 3550），为大多数 Unix 系统（主要是 Linux 和 HP-UX）以及 Microsoft Windows 提供支持。它是 Linphone 项目的一部分，用于处理实时传输协议。

## OHOS 适配

### 适配要点

1. **CMake 版本兼容性**：需要将 `cmake_minimum_required(VERSION 3.1)` 改为 3.5 或更高，以兼容 CMake 4.x
2. **依赖处理**：依赖 bctoolbox 库，但 cmd-pkgs 无预编译包，需手动编译
3. **编译警告处理**：`rtpsession_inet.c` 中 CMSG_NXTHDR 宏产生类型比较警告，需添加 `-Wno-error=sign-compare` 编译选项
4. **测试程序禁用**：测试程序依赖 `bctoolbox/tester.h`，建议禁用测试编译

### 已知问题

- 函数原型声明弃用警告（`-Wstrict-prototypes`）：不影响编译，仅作为警告处理
- CMSG_NXTHDR 宏类型比较警告：平台头文件定义问题，非源码错误

### 与 Linux 的差异

- 使用 Clang 15.0.4 编译器而非 GCC
- 动态库命名遵循 OHOS 规范（libortp.so）
- 使用 DESTDIR 模式进行 staging 验证

## 依赖

### 编译依赖

- **bctoolbox**: >= 0.2.0（必须）
  - 版本 5.5.0 已成功编译并安装
  - 需禁用 MBEDTLS/OPENSSL/DECAF/TESTS_COMPONENT/UNIT_TESTS

### 运行依赖

- bctoolbox（动态链接）

## 功能验证

### pkg-config 验证

```bash
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --modversion ortp  # 输出: 5.2.0
pkg-config --libs ortp        # 输出: -L/storage/Users/currentUser/usr/local/lib -lortp
pkg-config --cflags ortp      # 输出: -I/storage/Users/currentUser/usr/local/include
```

### 库文件检查

- 静态库：`libortp.a` (329KB)
- 动态库：`libortp.so` (322KB)

## 排除与替代

无特殊排除项。

## 参考

- 官网：https://www.linphone.org/technical-corner/ortp
- 源码仓库：https://gitlab.linphone.org/BC/public/ortp
- GitHub 镜像：https://github.com/BelledonneCommunications/ortp
- 许可证：GNU AGPLv3 或 商业许可
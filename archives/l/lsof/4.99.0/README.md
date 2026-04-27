# lsof 4.99.0 for HarmonyOS

## 概述

lsof (List Open Files) 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

⚠️ **重要提示**: lsof 在 HarmonyOS 上存在平台限制，无法正常访问 /proc 文件系统，功能受限。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | lsof |
| 版本 | 4.99.0 |
| 下载地址 | https://api.github.com/repos/lsof-org/lsof/tarball/4.99.0 |
| 官方文档 | https://github.com/lsof-org/lsof |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 |
| 构建系统 | Configure (lsof特有) + make |

## 编译步骤

```bash
# 1. 初始化编译环境
SKILL_ROOT="$(dirname "$(find "$HOME/.opendesk" -name "SKILL.md" -path "*openharmony-compile-agent*" 2>/dev/null | head -1)")"
python3 $SKILL_ROOT/scripts/ohc-run.py init-build lsof 4.99.0 --url=https://api.github.com/repos/lsof-org/lsof/tarball/4.99.0

# 2. 设置环境变量
export LINUX_CONF_CC=clang
export LSOF_INCLUDE=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include
export CC=clang

# 3. 应用补丁
cd $BUILD_SRC_DIR
patch -p1 < patches/0001-Mksrc-shebang.patch
patch -p1 < patches/0002-dlsof.h-ohos-fix.patch

# 4. 配置
./Configure -n linux

# 5. 编译
make CC=clang -j$(nproc)

# 6. 安装（lsof 没有默认 install 规则，需手动安装）
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp lsof $TEST_PREFIX/$DEFAULT_PREFIX/bin/
chmod 755 $TEST_PREFIX/$DEFAULT_PREFIX/bin/lsof
```

## 补丁说明

### 0001-Mksrc-shebang.patch

**目的**: 修复 Mksrc 脚本的 shebang，适应 HarmonyOS 的 bash 位置

**修改文件**:
- `lib/dialects/linux/Mksrc`: 将 `#!/bin/bash` 改为 `#!/data/service/hnp/bin/bash`

**原因**: HarmonyOS 上 `/bin/bash` 不存在，bash 位于 `/data/service/hnp/bin/bash`

### 0002-dlsof.h-ohos-fix.patch

**目的**: 解决 sockaddr_storage 结构体重复定义问题

**修改文件**:
- `lib/dialects/linux/dlsof.h`: 
  1. 添加 `__OHOS__` 条件到 tcp 头文件选择，避免 linux/tcp.h 引入 linux/socket.h
  2. 在 `sys/socket.h` 之后定义必要的类型并设置 `_UAPI_LINUX_SOCKET_H`，防止后续重复包含

**原因**: 
- `sys/socket.h` 和 `linux/socket.h`（通过 linux/netlink.h 间接包含）都定义了 `sockaddr_storage`
- OHOS 的 musl libc 系统头文件与 Linux kernel 头文件存在命名冲突

## 遇到的问题

### 问题1: Configure 脚本无法检测 IPv6

**现象**: Configure 生成的 Makefile 没有 `-DHASIPv6` 定义

**原因**: Configure 默认使用 `/usr/include` 作为 LSOF_INCLUDE，但 HarmonyOS 的头文件在 OHOS sysroot

**解决**: 设置环境变量 `LSOF_INCLUDE=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include`

### 问题2: sockaddr_storage 重复定义

**现象**: 编译错误 `error: redefinition of 'sockaddr_storage'`

**原因**: `sys/socket.h` 和 `linux/socket.h` 都定义了同名结构体，OHOS 平台的 musl libc 与 kernel 头文件冲突

**解决**: 在 `dlsof.h` 中添加 OHOS 特定处理，定义必要类型后跳过 `linux/socket.h` 的包含

### 问题3: 平台限制 - /proc 文件系统访问受限

**现象**: lsof 编译成功但运行时无输出，查询进程无结果

**原因**: HarmonyOS 对 /proc 文件系统的访问有权限限制，普通用户无法读取其他进程信息

**解决**: 记录为平台限制，lsof 在 OHOS 上功能受限

## 测试结果

详见 [PROGRESS.md](./PROGRESS.md)

| 测试项 | 结果 |
|--------|------|
| 编译 | ✅ 成功 |
| 安装 | ✅ 成功 |
| 运行 | ⚠️ 功能受限（/proc 访问受限） |
| ELF 签名 | ❌ 失败（"is not trust command"） |

## 验证安装

```bash
# 检查安装
ls -la $HOME/usr/local/bin/lsof

# 检查依赖
readelf -d $HOME/usr/local/bin/lsof | grep NEEDED
# 输出: Shared library: [libc.so]

# 尝试运行（注意：功能受限）
$HOME/usr/local/bin/lsof
# 可能无输出（/proc 访问受限）
```

## 经验总结

1. **shebang 修复**: HarmonyOS 的 bash 位于 `/data/service/hnp/bin/bash`，不是 `/bin/bash`
2. **头文件路径**: Configure 类脚本可能使用硬编码的头文件路径，需要设置环境变量覆盖
3. **结构体冲突**: musl libc 与 kernel UAPI 头文件可能存在同名结构体冲突，需要条件编译处理
4. **平台限制**: 某些 Linux 工具依赖特定的内核功能（如 /proc），在 HarmonyOS 上可能受限

## 参考资料

- [lsof GitHub Repository](https://github.com/lsof-org/lsof)
- [lsof Documentation](https://lsof.readthedocs.io/)
- [OHOS sysroot header conflicts](knowledge/operations/build-systems.md)
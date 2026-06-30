# clamsmtp 1.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

ClamSMTP 是一个 SMTP 过滤代理，用于与 ClamAV 集成，实现邮件病毒扫描功能。

**实际编译流程**：

1. **下载源码**：从官方 URL 下载 `clamsmtp-1.10.tar.gz`
2. **解压源码**：解压到 `~/tmp/builds/clamsmtp-1.10.work`
3. **应用补丁**：应用 3 个平台适配补丁
4. **配置编译**：`./configure --prefix=/storage/Users/currentUser/usr/local`
5. **编译**：`make -j1`
6. **安装**：`make install DESTDIR=/storage/Users/currentUser/tmp/test-install-clamsmtp-1.10`
7. **验证**：测试二进制可用性

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 头文件冲突 | `LINUX_TRANSPARENT_PROXY` 模式下，`linux/netfilter_ipv4.h` 与 `netinet/in.h` 结构体重复定义 | 使用 `#ifdef __OHOS__` 守卫，先包含 `netinet/in.h`，定义 `_UAPI_LINUX_IN_H` 防止重复定义 |
| 2 | 平台识别失败 | config.guess 无法识别 HarmonyOS 平台 | 在 config.guess 添加 `aarch64:HarmonyOS:*:` 模式识别，返回 `aarch64-unknown-linux-gnu` |
| 3 | HMDFS 权限限制 | configure 创建临时目录时使用 `umask 077`，HMDFS 不支持过于严格的权限 | 将 configure 中的 `umask 077` 改为 `umask 022` |

## 源码修改

应用了 3 个补丁文件：

| 补丁文件 | 修改目标 | 知识条目 | 类型 |
|----------|----------|----------|------|
| `0001-common-smtppass.c.patch` | `common/smtppass.c` | E091 | OHOS 头文件冲突修复 |
| `0003-config.guess.patch` | `config.guess` | E007 | 平台识别修复 |
| `0004-configure-umask.patch` | `configure` | E011 | HMDFS 权限修复 |

**0001-common-smtppass.c.patch 详细说明**：
- 位置：`#ifdef LINUX_TRANSPARENT_PROXY` 代码块
- 问题：OHOS 系统中 `linux/netfilter_ipv4.h` 会间接包含 `linux/in.h`，与已包含的 `netinet/in.h` 结构体定义冲突
- 修复：在 OHOS 平台先包含 `netinet/in.h`，然后定义 `_UAPI_LINUX_IN_H` 和 `_UAPI_LINUX_IN6_H` 守卫，阻止 linux 头文件重复定义
- 代码：
  ```c
  #ifdef LINUX_TRANSPARENT_PROXY
  #ifdef __OHOS__
  #include <netinet/in.h>
  #define _UAPI_LINUX_IN_H
  #define _UAPI_LINUX_IN6_H
  #endif
  #include <linux/netfilter_ipv4.h>
  #ifdef __OHOS__
  #undef _UAPI_LINUX_IN_H
  #undef _UAPI_LINUX_IN6_H
  #endif
  #endif
  ```

## 依赖版本

无外部依赖。ClamSMTP 是独立编译的 SMTP 过滤代理。

编译工具链：
- clang (系统自带)
- autotools (autoconf, automake)

## 验证结果

```bash
# 编译产物
ls ~/tmp/test-install-clamsmtp-1.10/storage/Users/currentUser/usr/local/bin/
clamsmtpd

# 二进制信息
file clamsmtpd
# ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), dynamically linked

# 运行测试（需要配置文件）
./clamsmtpd --help
# 显示帮助信息，确认可执行
```

## 交付物

预编译包待生成：`clamsmtp-1.10-ohos-aarch64.tar.gz`

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/clamsmtp-1.10-ohos-aarch64.tar.gz | 待生成 | 预编译包 |

## 注意事项

1. **透明代理模式**：ClamSMTP 支持透明代理模式（`LINUX_TRANSPARENT_PROXY`），需要内核支持 iptables/netfilter
2. **配置文件**：运行需要配置文件（`/etc/clamsmtpd.conf`），需手动配置 ClamAV socket 地址
3. **权限要求**：透明代理模式需要 root 权限运行
4. **OHOS 限制**：透明代理功能在 OHOS 上可能受限（iptables 支持情况未知），建议使用标准代理模式

---
**编译结束**: 2026-05-28 18:10
**最终状态**: built
## 功能测试

**测试日期**: 2026-05-29
**测试结果**: PASS

### 测试项通过情况
- ✅ 版本信息: 正确显示版本 1.10
- ✅ 帮助信息: 正确显示使用说明
- ✅ 二进制检查: ELF 64-bit ARM64, 依赖 libc.so
- ⚠️ ELF 签名: 存在 .note.ohos.ident 段但格式有警告
- ✅ 配置解析: 正确解析配置文件
- ✅ 网络功能: 成功绑定端口并启动服务
- ✅ 透明代理: 代码存在，支持 TransparentProxy 配置
- ✅ 文档: man5/man8 文档完整

### 已知问题
1. **ELF 签名格式警告**: readelf 显示 `.note.ohos.ident` 段格式不规范，但不影响运行
2. **透明代理限制**: 透明代理功能依赖 iptables/netfilter，在 HarmonyOS 上可用性待验证

### 测试环境
- HarmonyOS Kernel 1.12.0
- 架构: aarch64
- C 库: musl libc

详细报告见: reports/test-report.md
---

**编译结束**: 2026-05-29 10:16
**最终状态**: published

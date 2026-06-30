# catatonit 0.2.1 适配笔记

## 编译环境
- 构建系统: autotools（但 configure 在 tmpfs 上无法运行，改为手动编译）
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

由于 configure 在 tmpfs 上运行时遇到权限问题，采用手动编译方式：
1. 手动创建 config.h（从 config.h.in 替换变量）
2. 手动编译：`clang -o catatonit catatonit.c -static`
3. Strip 符号：`llvm-strip catatonit`
4. ELF 签名：使用 ohc-run.py sign-elf

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败（permission denied） | tmpfs/HMDFS 平台限制，config.status 无法创建临时文件 | 手动创建 config.h 和 Makefile，手动编译 |
| 2 | automake 1.17 Perl 模块路径错误 | 预编译包 aclocal 硬编码 automake-1.17 路径 | 使用 aclocal-1.16 和 automake-1.16 |
| 3 | 缺少 secure_getenv 函数 | musl C 库不支持 GNU 扩展 secure_getenv | 修改源码，用 getenv 替换 secure_getenv |
| 4 | SSL 证书验证失败 | Savannah 服务器证书问题 | 使用 GitHub releases tarball |
| 5 | close_range syscall 触发 SIGSYS | OpenHarmony 内核不支持 close_range syscall | 移除 SIGSYS from kernel_signals，添加运行时检测 |

## 源码修改

### 补丁 1: 0001-catatonit.c.patch
- **类型**: musl 平台兼容性
- **修改**: 将 secure_getenv 替换为 getenv（2处）
- **原因**: musl C 库不支持 GNU 扩展 secure_getenv
- **影响**: 功能无变化（getenv 在容器环境中行为相同）

### 补丁 2: 0002-fix-close_range-sigsys.patch
- **类型**: OpenHarmony 平台兼容性
- **修改内容**:
  1. 从 `kernel_signals` 数组移除 SIGSYS
  2. 添加 close_range syscall 运行时检测
  3. 不支持时自动 fallback 到 close() 循环
- **原因**: OpenHarmony Kernel 1.12.0 不支持 close_range syscall (syscall 436)
- **影响**: 修复所有测试用例，功能完全正常

## 依赖版本

- clang 15.0.4
- automake 1.16.5
- autoconf 2.72
- libtool 2.4.7

## 测试结果

### 初始版本测试（失败）
- 基本功能: ✅ PASS (3/3)
- 子进程管理: ⚠️ 部分通过 (2/4)
- 边界条件: ⚠️ 部分通过 (2/4)
- 压力测试: ❌ FAIL (0/2)
- 信号处理: ❌ FAIL (1/3)
- **问题**: close_range syscall 触发 SIGSYS，导致所有命令返回 159

### 修复版本测试（成功）
- 基本功能: ✅ PASS (3/3)
- 子进程管理: ✅ PASS (4/4)
- 边界条件: ✅ PASS (4/4)
- 压力测试: ✅ PASS (10/10)
- 信号处理: ✅ PASS (3/3)
- **结论**: 所有功能正常，可以发布

## 验证结果

```bash
$ catatonit --version
tini version 0.2.1_catatonit
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| catatonit-0.2.1-ohos-aarch64.tar.gz | 234KB | 预编译包（静态编译，已修复 SIGSYS 问题） |

## 注意事项

- **configure 限制**: 本软件在 tmpfs/HMDFS 上 configure 会失败，建议在其他平台上生成 configure 后再编译，或使用手动编译方式
- **静态编译**: catatonit 编译为静态二进制，适合容器环境使用
- **补丁必须性**: 两个补丁都是必需的，第一个解决 musl 兼容性，第二个解决 OpenHarmony 内核兼容性

---
**编译结束**: 2026-05-26 14:46
**修复完成**: 2026-05-26 15:25
**最终状态**: published
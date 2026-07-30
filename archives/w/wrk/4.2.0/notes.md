# wrk 4.2.0 编译笔记

## 编译过程

### 1. 初始化
- 源码来自 GitHub: https://github.com/wg/wrk/archive/refs/tags/4.2.0.tar.gz
- 构建系统: Makefile（无 configure）
- 内嵌依赖: LuaJIT-2.1, OpenSSL-1.1.1i

### 2. 遇到的问题及解决方式

#### 问题1: Makefile 不识别 HarmonyOS 平台
- **症状**: `uname -s` 返回 "HarmonyOS"，Makefile 只处理 linux/darwin/sunos/freebsd
- **解决**: 添加 `harmonyos` 目标，使用与 linux 相同的 CFLAGS 和 LIBS

#### 问题2: LuaJIT struct sigaction 不完整类型
- **症状**: `lj_profile.c:67:20: error: field has incomplete type 'struct sigaction'`
- **原因**: OpenHarmony musl libc 需要显式包含 signal.h
- **解决**: 编译 LuaJIT 时添加 `XCFLAGS+=-DLUAJIT_DISABLE_PROFILE` 禁用 profiler

#### 问题3: LuaJIT 使用 gcc 且不识别 HarmonyOS 架构
- **症状**: `gcc: No such file or directory` 和 `Unsupported target architecture`
- **解决**: 传递 `CC=clang TARGET_SYS=Linux` 给 LuaJIT 构建

#### 问题4: LuaJIT lib_io.c popen/pclose 未声明
- **症状**: `call to undeclared function 'popen'`
- **解决**: 在 LuaJIT 解压后 patch lib_io.c 添加 `#include <unistd.h>`

#### 问题5: OpenSSL 不支持 HarmonyOS 平台
- **症状**: `Operating system: aarch64-whatever-HarmonyOS, This system (HarmonyOS) is not supported`
- **解决**: 使用 `./Configure linux-aarch64` 配置

#### 问题6: OpenSSL 继承父 Makefile 的 CFLAGS (-std=c99 导致 asm 失败)
- **症状**: `error: expected ')'` in inline assembly (BSWAP4 macro)
- **原因**: 父 Makefile 的 `-std=c99` 被传递到 OpenSSL 子构建，导致 `asm()` 不被识别
- **解决**: 在 OpenSSL Configure 和 make 命令前加 `env -u CFLAGS`

#### 问题7: wrk.h 缺少 signal.h
- **症状**: `struct sigaction` 不完整类型
- **解决**: 在 src/wrk.h 中添加 `#include <signal.h>`

#### 问题8: ELF 二进制无法执行 (HarmonyOS 签名要求)
- **症状**: `Operation not permitted` (exit code 126)
- **原因**: HarmonyOS 要求 ELF 二进制包含 `.codesign` 签名段才能执行
- **解决**: 在 Makefile 中添加签名步骤:
  1. `llvm-objcopy --remove-section .codesign` (移除已有签名)
  2. `binary-sign-tool sign -inFile ... -outFile ... -selfSign 1`
  需要在 LuaJIT 构建后（用于编译 bytecode）和 wrk 链接后各签名一次

### 3. 修改文件
- `Makefile`: 添加 HarmonyOS 平台支持、LuaJIT/OpenSSL 构建修复、ELF 签名步骤
- `src/wrk.h`: 添加 `#include <signal.h>`

### 4. 依赖包
- LuaJIT-2.1 (内嵌)
- OpenSSL 1.1.1i (内嵌)

### 5. 产物
- wrk 可执行文件 (ELF shared object, 64-bit LSB arm64)

---
**编译开始**: 2026-07-15
**最终状态**: built
---

**编译结束**: 2026-07-15 20:42
**最终状态**: built

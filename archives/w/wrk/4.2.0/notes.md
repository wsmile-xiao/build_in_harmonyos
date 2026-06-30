# wrk 4.2.0 编译笔记

## 编译过程

### 1. 初始化
- 源码来自 GitHub: https://github.com/wg/wrk/archive/refs/tags/4.2.0.tar.gz
- 构建系统: Makefile（无 configure）

### 2. 遇到的问题及解决方式

#### 问题1: LuaJIT struct sigaction 不完整类型
- **症状**: `lj_profile.c:67:20: error: field has incomplete type 'struct sigaction'`
- **原因**: OpenHarmony musl libc 需要显式包含 signal.h
- **解决**: 在 LuaJIT 编译时添加 `XCFLAGS+=-DLUAJIT_DISABLE_PROFILE` 禁用 profiler

#### 问题2: LuaJIT lib_io.c popen/pclose 未声明
- **症状**: `call to undeclared function 'popen'`
- **原因**: 缺少必要的头文件
- **解决**: 在 lib_io.c 中添加 `#include <unistd.h>`

#### 问题3: OpenSSL 不支持 HarmonyOS 平台
- **症状**: `Operating system: aarch64-whatever-HarmonyOS, This system (HarmonyOS) is not supported`
- **原因**: OpenSSL Configure 不识别 HarmonyOS
- **解决**: 使用 `./Configure linux-aarch64` 配置

#### 问题4: wrk Makefile 不识别 HarmonyOS
- **症状**: `struct sigaction` 仍然不完整，因为 Makefile 没有添加 POSIX 定义
- **原因**: `uname -s` 返回 "HarmonyOS"，Makefile 只处理 linux/darwin 等
- **解决**: 添加 `harmonyos` 目标支持，添加 `-D_POSIX_C_SOURCE=200112L -D_BSD_SOURCE -D_DEFAULT_SOURCE`

#### 问题5: wrk.h 缺少 signal.h
- **症状**: `struct sigaction` 不完整类型
- **原因**: wrk.h 没有包含 signal.h
- **解决**: 在 src/wrk.h 中添加 `#include <signal.h>`

### 3. 修改文件
- `Makefile`: 添加 HarmonyOS 平台支持
- `src/wrk.h`: 添加 `#include <signal.h>`

### 4. 依赖包
- LuaJIT-2.1 (内嵌)
- OpenSSL 1.1.1i (内嵌)

### 5. 编译时间
约 10 分钟

---

**编译开始**: 2026-05-21 23:00
**编译结束**: 2026-05-21 23:20
**最终状态**: built
---

**编译结束**: 2026-05-21 23:22
**最终状态**: built

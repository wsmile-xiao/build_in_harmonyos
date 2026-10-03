# DRAFT knowledge entry — radioclk 1.0.pristine: musl 无 <termio.h> 死包含 + TIOCMIWAIT ioctl 号在 aarch64/asm-generic 头中缺失

## 背景

radioclkd（DCF77/MSF/WWVB 无线电报时解码守护进程，Jonathan A. Buzzard，
2003 年 vintage C 代码）在 OHOS/musl/aarch64 上编译时的两个独立可移植性问题。
上游站点 buzzard.org.uk 已停泊，权威 pristine 源为 Debian pool 的
`radioclk_1.0.pristine.orig.tar.gz`（R39 先例路线）。

## 症状

1. `fatal error: termio.h: No such file or directory`
   —— musl 不提供 glibc 遗留头 `<termio.h>`（struct termio 是被 `<termios.h>`
   取代的 SVR3 时代接口）。
2. `error: use of undeclared identifier 'TIOCMIWAIT'`
   —— TIOCMIWAIT（等待 modem 线变化的 ioctl，驱动级支持）是 x86 侧
   `arch/x86/include/uapi/asm/ioctls.h` 定义的 0x5452；aarch64 内核 uapi 走
   `asm-generic/ioctls.h`，该表**不含** TIOCMIWAIT，musl 的 aarch64
   `bits/ioctl.h` 同样没有。

## 根因与判据

- `<termio.h>`：musl 不提供该遗留头。**注意：并非纯死包含**——r1 本机静态
  分析误判为"死包含直接删"，r2 真机编译报 19 个
  `use of undeclared identifier 'TIOCM_CD/TIOCM_CTS/TIOCM_DSR/TIOCMGET'`：
  上游代码靠 glibc 头文件链从 `<termio.h>` 间接获得 TIOCM_* modem 线宏
  （glibc 中它们经 termios 系头可见），musl 把这些宏放在 `<termios.h>`。
  正确解法是替换为 `#include<termios.h>` + `#include<sys/ioctl.h>`
  （后者补 ioctl() 原型，消除 implicit declaration 警告）。
- `TIOCMIWAIT`：编译期必须存在宏。运行期语义在 aarch64 上本就不可用
  （内核驱动基本不实现），上游自带降级路径：`WaitOnSerialChange()` 在
  ioctl 失败时返回 -1，且上游 README 文档化 `-p/--poll` 轮询模式
  （每 5ms TIOCMGET 轮询）。

## 解法（conanfile.py source() 内 replace_in_file，无 patch 文件）

1. `#include<termio.h>` → `#include<termios.h>` + `#include<sys/ioctl.h>`
   （锚点在 pristine 源中唯一）。
2. 在 include 块后追加：

   ```c
   #ifndef TIOCMIWAIT
   #define TIOCMIWAIT 0x5452
   #endif
   ```

   `#ifndef` 守卫保证 x86/glibc 环境零影响；0x5452 为该 ioctl 的历史
   Linux 值。

## 验证

- 锚点唯一性：对 pristine tarball 原文计数，`#include<termio.h>` 与
  `#include<setjmp.h>`（插入锚点）各出现 1 次。
- 真机 shadow CI（2026-10-02 r3，HarmonyOS / HongMeng 1.12.0 / aarch64）：
  全绿——conan create 成功、test_package 5 组断言全过、L0/L1/L2/L4/L5
  全 pass、L1e 破坏性反向验证确认（`test genuinely depends on radioclk`）。

## 可推广性

任何 vintage C 串口工具迁 musl 都可能同时踩这两个坑：
- 死包含 `<termio.h>` → 直接删（先全文检索确认无 termio 符号使用）；
- x86 专属 ioctl 宏（TIOCMIWAIT/TIOCMIWAIT 类）→ `#ifndef` 回退定义 +
  确认运行期失败路径有降级（轮询/报错退出），并在 notes 记录功能影响。

相关条目：E092（CMake 不识别 HarmonyOS）、E098（OHOS 缺 install 命令——
本包 Makefile install 目标同样因 `/usr/bin/install` + `/sbin` 布局被
package() 替代）。

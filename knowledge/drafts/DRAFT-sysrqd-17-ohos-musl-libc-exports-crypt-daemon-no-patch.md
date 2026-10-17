# DRAFT: OHOS musl libc 自带 crypt/daemon/syslog 等符号 + sysroot libcrypt.a —— libxcrypt 类用户零补丁适配（sysrqd 17 实证）

## 基本信息

- 来源包：sysrqd/17（archives/s/sysrqd/17）
- 阶段：linking / dependency-audit
- 严重度：1（规避误判依赖缺失）

## 错误特征

```
-lcrypt 找不到|libcrypt.so missing|crypt.h: No such file|undefined reference.*crypt|syslog.*undefined|daemon.*undefined|setpriority.*undefined
```

适配审计 libxcrypt 用户（`#include <crypt.h>` + `LDFLAGS += -lcrypt`）时，容易因
「OHOS sysroot 没有 libcrypt.so」而误判为依赖缺失、拆任务或引入源码补丁。

## 根因分析

OHOS PC 的 musl libc 把 glibc 中拆分到 libxcrypt/libutil 的历史符号直接编进了
`libc.so`。实测（DevEco SDK，`llvm-nm -D sysroot/usr/lib/aarch64-linux-ohos/libc.so`）：

- `crypt`（crypt(3)，DES/MD5/SHA crypt 实现）
- `daemon`
- `mlockall`
- `setpriority`
- `syslog`（注意与 E014「musl 未导出符号」族相反：此处已导出，链接期无问题；E014
  场景是内核 syscall 未实现，发生在运行期）

同时 sysroot 提供 `libcrypt.a`（无 libcrypt.so），上游 Makefile 的 `-lcrypt` 原样
可链（链接静态 stub 或直接落到 libc 符号），最终 NEEDED 仅 libc.so。

## 推荐方案

**方法**：nm-verify-then-link-as-is

1. 审计期不要看到「无 libcrypt.so」就拆依赖任务；先用
   `llvm-nm -D <sysroot>/usr/lib/aarch64-linux-ohos/libc.so | grep <symbol>` 核验。
2. 符号在 libc 中 → 保持上游 `-lcrypt` 不动（libcrypt.a 存在，链接不会失败）。
3. sysrqd 17 案例：零源码补丁，OHOS clang 交叉编译 + 链接一次通过。

验证命令：

```sh
llvm-nm -D "$OHOS_SYSROOT/usr/lib/aarch64-linux-ohos/libc.so" | grep -E ' crypt$| daemon$| syslog$| mlockall$| setpriority$'
ls "$OHOS_SYSROOT/usr/lib/aarch64-linux-ohos/libcrypt.a"
```

## 同族场景与边界

- 适用：crypt(3)、daemon()、syslog()、setpriority()、mlockall() 等 musl 内置符号的
  链接期审计。
- 不适用（运行期）：符号链接通过 ≠ syscall 已实现。`mlockall`/`setpriority(-19)`/
  `/proc/sysrq-trigger` 写入在真机上仍受 root/SELinux 约束（E031/E051），完整守护
  行为需真机归因，与本文（链接期结论）分层。
- 附带经验（sysrqd Makefile）：上游用 `grep|head|cut|tr` 管道从 ChangeLog 提取
  VERSION，`make VERSION=<v>` 命令行钉住可绕开 toybox 工具链依赖并保证确定性；
  上游 install 目标用 `install` 命令（OHOS 缺失，E098），package() 直接复制。

---
Status: UNMATCHED

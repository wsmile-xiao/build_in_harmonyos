# DRAFT-rdate-1.11-musl-builtin-arc4random-vestigial-bsd-header

## 一句话
libbsd 的 `bsd/stdlib.h` 兼容头在 OHOS 上是**假依赖**：configure 硬检（缺失 exit -1）+ LDADD 硬编码
`-lbsd` 双重加固，但源码唯一消费点是单个 `arc4random()`——musl 的 `<stdlib.h>` 1.2 起已内建（链接探针
rc=0），整条 libbsd 链冗余，正确解法是卸除而非适配 libbsd。

## 症状（两层）
1. configure 阶段：`ERROR: previous header not found.`（configure.ac `AC_CHECK_HEADERS([bsd/stdlib.h],[],[exit -1])`）
2. 若硬检被绕过：链接阶段 `ld.lld: error: unable to find library -lbsd`（Makefile.am LDADD 硬编码）

## 根因
- 上游（glibc 世界）默认 libbsd 提供 arc4random/getprogname/errc 等浅函数；
- musl 1.2 的 stdlib.h 已内建 arc4random 族（无需任何特性宏）；OHOS musl 实测直连可用；
- 消费点越少，整条 libbsd 依赖越假。rdate 全树消费点 = `ntp.c:287` 一次 arc4random。

## 最小复现（rdate 1.11，A 机 2026-09-25）
1. 未打补丁 configure → `checking bsd/stdlib.h usability... no` → `ERROR: previous header not found.` 退出
2. 打通头检后链接 → `unable to find library -lbsd`
3. 探针：`printf '#include <stdlib.h>\nint main(void){return (int)(arc4random()>>30);}' | clang -x c - -o p && ./p` → rc=0

## 方案（三件套补丁，见 archives/r/rdate/1.11/patches/0001）
1. configure.ac 删硬检；
2. `#include <bsd/stdlib.h>` → **真实需要的标准头**：本例 ntp.c 还要用 u_char，musl 在
   `sys/types.h` 的 `_BSD_SOURCE` 分支定义它，且 musl 不经 sys/param.h 传递（glibc 会！）——
   **必须显式 `#include <sys/types.h>`**；openrdate 未定义任何特性宏，musl features.h 自动置
   `_BSD_SOURCE`，typedef 直接可见（实测）。若上游自定义了特性宏则需补 `-D_BSD_SOURCE`；
3. LDADD 去 `-lbsd`。

## 边界
- 消费点若含 libbsd 独有函数（fparseln/dehumanize_number 等 musl 真没有的）则本条不适用，
  转 E534 兼容层工艺；
- `-D_BSD_SOURCE` 不是万能钥匙：头文件没被 include 时 define 无效（本窗第一版踩过，见 notes §2）。

## 证据
- 探针与构建日志：设备 `~/tmp/uc2/z35-rdate/`（ar4-probe.c、create-r1.log、uchar-probe.c）
- 配方：`archives/r/rdate/1.11/`（create rc=0 + 消费者 4 断言 PASS）

## 判重说明
- E534 = musl **缺**函数 → 自建兼容层（方向相反）；
- E087/E018 = HMDFS 权限/软链层（不同层）；
- 无「libbsd 假依赖卸除」既有条目 ⇒ 申报 create。

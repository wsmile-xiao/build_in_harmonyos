# DRAFT — OHOS musl libc 不传递包含 POSIX 类型（uid_t/pid_t/mode_t）

> 状态: 重新提交草稿（原提交在 20260831 知识库合入中被判"空壳"清理；根因是 .kv 的
> root_cause: > YAML 块标量格式使治理工具解析为空值，已修复格式后随 afl++-tools
> 4.40c 适配重新提交）。知识库查重结论见文末（含 20260831 批量合入后的复查）。

## 真实问题（aflplusplus 4.33c 适配实际命中）

conan create 首轮编译失败，5 个核心工具 + LLVM 插桩全部卡在头文件编译：

    include/forkserver.h:191:3: error: unknown type name 'uid_t'
    include/forkserver.h:193:3: error: unknown type name 'pid_t'
    include/forkserver.h:197:3: error: unknown type name 'mode_t'
    include/sharedmem.h:61:19: error: unknown type name 'mode_t'

根因：OHOS SDK 的 libc（musl）不像 glibc 那样通过 <unistd.h>/<stdio.h>/<fcntl.h>
传递包含 <sys/types.h> 中的 POSIX 类型定义。AFL++ 的 forkserver.h/sharedmem.h
直接使用 uid_t/pid_t/mode_t 却只 include 了自定义的 "types.h"，依赖 glibc 的
传递包含在 Linux 上侥幸编译通过；移植 OHOS 后传递包含失效，类型未定义。

## 修复（真实实施，2 个最小 patch）

patches/0001-include-forkserver.h.patch（+1 行）:
    #include "types.h"
    #include <sys/types.h>   // ← 新增：显式引入 POSIX 类型定义

patches/0002-include-sharedmem.h.patch（+1 行）: 同上。

每个补丁只加一行 #include <sys/types.h>，最小 diff，遵循 R6 与补丁最小化原则。

## 独立验证（跨版本）

同一补丁在 aflplusplus 4.33c 与 afl++-tools 4.40c 两个独立适配中均命中并修复，
证实该知识为 L1 平台真理（musl 传递包含行为差异），非单库偶发。

> 4.40c 实测（鸿蒙 PC clang，2026-09-04 §A 验证）：
> - `#include "sharedmem.h"` 单独编译报 `sharedmem.h:63:19: error: unknown type name 'mode_t'`
>   （unistd.h 在 musl 中不带 mode_t）→ 补丁 0002 必需
> - `#include "forkserver.h"` 单独编译通过（4.40c 上游新增 <unistd.h>/<fcntl.h>，
>   musl 下带出 uid_t/pid_t/mode_t）→ 补丁 0001 对 4.40c 为冗余保险项
> 结论：4.40c 命中 mode_t（sharedmem.h 无条件函数声明 afl_shm_init），补丁 0002 实锤必需。

## 复用步骤

1. 编译报 unknown type name 'uid_t'/'pid_t'/'mode_t'/'gid_t'/'off_t' 时，定位报错头文件。
2. 检查该头文件是否已 #include <sys/types.h>；若否，在首次使用 POSIX 类型的 include
   块后补丁加一行 #include <sys/types.h>。
3. 用 difflib.unified_diff 生成最小 diff，保持补丁单行增量，不整文件重写。
4. 注意区分：上游头文件若已 include <unistd.h>/<fcntl.h>，musl 下可能已带出部分
   POSIX 类型（unistd.h → uid_t/pid_t/gid_t/off_t；fcntl.h → mode_t），但 unistd.h
   不带 mode_t——逐个头文件按实际报错判定，勿照抄旧补丁。

## 验证

- conan create：PASS，5 个核心工具 + afl-cc + LLVM 插桩 pass 全部编译通过。
- test_package：5/5（VERSION + 类型尺寸 + MAP_SIZE 常量）。
- afl-cc 实机插桩：Instrumented 成功，nm 确认符号注入。
- 4.40c §A 实机：sharedmem.h 编译报 mode_t（命中），补丁 0002 应用后 conan create 通过。

## 知识库查重结论（2026-08-31 批量入库后复查，本库 540+ 正式条目）

复查方法：index.tsv 关键词粗筛 → 命中条目逐一读 root_cause 对比根因 → 全库精确搜
「传递包含/不传递/显式 include sys/types.h」零命中。

结论：无重复，可新增。近邻条目根因均不同：
- E152（musl 需显式 include time.h + _GNU_SOURCE 取 CLOCK_* 常量）— feature-macro
  门控 vs 本条类型定义传递包含失效，修复不同（加宏 vs 加 #include）
- E194（sys/types.h 的 bits/alltypes.h 文件缺失）— 文件缺失 vs 未显式 include
- E367（dlfcn.h Dl_info 需 _GNU_SOURCE）、E086（struct ucred 缺失）、E032/E033/E113
  （DIR/cchar_t/BSD 类型）— 各自不同机制/类型

## 关联条目

相关: E152、E194、E367、E032、E033、E113、E086

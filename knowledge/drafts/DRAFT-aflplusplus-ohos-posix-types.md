# DRAFT — OHOS musl libc 不传递包含 POSIX 类型（uid_t/pid_t/mode_t）

> 状态: 草稿（仅服务 aflplusplus 4.33c，待查重/提升）。知识库查重结论见文末。

## 真实问题（本轮 aflplusplus 4.33c 适配实际命中）

`conan create` 首轮编译失败，5 个核心工具 + LLVM 插桩全部卡在头文件编译：

```
include/forkserver.h:191:3: error: unknown type name 'uid_t'
include/forkserver.h:193:3: error: unknown type name 'pid_t'
include/forkserver.h:197:3: error: unknown type name 'mode_t'
include/sharedmem.h:61:19: error: unknown type name 'mode_t'
```

根因：OHOS SDK 的 libc（musl）不像 glibc 那样通过 `<unistd.h>`/`<stdio.h>`/`<fcntl.h>`
**传递包含** `<sys/types.h>` 中的 POSIX 类型定义。AFL++ 的 `forkserver.h`/`sharedmem.h`
直接使用 `uid_t`/`pid_t`/`mode_t` 却只 include 了自定义的 `"types.h"`，依赖 glibc 的
传递包含在 Linux 上侥幸编译通过；移植 OHOS 后传递包含失效，类型未定义。

## 修复（本轮真实实施，2 个最小 patch）

`patches/0001-include-forkserver.h.patch`（+1 行）:
```c
#include "types.h"
#include <sys/types.h>   // ← 新增：显式引入 POSIX 类型定义
```

`patches/0002-include-sharedmem.h.patch`（+1 行）: 同上。

每个补丁只加一行 `#include <sys/types.h>`，最小 diff（各 10 行），遵循 R6（只改源文件
不改生成文件）与补丁最小化原则（tre PR 教训）。

## 复用步骤

1. 编译报 `unknown type name 'uid_t'/'pid_t'/'mode_t'/'gid_t'/'off_t'` 时，定位报错头文件。
2. 检查该头文件是否已 `#include <sys/types.h>`；若否，在首次使用 POSIX 类型的 include
   块后补丁加一行 `#include <sys/types.h>`。
3. 用 `difflib.unified_diff` 生成最小 diff，保持补丁单行增量，不整文件重写。

## 验证

- `conan create`：PASS，5 个核心工具 + afl-cc + 10 个 LLVM 插桩 pass 全部编译通过。
- test_package：5/5（VERSION + u8/u32/u64 类型尺寸 + MAP_SIZE 常量）。
- afl-cc 实机插桩：`[+] Instrumented 1 locations`，nm 确认 `__afl_area_ptr` 符号注入。

## 知识库查重结论

- **E194**（`sys/types.h` 文件本身缺失）：其根因是 OHOS SDK musl 头文件集**不完整**、
  缺少 `bits/alltypes.h`，属「无法修复，标记平台限制」；本轮 `sys/types.h` 文件**存在**，
  只是上游头文件未显式 include，属「可修复，加 include」——非重复条目。
- **E032**（`unknown type name 'DIR'`）、**E033**（`cchar_t`）、**E113**（`u_int`/`u_long`/
  `u_char`/`caddr_t` 等 BSD 类型）：均为**特定头文件/特定类型**的模式，均不覆盖
  `sys/types.h` 中的 POSIX 类型（uid_t/pid_t/mode_t）传递包含问题。
- 知识库无「musl libc 不传递包含 POSIX 类型，需显式 `#include <sys/types.h>`」的既有条目，
  本草稿为新增候选（L1 平台真理，影响所有有此移植 bug 的 C 库）。

## 关联条目

- 相关: E032（`DIR`）、E033（`cchar_t`）、E113（BSD 类型）、E194（`sys/types.h` 文件缺失，同类但不同根因）

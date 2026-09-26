# DRAFT-libxdp-1.6.3-vendored-kernel-tools-compiler-guard

**一类问题**：项目内 vendored 的 Linux **kernel-tools** 头（`tools/include/linux/compiler_types.h` +
`compiler-gcc.h`）在 **OHOS/bionic** sysroot 上被“从旁路”拉起：bionic 的 `<linux/stddef.h>` 会
`#include <linux/compiler_types.h>`，而 vendored 头因 `-I` 顺序胜出，其无条件的
`#include <linux/compiler-gcc.h>` 触发 `_TOOLS_LINUX_COMPILER_H_` 守卫报错。glibc 宿主不触发，
故是 **OHOS/交叉专属** 的一类。

## 使用说明（怎么判定 + 怎么修）

1. **判定**：编译任何引用 vendored `linux/*.h` 的用户态对象时报
   `"Please don't include <linux/compiler-gcc.h> directly, include <linux/compiler.h> instead."`。
2. **定位**：确认 include 链是 `<sysroot>/linux/stddef.h`（或 `linux/types.h` 链）→ **vendored**
   `linux/compiler_types.h` → vendored `linux/compiler-gcc.h`；用 `cc -H` 看解析路径：
   ```sh
   printf '#include <linux/stddef.h>\n' | cc -I<vendored headers> -H -E -xc - -o /dev/null
   ```
3. **修复（平台无关、保持上游语义）**：把 `compiler_types.h` 里的
   `#ifdef __GNUC__ / #include <linux/compiler-gcc.h> / #endif` 块移到 `linux/compiler.h`
   （在其 `#define _TOOLS_LINUX_COMPILER_H_` 之后）。`compiler.h` 本就是唯一正规入口。
4. **不要**用平台宏（`__OHOS__`）分支（违反 R8），也不要简单删掉 `compiler-gcc.h`（会丢宏）。

## 适用范围

- 所有把 Linux `tools/include`（kernel-tools）头目录整体 `-I` 到源码最前的项目：xdp-tools（libxdp）、
  bpftool、perf，及从内核树 tools/ 取头的移植；
- 触发前提：目标 libc 的 `linux/stddef.h` 会 include `linux/compiler_types.h`（bionic/OHOS 满足），
  且 vendored 头在 include 顺序上先于 sysroot 的 `linux/`。

## 输入输出定义

| | |
|---|---|
| 输入 | vendored `headers/linux/{compiler.h,compiler_types.h,compiler-gcc.h}`；目标 sysroot |
| 输出 | 任意 TU（含被 sysroot 头从旁路拉起的场景）都能无错包含 `<linux/compiler_types.h>`；被 `linux/compiler.h` 正规引入时仍得到完整宏 |
| 成功判据 | `printf '#include <linux/stddef.h>\n' | cc -I<headers> -E -xc - -o /dev/null` 退出码 0 |

## 示例

libxdp 1.6.3 的 `libxdp.c` 在 WSL 交叉（SDK sysroot）首次编译即触发；
补丁 `patches/0001-headers-linux-compiler.h.patch` +
`patches/0002-headers-linux-compiler_types.h.patch` 修复。

## 查重差异表（与最相近的既有条目逐条比）

| 维度 | E119（sockaddr_storage 重定义） | 本条 |
|---|---|---|
| 头冲突对象 | `linux/socket.h` vs `sys/socket.h` 的 `struct sockaddr_storage` | vendored `compiler_types.h` vs `compiler-gcc.h` 的 `_TOOLS_LINUX_COMPILER_H_` 守卫 |
| 触发链 | `linux/netlink.h` → `linux/socket.h` | sysroot `linux/stddef.h` → `linux/compiler_types.h` |
| 解法 | include 自守卫 + typedef `__kernel_sa_family_t` | 把 `compiler-gcc.h` 的包含上移到 `compiler.h` |
| 关系 | `similar_to: E119`（同属“OHOS sysroot 与前缀头重叠”族，但冲突对象与解法都不同） | — |

- `compiler_types`/`compiler-gcc`/`_TOOLS_LINUX_COMPILER_H_` 词边界在 `knowledge/{graph,drafts,doc}` **0 命中**（本次实测）。

## 验证证据

```
# WSL 交叉修复前
In file included from ../../headers/linux/bpf.h:11:
In file included from .../sysroot/usr/include/linux/types.h:23:
In file included from .../linux/posix_types.h:21:
In file included from .../linux/stddef.h:19:
In file included from ../../headers/linux/compiler_types.h:36:
../../headers/linux/compiler-gcc.h:3:2: error: "Please don't include <linux/compiler-gcc.h> directly, include <linux/compiler.h> instead."

# 修复后
CC staticobjs/libxdp.o      # 退出码 0
```

- 日志：`logs/021-make-libxdp.log`（失败）、`logs/021e-make-libxdp-fixed3.log`（通过）、
  WSL 最终 `logs/025e-conan-create-cross.log` EXIT=0。
- 补丁：`archives/l/libxdp/1.6.3/patches/0001-headers-linux-compiler.h.patch`、`0002-headers-linux-compiler_types.h.patch`。

## 平台侧修法建议（若有）

OHOS/bionic 的 `linux/stddef.h` 与 Linux glibc 的 `linux/stddef.h` 行为不同（会引入 compiler_types.h），
建议在 SDK 头差异文档中标注，便于内核工具类项目预判。

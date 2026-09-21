# DRAFT-truncate-via-tmpfile-ohos-ftruncate — 文件截断 tmpfile 技巧在 OHOS 只读 /tmp 上失败（源码级 ftruncate 修复）

> **Contributor**: codex | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium | **Category**: ohos / filesystem / portability / source-patch
> **Audience**: 任何在 OHOS 上用 `tmpfile()+freopen()` 技巧实现文件截断（shrink）的库

## Scope

纯 ANSI C 没有 truncate API，部分可移植库用「`tmpfile()` + `freopen(NULL, "w+b", f)`」技巧实现文件收缩。OHOS `/tmp` 只读导致 `tmpfile()` 返回 NULL，整条截断流程失败。本文给出 POSIX 平台改用 `ftruncate(2)` 的源码级修复，并说明与既有 E272（LD_PRELOAD shim）的适用边界。

## 背景

- pforth 2.0.1 的 `csrc/stdio/pf_fileio_stdio.c` 中 `TruncateFile()` 用如下技巧收缩文件：
  1. `tmpfile()` 建临时文件；
  2. 把原文件前 `Newsize` 字节复制进临时文件（`CopyFile`）；
  3. `freopen(NULL, "w+b", File)` 截断原文件；
  4. 再从临时文件复制回原文件。
- OHOS 真机首跑：`make test` 的 `t_file.fth` 中 `RESIZE-FILE` 收缩 4 个断言失败
  （`90 passed, 4 failed`），日志 `INCORRECT RESULT: T{ 37. FID2 @ RESIZE-FILE -> 0 }T`。
- 实测根因：`touch /tmp/x → Read-only file system`（erofs），`tmpfile()` 返回 NULL，
  `TruncateFile` 直接返回 error（`THROW_RESIZE_FILE`）。
- 注意区分：**扩展（extend）**走 `ExtendFile`（`fwrite` 填 0），**不受影响**；
  只有**收缩（shrink）**走 `TruncateFile` 失败。

## 修复方式（源码级 ftruncate）

```c
#include <limits.h>   /* For LONG_MAX */

#if defined(__unix__) || defined(__APPLE__) || defined(__OHOS__)
#include <unistd.h>   /* ftruncate(), fileno(), off_t */
#define PF_HAVE_FTRUNCATE (1)
#endif

static bool_t TruncateFile( FileStream *File, long Newsize )
{
    bool_t Error = TRUE;
#if defined(PF_HAVE_FTRUNCATE)
    if( ftruncate( fileno( File ), (off_t)Newsize ) == 0 )
    {
        Error = FALSE;   /* POSIX 原地截断，无需临时文件 */
    }
    else
#endif
    if( fseek( File, 0, SEEK_SET ) == 0 )
    {
        /* 原 tmpfile()+freopen() 回退，仅供非 POSIX（嵌入式）平台 */
        ...
    }
    return Error;
}
```

要点：
1. 平台守卫 `__unix__ || __APPLE__ || __OHOS__`，保留原逻辑作为非 POSIX 回退；
2. `fileno`/`ftruncate`/`off_t` 需要 `-D_DEFAULT_SOURCE`（musl）；pforth 的 Makefile
   已带 `-D_DEFAULT_SOURCE -D_GNU_SOURCE`，无需额外处理；
3. 补丁后真机二跑 `t_file.fth` 从 90/4 变为 **94/0**，上游合计 **346/346**。

## 验证

```sh
# 1) 确认 /tmp 只读（根因）
touch /tmp/probe 2>&1 || echo "Read-only file system"
# 2) 确认源码用 tmpfile+freopen 做截断
grep -nE "tmpfile|freopen" csrc/stdio/pf_fileio_stdio.c
# 3) 补丁后 OHOS 真机重跑（pforth 实测）
CI_PACKAGES="archives/p/pforth/2.0.1" zsh ci/conan/build_and_test.sh
```

## 与既有条目的关系

- **E272**（`tmpfile()` EACCES → LD_PRELOAD shim）：针对「真正需要临时文件」的场景
  （binutils libctf `ctf_link_write`），且源码不可改（交叉工具链），故用测试阶段
  `tmpfile-shim.so` 注入。本条目针对「tmpfile 仅作截断中间缓冲」的场景，**ftruncate
  是更干净的源码修复**，无运行时 LD_PRELOAD 依赖，且覆盖生产 package。
- **E002**（临时目录不可写）：通用只读 `/tmp` 背景；本条目是其在「文件截断」场景下的
  具体化与源码级解法。

## 不能宣称的结论

- ❌ "OHOS 不支持文件截断 / RESIZE-FILE"（实际是 /tmp 只读导致 tmpfile 失败，ftruncate 可解）。
- ❌ 在可改源码的库上用 LD_PRELOAD shim 就声称"已闭环"（shim 不进入生产 package）。

## Source

- Package: `archives/p/pforth/2.0.1`
- 补丁: `patches/0001-resize-file-use-ftruncate-on-posix.patch`
- 证据: 真机 shadow CI job `pforth-2.0.1-shadow-20260920-143514`（首跑 90/4 → 补丁二跑 94/0，exit 0）

# E648 草稿：musl realpath() 全路径存在性校验 vs glibc 最长前缀解析

> 状态：草稿（DRAFT，待人工审核）｜来源：scalpel 1.60-git20240110.6960eb2（nolaforensix/scalpel-1.60 commit 6960eb2）OHOS aarch64 适配（2026-09-21）

## 问题

设备（OHOS/musl）上运行按正常方式构建的 scalpel，`-o <不存在的输出目录>` 必然报：

```
ERROR: You have attempted to use a non-empty output directory. In order
       to maintain forensic soundness, this is not allowed.
Aborting.
```

同一命令行在 Debian（glibc）上工作正常。加 `-v` 后能看到真正的异常点：

```
Output directory: " domain string"        ← 未初始化栈内存
Coverage maps directory: " domain string"
```

## 根因

1. scalpel 的 `convertFileNames()`：

```c
realpath(state->outputdirectory, fn);              /* 返回值被忽略 */
strncpy(state->outputdirectory, fn, MAX_STRING_LENGTH);
```

2. POSIX-2008 起，`realpath()` 在路径分量不存在时的行为在两大 libc 上**分歧**：
   - glibc：解析"最长存在前缀"，把不存在的尾部拼回后**成功返回**；
   - musl（OHOS）：严格存在性校验，返回 **NULL 且不触碰 resolved 缓冲区**。
3. scalpel 输出目录按 forensic soundness 语义**本来就不该预先存在**，所以
   musl 下每次正常使用都命中：`fn` 保持未初始化栈垃圾 → 被拷进 outputdirectory
   → `outputDirectoryOK()` 对垃圾路径报"目录非空"。报错文案与真实故障无关。

## 方案（补丁式，平台中立）

`patches/0002-realpath-nonexistent-output-dir.patch`：对两次 realpath 返回值判空，
失败时保留原路径。**不要**写 `#ifdef __OHOS__` 之类平台宏（PF5/上游审查拦截）。

## 快速探针

```sh
# musl 下返回 NULL（errno=ENOENT），glibc 下返回 "/nonexistent/x"
cat > rp.c <<'EOF'
#define _POSIX_C_SOURCE 200809L
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
int main(void){ char b[4096]; char*r=realpath("/nonexistent/x",b);
  printf("r=%s buf=%s errno=%d\n", r?r:"(NULL)", b, errno); return 0; }
EOF
clang rp.c -o rp && ./rp
```

## 关联

- 同任务沉淀的另一独立缺陷见 E649（make 命令行 CC 丢弃目标级 `+=` 追加）。
- 上游回归建议：`feedback/upstream-backlog.md`（convertFileNames 判空）。

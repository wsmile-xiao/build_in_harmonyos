# DRAFT: OHOS 的 paths.h 不提供 _PATH_MEM/_PATH_KMEM 宏 ⇒ 须用特征守卫回退字面量

- **触发实例**：memdump 1.01 适配（任务 #8788，构建机 B，2026-09-27，worktree `~/qzy/主理-74-memdump-1.01`）
- **错误签名**：`memdump.c:338:24: error: use of undeclared identifier '_PATH_MEM'`（另两枚在 `:360:13` 与 `:414:40` 报 `_PATH_KMEM`）
- **类别**：musl, libc-header, macro-constant, compile-error
- **严重度**：2（编译期确定性阻塞，形状固定；且两条"看着能绕"的捷径实测都带病）

## 症状

```text
memdump.c:338:24: error: use of undeclared identifier '_PATH_MEM'
memdump.c:360:13: error: use of undeclared identifier '_PATH_KMEM'
memdump.c:414:40: error: use of undeclared identifier '_PATH_KMEM'
```

上游 `memdump.c` 在 SVR5/4 预处理分支里**无条件**引用这两个名字（原文见本包补丁的上下文行）。
它们不是 libc 函数、也不是符号，而是 `<paths.h>` 里的**字符串字面量宏**。

一手判据（不是"漏 include"，而是"宏根本没导出"）—— 本窗与 W4 审计棒各独立跑一次、两读一致：

```text
printf "#include <paths.h>\nint main(){return 0;}\n" > ~/tmp/uc2/p.c
clang --target=aarch64-unknown-linux-ohos -E -dM ~/tmp/uc2/p.c | grep -c "_PATH_"        # = 24
clang ... -E -dM ~/tmp/uc2/p.c | grep -cE "_PATH_MEM|_PATH_KMEM"                          # = 0
样例导出项：_PATH_BSHELL _PATH_CONSOLE _PATH_DEFPATH _PATH_DEV _PATH_DEVNULL ...
```

## 根因

OHOS 工具链用的 libc 其 `<paths.h>` 只导出 24 枚 `_PATH_*` 宏，设备路径类的 `_PATH_MEM`/`_PATH_KMEM`
不在其中（本条不宣称别家 libc 的内容，只申报本机实测）。于是：预处理阶段没有这两个宏名 ⇒
编译到引用处就是**未声明标识符**，属"头文件宏常量层"的缺失。

## 解决方案

照上游**自己已有的写法**补，而不是照平台身份补：上游 `SUNOS5` 分支体内就是
`#define _PATH_MEM "/dev/mem"` 这种内联定义 ⇒ 本包按同样的形状加**特征守卫**（恰 6 行新增）：

```c
#ifndef _PATH_MEM
#define _PATH_MEM "/dev/mem"
#endif
#ifndef _PATH_KMEM
#define _PATH_KMEM "/dev/kmem"
#endif
```

要点：
1. 守的是「**宏不存在**」这个可探测特征，不是「平台是 OHOS」这个身份 ⇒ glibc/BSD 侧守卫不触发，跨 libc 行为不变；
2. 补丁新增行不含平台宏 ⇒ 过静态审查 **PF5**（实测 `grep -c "^+.*__OHOS__" patches/*.patch` = 0）；
3. ⛔ 两条"看着更省事"的捷径，本包实测否决，记录防再试：
   - `DEFS=-DSUNOS5`：会让上游该分支连带改变其它行为面 —— 等于换平台语义，不是补宏；
   - 在 conanfile 里用命令行 define 注入宏值：值必须带引号，而引号要穿透 `make` 与 shell 两层，
     实测引号丢失后宏值不再是字符串字面量（编译能过、运行时路径是错的）。

## 与既有条目的区别

| 层面 | 覆盖它的条目 | 与本条的关系 |
|---|---|---|
| libc **函数/变量符号**缺失（`getprogname`、`program_invocation_name` 等） | 仓内已有 musl 符号层草稿与 E203 | 不同层：那些是链接/符号面，本条是**预处理阶段的宏名** |
| 未实现 **syscall** ⇒ SIGSYS 崩溃 | `E051` | 不同层：本包错误发生在编译期，进程根本没跑起来 |
| **socket 结构与常量**差异 | 图谱里的 socket 层条目 | 不同层，且不涉及 `paths.h` |
| 宏**在**但缺 include / include 路径不对 | include 面条目 | 相反：本条是宏**不在**，加 include 不解决 |
| 设备节点缺失（`/dev/mem`、`/dev/kmem` 在本机 ENOENT 而非 EACCES/EPERM） | 无（本包另有一条一手读数） | 那是**运行期能力面**问题，决定交付口径；与本条的编译期宏缺失是两件事 |

一手检索证据（⛔ 只看标题猜，均读原文）：`grep -rl '_PATH_MEM' knowledge/` **0 命中**；
`grep -rl 'paths.h' knowledge/` 仅命中 `knowledge/graph/E129.kv`，读原文确认它讲的是
HMDFS 上 `umask 077` 与 `mktemp -d` 的目录权限（处方＝`umask 022`/`TMPDIR`），与本条不同因不同处方。
第二读：W4 r1 审计棒独立检索 `_PATH_MEM|_PATH_KMEM` 与处方层 `#ifndef .*_PATH_|字面量回退` 均 0 命中。

## 验证

```bash
# ① 宏面缺失可复算
clang --target=aarch64-unknown-linux-ohos -E -dM <(printf '#include <paths.h>\n') | grep -cE '_PATH_MEM|_PATH_KMEM'   # 期望 0
# ② 补丁形状
grep -c '^+.*__OHOS__' archives/m/memdump/1.01/patches/0001-memdump.c.patch    # 期望 0（PF5）
sed -n '14,19p' archives/m/memdump/1.01/patches/0001-memdump.c.patch           # 期望恰两枚 ifndef/define/endif 守卫
# ③ 不打补丁必然报编译期未声明标识符（本包一手：notes.md:60-62 三行原文）
```

本包实测：①=0、②=0、③三行错误原文已入 `notes.md`「问题 3」节，打补丁后 21 条断言全通过。
⚠ 交付口径另受一条**运行期**限制约束：本机 `/dev/mem`、`/dev/kmem` 均 `ENOENT`（不是 `EACCES`/`EPERM`）
⇒ 本包功能面在平台级缺失，交付只申报"编译 + 静态 + 真实失败形态"断言，⛔ 宣称内存转储可用。

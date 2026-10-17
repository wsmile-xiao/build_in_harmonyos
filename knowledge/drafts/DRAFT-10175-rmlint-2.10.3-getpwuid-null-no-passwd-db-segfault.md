# DRAFT-10175：OHOS 无 passwd DB——getpwuid NULL 解引用 segfault、信号处理器死循环与 baduid 污染（rmlint 2.10.3）

- **触发实例**：rmlint 2.10.3 适配（2026-09-25，任务 10175，B 机真机）
- **错误签名**：`Aborting due to a fatal error. (signal received: Segmentation fault)`（重复数百万次）/ `chown (null)` / `0 are duplicates`
- **类别**：ohos / libc / runtime / testing
- **严重度**：1（运行期崩溃 + 测试语义失真双重阻塞）

## 症状（全部实测复现）

1. `rmlint --version`/`--help` 正常，但**任何扫描**启动即崩；stderr 被重定向到文件时，
   6 秒写出 27MB、12 分钟写出 2.9GB 的重复崩溃消息（信号处理器返回后内核重交付，SA_RESETHAND
   预期的"处理一次即默认终止"未发生——OHOS 内核实测行为，机制未深究）。
2. 修复崩溃后，默认 finder 集下两个内容相同的文件报 `Bad UID(s): chown (null)`、
   `0 are duplicates`、退出码 0——重复检测被 baduid finder 完全抢走。
3. `rmlint 2.x` 扫描成功恒返回 0（`lib/cmdline.c rm_cmd_main` 仅 BUG/中断/EQUAL 模式返回非 0）。

## 根因

- OHOS 应用 uid（如 20001006）**在 passwd DB 无条目** ⇒ `getpwuid(geteuid())` 合法返回 NULL。
  `lib/utilities.c rm_util_get_groupname()` 检查了 `getgrgid` 的结果却**直接解引用**
  `user->pw_gid`（同文件 `rm_util_get_username()` 有检查——明显疏漏）。
- 崩点在 **pretty formatter 的 INIT 回调**（`rm_fmt_head → rm_util_get_username/get_groupname`），
  早于任何扫描输出——这是打点二分（main→cmd_main→fmt_set_state→handler）定位的。
- 无 passwd DB ⇒ baduid finder 对**每个文件**触发 ⇒ 默认类型集下 dupe finder 永远拿不到文件。

## 最小修复

1. 补丁（`patches/0001-lib-utilities-null-check-getpwuid.patch`，portability，无平台宏）：

```c
 char *rm_util_get_groupname(void) {
     struct passwd *user = getpwuid(geteuid());
+    if(!user) {
+        /* getpwuid(3) is allowed to return NULL ... */
+        return NULL;
+    }
     struct group *grp = getgrgid(user->pw_gid);
```

2. 消费者测试/CI 调用加 `-T df`（只开 duplicate finder），绕开 baduid 污染。
3. 测试断言**报告文本**（孪生路径、"are duplicates in" 汇总行），不断言退出码。

## 诊断方法（gdb 被禁的环境）

OHOS 禁 ptrace ⇒ gdb batch 无法 attach。改用：调试副本（~/tmp 下 cp 源码）+ fprintf(stderr)
逐层打点（main → rm_cmd_main → rm_fmt_set_state → 各 handler）+ 用构建目录缓存
`_scons_env`/`generators` 增量重编（SCons 项目每次 <1 分钟）。

## 适用边界

- 适用于**一切**调用 `getpwuid/getgrgid/getpwnam` 的包（用户名显示、属主检查、quota 工具、
  "bad uid" 类 finder）。OHOS 侧该行为是平台事实，不是缺陷。
- 同场实测另一平台事实：psutil 7.2.2 无法为本平台编译（sysroot `linux/socket.h:23`
  `sockaddr_storage` 与 musl 定义冲突，`psutil/arch/linux/net.c` 首错）⇒ 依赖 psutil 的
  pytest 套件在本平台**收集期即不可达**。

## 关联

- 配方补丁：`archives/r/rmlint/2.10.3/patches/0001-lib-utilities-null-check-getpwuid.patch`
- 兄弟知识：DRAFT-10175-RMLINT-SCONS-SANDBOX-BOOTSTRAP-ENV-INLINE

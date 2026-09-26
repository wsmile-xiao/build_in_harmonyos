# DRAFT-mairix-0.24-ohos-musl-getpwuid-app-uid-no-passwd：OHOS musl 应用 uid 无 passwd 条目，`getpwuid()` 恒 NULL 使依赖工具致命退出

> Contributor: sunjunyang | Status: Draft | Updated: 2026-09-21
> Source: mairix 0.24 适配（本配方 PR），触发点 `dotlock.c` 建库锁路径
> 对应：`knowledge/drafts/DRAFT-mairix-0.24-ohos-musl-getpwuid-app-uid-no-passwd.kv`

## 现象

工具在真机上任何"建库/加锁"操作立即退出，stderr 仅一行：

```console
$ mairix -f mairixrc          # 建索引（内部 dotlock_database()）
getpwuid: Not supported
（exit 1）
```

编译期毫无征兆——`getpwuid` 在 musl 里存在、能链接、能调用，只是**运行期
对应用 uid 恒返回 NULL**。

## 根因

OHOS 上应用进程跑在专用 app uid（如 20020100）下，`/etc/passwd` 没有这个
uid 的条目，musl 的 `getpwuid()`/`getpwnam()` 因此返回 NULL。桌面 Linux
惯例代码把 getpwuid 失败当致命错误：

```c
pw = getpwuid(getuid());
if (!pw) {
    perror("getpwuid");
    exit(1);            /* ← 平台上 100% 走到这里 */
}
```

典型触点：① NFS 安全的 dotlock 锁文件（把 `pw_name` 写进锁信息文件作
诊断，mairix/tdl 风格）；② `$HOME` 未设时用 passwd 推断家目录；
③ whoami 类身份打印。注意区分：**先查 `getenv("HOME")` 的代码不受影响**
（mairix 的 expandstr.c 就是这种），只有"passwd 失败即退出"的分支致命。

## 方案（推荐 ①）

**① static fallback 结构体补丁（最小侵入）**

先确认 pw 结果只用于**诊断性输出**（锁信息文件、日志、提示语），不参与
权限/路径语义，然后：

```c
pw = getpwuid(getuid());
if (!pw) {
    /* OHOS musl: app uids have no passwd entry, so getpwuid() fails.
     * pw_name is only written into the lock info file for later
     * diagnostics -- fall back to a static name instead of dying. */
    static struct passwd fallback_pw;
    static char fallback_name[] = "unknown";
    fallback_pw.pw_name = fallback_name;
    pw = &fallback_pw;
}
```

mairix 的锁机制（link() 竞争检测 + 锁信息文件）**完整保留**，只是诊断行
的用户名固定为 "unknown"。

**② 环境变量绕开（仅限 HOME 推断场景）**

```sh
export HOME=/storage/Users/currentUser USER=<账号>
```

只对"HOME 未设才调 getpwuid"的代码有效；锁文件场景没有绕法，必须走 ①。

## 禁止动作

1. **伪造 uid / LD_PRELOAD 劫持 getpwuid**：uid 体系是平台安全边界，
   掩盖真实差异且产物不可信。
2. **禁用锁机制绕过**：dotlock 防并发建库损坏，禁锁把数据完整性问题
   推迟到运行期；正确做法是回退 pw_name 后保留锁。

## 验证

带补丁产物真机实测：mairix 建库成功生成 database 文件；上游 35 个
test-spec 全部可执行（此前 100% 秒死）；消费者端到端测试（建索引→检索→
断言）通过。

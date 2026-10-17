# DRAFT：沙箱里跑不了 session bus 的测试 —— 不许删、不许 SKIP，白名单要以「数量+身份」为判据

> 状态：草稿（待知识库主编 promote）
> 来源：libgsystemservice 0.3.0 适配，`archives/l/libgsystemservice/0.3.0`
> 类别：testing / sandbox-limitation / false-pass / allowlist-semantics / dbus

## 一、现象：有一个测试程序在这台机器上**根本起不来**

`libgsystemservice` 的 `libgsystemservice/tests/meson.build` 注册了 3 个测试程序：

```meson
test_programs = [
  ['config-file',  [config_file_resources], deps],   # 9 个用例
  ['peer-manager', [],                      deps],   # 2 个用例
  ['service',      [],                      deps],   # 2 个用例
]
```

其中 `peer-manager` 的 fixture 第一件事就是拉一条**私有 session bus**：

```c
fixture->bus = g_test_dbus_new (G_TEST_DBUS_NONE);
g_test_dbus_up (fixture->bus);
```

`g_test_dbus_up()` 会 fork 一个 `dbus-daemon`，把 `--print-address` 的输出从管道
读回来当作总线地址，daemon 在 **AF_UNIX socket** 上监听。

在 OHOS worker 上这条路两头都断：

| 前提 | OHOS 上 | 依据 |
| --- | --- | --- |
| 能 `bind()` 一个 AF_UNIX socket | **不能**，`Operation not permitted` | `archives/d/dbus/1.14.10.2/manifest.yaml` |
| PATH 里有 `dbus-daemon` | **没有**（已发布的 `dbus/1.14.10` 只构建客户端库；`dbus/1.14.10.1` 才加 `bin/dbus-daemon`） | `archives/d/dbus/` 各版本 recipe |

所以 `peer-manager` 在 OHOS 上**必然失败**。这是平台限制，不是适配缺陷：同一个
配方在允许 AF_UNIX、PATH 里有 `dbus-daemon` 的 Linux 主机上，该程序通过。

## 二、两种直觉反应，两种错法

### 错法 A：「跑不起来就别跑了」——删掉 / SKIP

从 `test_programs` 里删一条，或者给它加个 SKIP。**退出码立刻变成 0**，报表干净。

代价：适配的目标是让库在 OHOS 上跑对，不是让报表好看。少注册一个程序 = 少一份
回归保护，而且 rule4 会判「上游测试少报」。

### 错法 B：「允许它失败，但要求失败原因是 X」——把失败文本当门禁

这个更隐蔽，因为它看起来更严谨：既然失败是已知的，那就断言「失败信息里必须出现
某某字符串」——否则就抛异常。问题在于 **GLib 在这条路上有两条给出完全不同结果的
失败路径**。读 GLib 2.84 的 `gio/gtestdbus.c`：

```c
static void
start_daemon (GTestDBus *self)
{
  const gchar *argv[] = {"dbus-daemon", "--print-address", "--config-file=foo", NULL};
  ...
  g_spawn_async_with_pipes_and_fds (NULL, argv, NULL,
                                    G_SPAWN_DO_NOT_REAP_CHILD |
                                    G_SPAWN_SEARCH_PATH |
                                    G_SPAWN_LEAVE_DESCRIPTORS_OPEN,
                                    ..., &error);
  g_assert_no_error (error);                     /* ← 路径 1 */

  _g_test_watcher_add_pid (self->priv->bus_pid);

  /* Read bus address from pipe */
  channel = g_io_channel_unix_new (pipe_fds[0]);
  ...
  g_io_channel_read_line (channel, &self->priv->bus_address, NULL, &termpos, &error);
  g_assert_no_error (error);                     /* ← 路径 2 */
  self->priv->bus_address[termpos] = '\0';
  ...
}
```

- **PATH 里没有 `dbus-daemon`** → 走到路径 1 的 `g_assert_no_error (error)`，
  进程 **abort**，文本是
  `Failed to execute child process “dbus-daemon” (No such file or directory)`。
- **有 `dbus-daemon`，但 socket bind 被沙箱拒** → `g_spawn_*` 自己成功了，
  daemon 起来又立刻死掉；问题出在后面读地址那一行（路径 2 附近，地址拿不到时
  后面的 `bus_address[termpos]` 并没有等价的兜底）。失败文本完全是另一套，
  甚至可能直接段错误（`Test killed by SIGSEGV`）。

**结论：这条路上的失败文本不是稳定契约。** 把它写进硬断言，迟早会遇到
「真实回归被放过」（假阴性）或「平台限制因为措辞变化把构建打红」（假阳性）——
两种都会让人不再信任这条断言。

## 三、正确做法：声明 + 「数量 + 身份」白名单

### 3.1 上游套件保持原样

不删程序、不加 SKIP、不用 `--no-suite` 过滤。它照常构建、照常执行，失败如实
留在汇总块里。

### 3.2 判据放在汇总块，不在退出码

`meson test` 的退出码 0 只说明「没有失败」；SKIP 与「`test()` 根本没注册」同样
得 0。真正的判据是 `<builddir>/meson-logs/testlog.txt` 末尾的汇总块：

```
Ok:                    2
Expected Fail:         0
Fail:                  1
Unexpected Pass:       0
Skipped:               0
Timeout:               0
```

### 3.3 白名单钉「数量 + 身份」，不钉文本

配方里把三组常量分开写，语义各不相同：

```python
UPSTREAM_TEST_PROGRAMS    = 3                              # 上游注册了几个
REQUIRED_PASSING_PROGRAMS = ("config-file", "service")     # 必须通过的
SANDBOX_BLOCKED_PROGRAMS  = ("peer-manager",)              # 声明受阻的
```

硬条件：

| 条件 | 挡住什么 |
| --- | --- |
| `Timeout` == 0 且 `Unexpected Pass` == 0 | 挂住 / 意外的「通过」 |
| `Fail` ≤ `len(SANDBOX_BLOCKED_PROGRAMS)` | 多出来的失败 = 真实回归 |
| 出现失败时，失败程序名必须**就是**已声明的那个 | 真实回归伪装成已声明的平台限制 |
| `Ok` ≥ `len(REQUIRED_PASSING_PROGRAMS)` | 套件被静默截断 |
| 必须通过的程序名必须出现在日志里 | 用例根本没被注册 |
| 汇总块读不到 → 抛异常 | 「读不到结论」不等于「结论是好」 |

失败文本只降级为**诊断**：命中已知标记打 info，没命中打 warning，不据此判定成败。

### 3.4 口径写两个数

body / notes / MANIFEST 里一律给出**程序数**与**用例数**两个口径，并写明受阻的
那个程序**为什么**受阻、以及「换到条件满足的机器上即可通过」的判据：

> 上游 3 个程序 / 13 个用例；本平台执行集 3/3（100%）；
> 其中 2/3 程序通过、11/13 用例通过（程序口径 66.7%、用例口径 84.6%）。
> `peer-manager` 因需要私有 session bus（AF_UNIX bind + `dbus-daemon`）在本平台
> 必然失败，属于平台沙箱限制，已在 `manifest.yaml` 的
> `upstream_unrunnable_on_platform` 一节与 notes.md 中如实声明。

## 验证命令

```bash
# 1) 是不是「需要 bus」这一类失败
grep -n 'g_test_dbus_up\|g_test_dbus_new' <src>/tests/*.c

# 2) 沙箱事实（确定性限制，不是网络抖动）
grep -n 'AF_UNIX\|Operation not permitted' archives/d/*/*/manifest.yaml

# 3) 平台有没有 dbus-daemon —— 这条决定失败走哪条路，文本因此不稳定
command -v dbus-daemon; echo "exit=$?"      # 缺失 → 路径 1 的 g_assert_no_error abort

# 4) 判据在汇总块
meson test -C <builddir>
sed -n '/^Ok:/,/^Timeout:/p' <builddir>/meson-logs/testlog.txt
#   → Ok: 2 / Fail: 1        ← Ok 只有 2，不是 3

# 5) 反向对照：删掉那个程序，退出码立刻 0 —— 这就是「假通过」长什么样
#    （仅用于理解语义，不要真的这么做）
```

## 禁止策略

| 禁止 | 原因 | 后果 |
| --- | --- | --- |
| 因为跑不起来就把测试从 `test_programs` 里删掉 | 减少覆盖 + 退出码变 0 的假通过 | rule4 判少报，永久丢掉回归保护 |
| 用 SKIP / `--no-suite` 把它过滤掉 | SKIP 与「真跑过并通过」在报表上被抹平 | 伪造通过率，评审判不实 |
| 把「允许失败」写成「失败文本必须匹配 X」 | GLib 在这条路上有两条给不同文本的失败路径，文本不是稳定契约（见 §2 错法 B） | 假阴性（真回归被放过）或假阳性（措辞一变构建就红） |
| 只吃 `meson test` 的退出码 | 退出码 0 不覆盖 SKIP 与「用例没注册」 | 把「只跑了 2/3」当「3/3 全绿」 |
| 汇总块读不到时静默放过 | 「读不到结论」不等于「结论是好」 | 断言退化成恒真 |

## 关联

- `similar_to` **DRAFT-libgmobile-0.7.2-meson-not-installed-is-not-skipped-and-exit-code-is-not-coverage**：
  同一条主线（判据在汇总块、不在退出码）。本条往前一步——**上游程序数**也可能
  不等于**必须通过的程序数**，所以配方里要把 `UPSTREAM` / `REQUIRED` / `BLOCKED`
  三个集合分开表达，而不是一个数。
- `archives/d/dbus/1.14.10.2/manifest.yaml`：AF_UNIX bind 被拒这条平台事实的首次
  记录；本条把「它对测试代码意味着什么」补上。
- `archives/s/systemd/261/manifest.yaml`：47.6% 通过率如实声明的先例（rule 1.2）。
- `archives/a/accountsservice/26.27.3/notes.md`：同一族依赖（polkit/systemd）的
  适配笔记，其中 polkit 的 `.pc` 处理与本包的配方同源。

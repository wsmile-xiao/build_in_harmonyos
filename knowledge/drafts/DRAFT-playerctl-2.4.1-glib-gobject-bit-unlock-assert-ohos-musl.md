# DRAFT-PLAYERCTL-2.4.1-GLIB-GOBJECT-BIT-UNLOCK-ASSERT-OHOS-MUSL: glib GObject 原子锁断言在 OHOS/musl 间歇触发

- **草稿 ID**: DRAFT-PLAYERCTL-2.4.1-GLIB-GOBJECT-BIT-UNLOCK-ASSERT-OHOS-MUSL
- **严重度**: 1（阻塞级：影响所有 OHOS 上的 glib 图形/GObject 消费者）
- **类别**: glib, ohos, musl, atomic, flaky-test, blocking-risk
- **来源**: playerctl 2.4.1 适配（HarmonyOS PC aarch64）

## 错误特征

```
GLib-GObject:ERROR:../gobject/gobject.c:649:object_bit_unlock: assertion failed: (_object_bit_is_locked == lock_bit)
Bail out!
```

两态表现：① 子进程 stdout 被断言文本污染（文本断言失败）；
② 子进程无输出 → pytest-timeout 5s 超时。

## 根因分析

glib 2.84.0.1 GObject 的对象锁位操作校验（`gobject.c:649 object_bit_unlock`）在
OHOS/musl 工具链上间歇触发。间歇性证据：同一代码路径的 `test_commands`（通过）与
`test_basics`(失败) 在同一轮内表现相反；凡涉及 `playerctld` 后台驻留 + 多播放器
切换的用例更易命中。本适配零源码补丁、零二进制改写，非消费方引入，归因依赖层。

## 影响面与方案

- 影响：playerctl 上游 18 用例中 6 项同源失败；推及所有 OHOS 上经 GObject
  子进程/多线程路径的消费者（图形、MPRIS、D-Bus 守护进程类）
- 短期：按 TEST_QUALITY_SPEC §3.3 如实申报失败与归因，不裁剪用例；
  session bus 环境独立实跑留痕
- 中期：向 glib 适配方申报，排查 g_atomic_* / __atomic 内建在 musl 上的实现，
  必要时重建 glib 包

## 禁止事项

- 裁剪/跳过失败用例掩盖通过率；在 CI 侧重试至通过并隐瞒失败（违反 R51 申报口径）
- 把断言失败归因为适配层源码问题而修改消费者源码（无效且掩盖根因）

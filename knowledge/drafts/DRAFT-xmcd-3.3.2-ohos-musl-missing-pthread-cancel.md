# OHOS musl 缺 POSIX 线程取消 API（pthread_cancel 族）——特性宏间接层 + 取消点降级

> 知识条目：`knowledge/drafts/DRAFT-xmcd-3.3.2-ohos-musl-missing-pthread-cancel.kv`
> 拓展包（检测脚本 + 复现脚本 + README）：`knowledge/drafts/musl-pthread-cancel-gap/`
> 样例库：`archives/x/xmcd/3.3.2`（xmcd 3.3.2，2006 年发行快照）

## 1. 现象

在 OHOS aarch64（clang 15 / musl）上构建使用 POSIX 取消点 API 的老代码时：

```
undefined symbol: pthread_cancel
undefined symbol: pthread_setcancelstate
implicit declaration of function 'pthread_cancel'
```

即使追加 `-lpthread` / `-pthread`，仍报同一 undefined symbol。

## 2. 根因（实测证据）

| 探针（2026-10-04，OHOS SDK 26.0.0.18） | 结果 |
|---|---|
| `nm -D --defined-only <libc.so>` → `pthread_cancel` | **0**（缺失） |
| 同探针 → `pthread_setcancelstate` / `pthread_setcanceltype` | **0**（缺失） |
| 同探针 → `pthread_exit` / `pthread_detach` / `pthread_cond_timedwait` | 各 1（存在） |
| `nm --defined-only <sysroot>/usr/lib/*/libpthread.a` 定义符号数 | **0（空壳库）** |

结论：缺口在 libc 本体，且 sysroot 的 `libpthread.a` 为空壳，**链接选项无法补齐**。
上游代码通常把 `pthread_cancel` 用于两类场景：①错误分支里的"线程自杀"
（`pthread_cancel(pthread_self())`）；②跨线程取消点（`pthread_cancel(other)` 配合
`pthread_cleanup_push` 清理链）。

## 3. 处置（首选策略）

**源码侧特性宏间接层**，把平台差异收敛成一个宏，缺省保持上游原语义：

```c
/* pthr.h —— 缺省 1 = 上游行为；配方以 -DHAVE_PTHREAD_CANCEL=0 切换 */
#if !defined(HAVE_PTHREAD_CANCEL) || HAVE_PTHREAD_CANCEL
#define PTHR_SELF_ABORT(t)  pthread_cancel(t)
#else
#define PTHR_SELF_ABORT(t)  pthread_exit(NULL)
#endif
```

| 取消点形态 | 处置 | 语义说明 |
|---|---|---|
| 自中止 `pthread_cancel(pthread_self())` | `PTHR_SELF_ABORT(t)` → `pthread_exit(NULL)` | **语义等价**（本线程终止），栈上 `pthread_cleanup_push` 链正常展开 |
| 跨线程 `pthread_cancel(other)` | 记录日志 + 空操作，交后续 `stop`/`join` 收管线 | **语义近似**，需确认该取消点后有收管线路径（样例库该点后立刻 `cdda_pthr_stop`） |
| `pthread_setcancelstate/type` 配置调用 | 特性宏分支整体旁路 | 仅为取消做准备，不产生未定义符号 |

配方注入：`-DHAVE_PTHREAD_CANCEL=0`。**补丁内只含特性宏、不含平台宏**，同一配方
在 Linux 与 OHOS 上都能构建。

## 4. 禁止做法

1. **`-lpthread` / `-pthread` 顶替**——空壳库，符号依旧缺失（探针已证）；
2. **弱符号 stub**（`__attribute__((weak))` 空实现）——把"取消"静默变成"什么都没做"，
   运行期线程不收线/资源泄漏，且无任何错误信号。

## 5. 验证

- 直线验证：`conan create archives/x/xmcd/3.3.2 -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=ci/conan/profiles/ohos-aarch64` 全绿（W3 本地 CI，exit_code=0）；
- 反向验证：去掉 `-DHAVE_PTHREAD_CANCEL=0` 即恢复 `undefined symbol: pthread_cancel`；
- 运行验证：headless 消费者用例（`cda -h`、`xmcd -h` 抵达显示初始化）通过。

## 6. 关联

- 拓展包文档：`knowledge/drafts/musl-pthread-cancel-gap/README.md`（触发场景/适用库范围/限制）
- 同族 libc 缺口：`DRAFT-xli-1.17.0-ohos-musl-missing-rindex-bsd-legacy.*`（逐函数最小定向替换）
- 传统 tty 头/HZ：`DRAFT-xmcd-3.3.2-ohos-musl-missing-termio-and-hz.*`

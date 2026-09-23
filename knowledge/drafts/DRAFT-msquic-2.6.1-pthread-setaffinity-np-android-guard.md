# 反向平台守卫 #if !defined(__ANDROID__) 漏掉 OHOS(musl)——对齐上游平台策略而非改写

## 错误特征

```
src/platform/platform_posix.c:XXX: error: call to undeclared function
'pthread_setaffinity_np' with C99 [-Werror,-Wimplicit-function-declaration]
```

或链接期：

```
ld.lld: error: undefined symbol: pthread_setaffinity_np
```

- 只在 musl 系 libc（OHOS/Alpine）触发，glibc 正常
- 代码形态：上游用 `#if !defined(__ANDROID__)` 包住 glibc 专有调用

## 根因

musl/bionic 都不提供 `pthread_setaffinity_np`（glibc 扩展）。上游跨平台库
惯用**反向守卫**排除 bionic：

```c
#if !defined(__ANDROID__)   // 隐含假设：非 Android == glibc
    pthread_setaffinity_np(...)
#endif
```

OHOS(musl) 落进这个隐含假设的盲区：**不是 ANDROID 却也没有该 API**。

## 与 E211 的差异（查重覆盖判断）

| 条目 | 场景 | 修法 |
|---|---|---|
| E211 | 裸符号缺失，无平台分支语境 | 改写为 sched_setaffitness 等 POSIX API |
| 本条 | 上游已自设 `!__ANDROID__` 排除分支 | **对齐上游策略**：`&& !defined(__OHOS__)` 追加排除 |

判定依据：被排除代码是否功能必需 + 上游对同类平台怎么处理。
msquic 的 CxPlatThreadCreate 尾部绑核是**性能优化非功能路径**，上游对
Android 直接跳过——OHOS 对齐跳过即可，后续 rebase 零冲突（改写调用
逻辑则每轮升级都可能冲突）。

## 解法（msquic 2.6.1 实证，补丁 0001）

```c
// 上游：#if !defined(__ANDROID__)
// 改为：
#if !defined(__ANDROID__) && !defined(__OHOS__)
    if (Status == QUIC_STATUS_SUCCESS) {
        if (Config->Flags & CXPLAT_THREAD_FLAG_SET_AFFINITIZE) {
            cpu_set_t CpuSet; ...
```

佐证：同函数**前部**的 attr 版亲和调用（pthread_attr_setaffinity_np）
上游自己就用 `#ifdef __GLIBC__` 守卫——说明该函数本就按 libc 分支设计，
musl 走"跳过"是上游心智内的一致行为。

## 降级方案

- 功能必需不能跳过 → E211 路线：`sched_setaffinity(0, sizeof(cpu_set_t), &set)`
- 或上游化：提议改 `#if defined(__GLIBC__)` 正向守卫（语义更准）

## 红线

- **不要**在 musl 上硬链 `-lpthread` 试图解决——符号根本不存在，链接必挂
- **不要**自造 `pthread_setaffinity_np` stub（空壳宏）——R6 禁空壳守卫，且
  亲和性跳过上游已有先例语义
- 验证：conan create 全绿 + test_package 真实 API PASS（msquic 的
  RegistrationOpen 会 spawn worker 线程，pthread_create 路径被真实覆盖）

## 关联

- msquic 2.6.1 适配 PR patches/0001
- 对照：E211（sched API 改写）、E094/E147（affinity 头文件族）

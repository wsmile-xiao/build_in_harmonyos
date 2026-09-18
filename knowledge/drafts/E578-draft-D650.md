# E578: musl(OHOS) 无 pthread 取消 API — 线程改为协作式退出

## 错误特征

```
undefined reference.*pthread_cancel
undefined reference.*pthread_setcancelstate
undefined reference.*pthread_testcancel
```

实测（libkysdk-base 3.0.1.3，OHOS aarch64 / clang 15 / musl）：

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: pthread_setcancelstate
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: pthread_testcancel
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: pthread_cancel
clang-15: error: linker command failed with exit code 1
```

## 根因

OHOS 使用 musl libc：`pthread.h` 既不声明 `pthread_cancel` / `pthread_setcancelstate` /
`pthread_testcancel`，libc 也不导出这些符号（musl 不实现线程取消）。glibc 下依赖
“取消点”终止后台线程的代码，在链接可执行文件（`--no-allow-shlib-undefined`）时报未解析符号；
共享库自身因允许未定义符号可能“编译通过”，问题被推迟到可执行文件链接阶段。

## 推荐方案：协作式退出（cooperative shutdown）

1. 源文件加退出标志：`static volatile int g_thread_stop = 0;`
2. 线程循环条件由 `while (1)` 改为 `while (!g_thread_stop)`；
   把无限阻塞等待（`epoll_wait(..., -1)` / `poll(..., -1)`）改为有限超时
   （本例 200ms），使线程能周期性观察退出标志。
3. 销毁路径：`g_thread_stop = 1;` 后 `pthread_join(tid, NULL);`；
   若原实现调用过 `pthread_detach(pthread_self())`，须一并移除 detach 使其可 join。
4. 删除所有 `pthread_setcancelstate/pthread_testcancel` 调用。

语义影响：线程退出延迟从“立即取消”变为“≤1 个轮询周期”，无功能损失。

## 验证

```
conan create <recipe> -pr:h=ci/conan/profiles/ohos-aarch64 ...    # 链接阶段不再报未解析符号
```
libkysdk-base 实测：改造后 `make -j4` EXIT=0，`test-kytimer` / `kylog-testpressure`
等上游测试 rc=0（12/12）。

## 相关条目

- **E085**（`similar_to`）：同一根因的另一条处置路径。E085 面向 gnulib/gcry 的 weak-symbol
  线程可用性探测（`PTHREAD_IN_USE_DETECTION_HARD`）与 stub 桩函数，解决的是「链接不再失败」；
  本条目解决的是「取消语义消失后线程如何正确收尾」。两者互补：能改线程模型时优先用协作式退出
  （语义完整）；只允许链接期兼容时才退回 E085 的 stub（取消变成静默空实现）。
- **E513**（`similar_to`）：同样处理「取消不可用后 joinable 线程如何收尾」，但机制不同——
  E513 走 `guarded-signal-thread-exit`（安装 async-signal-safe 的线程退出处理器 + 发信号），
  本条目走**不引入信号的协作式退出**（`volatile` 标志 + 有限超时等待 + `pthread_join`）。
  两者取舍：不能改动/拦截信号的库（或已有 signal handler）用本条目；可以自建信号路径时用 E513。

## 申报定位（供主编参考）

- **路径**：路径 B（贡献创新 / 知识库扩展）申报中的**方案侧补充**条目，与 E577 同批提交。
- **与既有条目的关系（已如实申报，不谎报为全新知识）**：根因层面已被 **E085** 覆盖
  （其 `error_signature` 就是 `undefined reference to pthread_cancel`）；线程收尾语义层面
  与 **E513** 相邻但机制不同。本草稿的价值在**推荐方案**：给出可操作的协作式退出改造清单
  （退出标志 → 循环条件 → 无限阻塞改有限超时 → 去 detach 使可 join → 删 setcancelstate 调用）
  与量化语义影响（退出延迟 ≤1 个轮询周期，本例 200ms，无功能损失），这是上述两条未展开的部分。
- **编号变更说明**：本草稿最初编号为 `E429`，但该号同时被 13 个其他草稿占用
  （`_next_id()` 取「最小空闲号」且不排除草稿占用所致），为避免主编合入时歧义，改为当前编号。

## 关键词

pthread_cancel, pthread_setcancelstate, pthread_testcancel, musl, OHOS, 协作式退出,
undefined reference, no-allow-shlib-undefined, thread cancellation

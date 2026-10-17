# DRAFT-aml-1.0.0-ohos-pthread-setcancelstate-meson-feature-detect — OHOS 链接期缺 pthread_setcancelstate 用 Meson 特性检测守卫（路径 B 候选）

> 配对条目：`knowledge/drafts/DRAFT-aml-1.0.0-ohos-pthread-setcancelstate-meson-feature-detect.kv`
> 来源：aml 1.0.0 R01 适配（pc2-46，2026-09-24）

## 问题

在 HarmonyOS PC 上编译 aml 1.0.0（Meson 构建）时链接失败：

```
ld.lld: error: undefined symbol: pthread_setcancelstate
>>> referenced by thread-pool.c:100
>>>               libaml.so.1.0.0.p/src_thread-pool.c.o:(worker_fn)
clang-15: error: linker command failed with exit code 1
```

编译期还有 `call to undeclared function 'pthread_setcancelstate'` 警告。

## 根因

- 编译期 sysroot（SDK 26）的 `pthread.h` **不声明** `pthread_setcancelstate`
  （`grep -c` = 0），sysroot libc **无该符号**（链接失败）。
- 但设备**运行** libc `/system/lib64/libc.so` 实际导出：
  ```
  nm -D /system/lib64/libc.so | grep pthread_...
  T pthread_cancel
  W pthread_setcancelstate
  W pthread_testcancel
  ```
  即「编译期 sysroot 缺声明/缺符号」≠「运行时不存在」。与 Android 的
  处理思路一致：worker 线程禁用取消是防御性行为，缺失时可安全跳过。

## 最小本地解决 / 边界

```meson
# meson.build（0001-meson.build.patch 要点）
cc = meson.get_compiler('c')
have_pthread_setcancelstate = cc.has_function('pthread_setcancelstate',
    prefix: '#include <pthread.h>')
if have_pthread_setcancelstate
    c_args += '-DHAVE_PTHREAD_SETCANCELSTATE'
endif
```

```c
// src/thread-pool.c（0002-src-thread-pool.c.patch 要点）
#if !defined(__ANDROID__) && defined(HAVE_PTHREAD_SETCANCELSTATE)
    pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, NULL);
#endif
```

边界：

1. 特性检测 > 平台列表：不硬编码 `__OHOS__`（符合 R8/PF5，避免平台宏闸拦截），
   跨 libc 变体（musl/OHOS/其他裁剪 libc）自动适配；
2. 若软件**必须**依赖该符号语义（非可选），应走声明型 compat header
   （DRAFT-ohos-pthread-cancel-decl 方案），而非跳过；
3. glibc 等完整 libc 下 `has_function` 自动为真，本守卫不改变行为。

## 验证

```bash
meson setup builddir --prefix=$DEFAULT_PREFIX   # rc=0
ninja -C builddir                                # rc=0，libaml.so.1.0.0 链接成功
meson setup builddir-ex -Dexamples=true && ninja -C builddir-ex   # examples 构建成功
./builddir-ex/examples/ticker                     # 输出 "tick 1!"（事件循环真实运行）
conan create ... -pr:h=ohos-aarch64 -pr:b=ohos-aarch64            # G2 通过，含 test_package 消费者测试
```

## 与既有知识的关系（七轴查重）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 无 Meson + 特性检测 + 保留 __ANDROID__ 守卫的条目 |
| causal_duplicate | 部分 | 根因与 E085/E127/E513 同族（OHOS/musl libc 缺 pthread cancel 系列），但本条目聚焦「编译期 sysroot 缺符号」 |
| trigger_overlap | 部分 | `undefined symbol: pthread_setcancelstate` 与 E085/E127/E507 特征重叠 |
| solution_overlap | 部分 | E507 同为能力探测（CheckCXXSymbolExists），但为 CMake+Boost 特化；本条目为 Meson 通用写法 |
| combination_novelty | 是 | Meson `cc.has_function` + HAVE 宏 + 保留 __ANDROID__ 守卫 + 无 __OHOS__ 宏 的组合 |
| boundary_novelty | 是 | 明确「sysroot 编译期缺符号」与「运行时 libc 导出 T/W」的差异边界（nm 实证） |
| test_migration_novelty | 是 | 消费者测试真实运行事件循环（ticker 回调）验证适配后行为 |

**决定：** 部分重复（causal/solution 与 E085/E127/E507 部分覆盖），但新增
差异（Meson 特性检测通用写法 + 编译期/运行时符号边界）已由本轮真实日志验证、
可跨库复用 → **new_draft**（路径 B），建立同 stem 的 `.kv`/`.md` 配对草稿。

## 适用边界 / 反例

- 适用：OHOS 上 Meson 构建、worker/后台线程调用 pthread_setcancelstate 的库
- 反例：必须依赖取消语义的库（应走声明型 compat header）；
  已有完整 glibc 声明的平台（守卫自动失效，无需处理）

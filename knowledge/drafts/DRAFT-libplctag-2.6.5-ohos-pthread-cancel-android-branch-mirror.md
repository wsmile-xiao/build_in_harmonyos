# DRAFT-libplctag-2.6.5-ohos-pthread-cancel-android-branch-mirror：复用上游 __ANDROID__ 分支修复 OHOS pthread_cancel 缺失

> Contributor: junshi_liu | Status: Draft | Updated: 2026-09-08
> Source: libplctag 2.6.5 HarmonyOS PC 适配（R01，task libplctag-2.6.5-r01-pc1-24-20260907T135322Z）
> 本文件与 `DRAFT-libplctag-2.6.5-ohos-pthread-cancel-android-branch-mirror.kv` 配对，stem 完全相同。

## 现象

conan-verify G2（conan create）链接阶段失败：

```text
ld.lld: error: undefined symbol: pthread_cancel
>>> referenced by platform.c
>>>               platform.c.o:(thread_kill) in archive .../libplctag_static.a
clang-15: error: linker command failed with exit code 1
```

编译期同时出现 `pthread_cancel` 隐式声明警告（C99 起不允许隐式函数声明）。

## 根因

OHOS musl libc 不实现 POSIX 线程取消 API（`pthread_cancel`/`pthread_testcancel`/
`pthread_setcancelstate`/`pthread_setcanceltype`）。上游 `src/platform/posix/platform.c`
的 `thread_kill()` 仅对 `__ANDROID__` 提供 `pthread_kill(t->p_thread, 0)` 替代分支，
非 Android 路径直接调用 `pthread_cancel`，在 OHOS 链接时符号缺失。

与既有知识的差异：E127（OpenMP `KMP_CANCEL_THREADS` undef 宏场景）与 E513
（JACK 信号方案 pthread_kill+SIGUSR1）均不覆盖"上游源码已自带 Android 合法
替代分支、只需扩宽预处理器守卫"的最小补丁形态。

## 修复方案

将上游既有 Android 守卫扩宽为同时匹配 OHOS，镜像已随发行版验证的 Android 行为：

```c
-#ifdef __ANDROID__
+#if defined(__ANDROID__) || defined(__OHOS__)
        pthread_kill(t->p_thread, 0);
 #else
        pthread_cancel(t->p_thread);
-#endif /* __ANDROID__ */
+#endif /* __ANDROID__ || __OHOS__ */
```

补丁：`patches/0001-src-platform-posix-platform.c.patch`（portability），
conandata.yml `patch_description` 说明平台宏例外理由（musl libc 探针，R8 例外）。

## 验证

- `conan-verify libplctag 2.6.5`：G2 conan create PASS
- `nm libplctag_static.a | grep -c pthread_cancel`：0（补丁后静态库无该符号引用）
- test_package `ohos_test`：5 轮 `plc_tag_create`/`plc_tag_destroy` 生命周期 + 版本契约 PASS
- W3 本地 CI 模拟：通过

## 适用边界与反例

- 适用：上游代码已含 `__ANDROID__` 分支且用 `pthread_kill`/其他替代线程取消的库；补丁为最小 diff。
- 反例：无线程取消调用或上游无 Android 分支的库不需要此补丁（此时直接改调用点或依赖 E127/E513 方案）。
- 语义注意：`pthread_kill(t, 0)` 只做存在性检查而非真正取消线程，与 Android 分支行为一致；若库依赖取消语义，需评估功能影响并如实记录。

## 关系

- similar_to: E085（musl pthread_cancel 缺失根因）、E127（条件编译守卫思想）、E513（线程退出替代方案）
- caused_by: OHOS musl libc 平台限制（不实现 POSIX 线程取消）
- conflicts_with: 无

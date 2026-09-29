# DRAFT-E680-ohos-no-pthread-cancellation

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-E680-ohos-no-pthread-cancellation.kv`

**标题**：OHOS NDK 不提供 pthread cancellation 三函数（pthread_cancel/testcancel/setcanceltype）
                        的符号——链接失败的集中 shim 方案（保留真实 mutex/线程，仅补取消 API 缺口）

**阶段: `build|link` · 触发: `conan|make|clang-linker` · 类别: `ohos-ndk|pthread|cancellation|link|porting-shim` · 严重级: `2`**

## 错误签名（error_signature）

```text
'undefined symbol: pthread_cancel\b|undefined symbol: pthread_testcancel\b|undefined symbol: pthread_setcanceltype\b|ld\.lld: error: undefined symbol: pthread_(cancel|testcancel|setcanceltype)'
```

## 根因（root_cause）

>
  OHOS NDK sysroot 的 libc.so 与 libpthread.a 都不导出 pthread_cancel()、
  pthread_testcancel()、pthread_setcanceltype()（readelf 实查三符号计数全 0），
  pthread.h 也只暴露 PTHREAD_CANCEL_* 宏而无函数原型；glibc/musl 系统上这些符号
  存在于 libc（或 libpthread），因此「设备上编译过的老代码」在 OHOS 上会在链接期
  报 undefined symbol。凡在 mutex 宏里内联 pthread_setcanceltype、在线程体里调
  pthread_testcancel、或提供 cancel_all 型收尾 API 的项目（HIDS/守护类老 C 项目
  常见）都会命中。pthread_create/pthread_join/pthread_mutex_* 本身是存在的——
  项目往往「除取消家族外全部可链」，失败面很小但致命。

## 方案（rec_approach）

pthread-cancel-shim-header-first（集中 shim + 原型前置 + ESRCH 语义）

## 关键词

pthread_cancel, pthread_testcancel, pthread_setcanceltype,
                        libpthread.a, libc.so, seccomp, cancellation API,
                        SH_MUTEX_LOCK, sh_pthread_cancel_all, ESRCH,
                        readelf --dyn-syms, NDK sysroot

## 来源

本条目取自 `knowledge/drafts/DRAFT-E680-ohos-no-pthread-cancellation.kv`；promote 后对应 `knowledge/doc/E###.md`。

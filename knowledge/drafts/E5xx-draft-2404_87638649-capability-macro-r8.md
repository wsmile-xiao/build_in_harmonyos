# DRAFT-E5xx: R8 合规的平台 API 缺失适配范式——AC_CHECK_FUNCS 能力宏探测替代 #ifdef __OHOS__ 平台宏

## 场景

目标平台（OHOS musl）缺失某 POSIX API 实现，但头文件保留了相关宏定义
（头/实现不同步）。仓规范 R8 禁止 patches/ 引入 `#ifdef __OHOS__` 平台
条件宏（补丁等价源码），要求 POSIX 接口适配。

vlc 3.0.23 案例：OHOS musl 无 `pthread_cancel`/`pthread_setcancelstate`/
`pthread_testcancel`/`posix_close` 四函数实现，但 unistd.h 定义了
`POSIX_CLOSE_RESTART` 宏、pthread.h 定义了 `PTHREAD_CANCEL_*` 宏——
按宏存在性分支（上游原生写法）会编译过但链接失败（undefined symbol）。

## 为什么不用 `#ifdef __OHOS__`（E102 的范式升级）

- R8 门禁：平台宏分支会把差异固化进上游源码树，非 OHOS 构建的 CI
  永远不覆盖该分支 → 长期不可维护的平台分叉
- AI review（atomgit-bot）将其归类为欺骗性行为检测的 High 优先级，
  必改项
- 能力宏（HAVE_*）是 autoconf 的标准语义：**任何**缺该函数的平台
  （不只是 OHOS）都自动走 fallback，上游可接受度高

## 修法三步

### 1. configure.ac 追加链接探测

```m4
case "$SYS" in
  "linux")
    AC_CHECK_FUNCS([eventfd vmsplice sched_getaffinity recvmmsg])
    dnl Thread cancellation & restartable close capability probes.
    dnl musl variants (e.g. OHOS) may ship POSIX_CLOSE_RESTART /
    dnl PTHREAD_CANCEL_* macros in headers without implementing the
    dnl functions; the link probe below decides by symbol presence.
    AC_CHECK_FUNCS([posix_close pthread_cancel pthread_setcancelstate pthread_testcancel])
    ;;
```

关键：AC_CHECK_FUNCS 的 conftest **不带 -Werror**（autoconf 默认），
头文件无声明只产生隐式声明告警；**链接成败**（符号存在性）才是判据。
OHOS musl 无符号 → `HAVE_PTHREAD_CANCEL` 等 config.h 中 `#undef`。

### 2. 源码守卫改能力宏（逻辑等价改写）

```c
/* 原（R8 违规）：
 * #ifdef __OHOS__
 *     (void) th;                     no-op
 * #else
 *     pthread_cancel(th.handle);
 * #endif
 */
#ifndef HAVE_PTHREAD_CANCEL
    (void) th;                        /* capability absent: no-op */
#else
    pthread_cancel(th.handle);
#endif
```

posix_close 场景（宏在但函数缺——能力宏与上游宏双重守卫）：

```c
#if defined(POSIX_CLOSE_RESTART) && defined(HAVE_POSIX_CLOSE)
    ret = posix_close(fd, 0);
#else
    ret = close(fd);
#endif
```

多函数依赖逐函数探测（pthread_cancel 与 pthread_setcancelstate
可能在不同 libc 中分别存在——OHOS 四个全缺、musl 主线四个全有，
但逐函数守卫对混合场景最稳）。

### 3. patch-ng 严格模式验证（conan apply fuzz=False）

多补丁共改 configure.ac 时，后序补丁的 hunk 行号必须按前序补丁
插入行数精算（本例 0002 在 configure.ac 706 行附近插 5 行 → 0004 的
hunk 起始行 +5）。GNU patch 容 fuzz 自动偏移，**conan 内置 patch-ng
不容**（fuzz=False 严格模式）——hunk 头必须与"前序补丁应用后"的
实际行号一致。验证方法：

```python
from patch_ng import fromfile
ps = fromfile("xxx.patch")
ok = ps.apply(root=srcdir, fuzz=False, strip=1)   # 逐补丁依序验证
```

## 验证证据（vlc 3.0.23）

- OHOS 下 config.h 实测：`/* #undef HAVE_POSIX_CLOSE */` 等 4 宏全部
  undef → 走 fallback 分支（行为与平台宏方案等价）
- libvlc_new/libvlc_release 实例生命周期 5/5 PASS（线程系统在无
  cancel 能力下正常——vlc 线程退出走 join 不依赖 cancel）
- CI #61558（R8 修复轮）绿；AI review force 复审：**未发现问题**
  （原 High 意见清除）

## 与既有条目的关系（查重）

- **E102**（add-linux-ohos-to-validation）：config.sub 白名单——不涉
  平台宏守卫问题，无交集
- **E011**（edit-umask-in-configure）：HMDFS umask——同 PR 但不同问题
- 本条是对"E102 时代"`!defined(__OHOS__)` 写法的**修正性增量**：
  R8 落地后该写法被禁，能力宏探测是合规替代范式

## fallback（非 autotools 项目）

- CMake：`check_function_exists(pthread_cancel HAVE_PTHREAD_CANCEL)` +
  `configure_file` 注入 config.h
- meson：`cc.has_function('pthread_cancel')` + 配置头
- 手写 configure：模仿 AC_CHECK_FUNCS 的 conftest（编译+链接双探测）
- 函数存在但语义不同（非缺失）：运行时探测（dlsym + weak symbol）

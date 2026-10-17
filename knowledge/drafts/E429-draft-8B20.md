# E429 — FreeBSD 专有接口（sysctl/errc/cdefs 宏）迁移 OHOS 的守卫与替换

## 错误特征

FreeBSD/NetBSD 系源码（如 Apple bsdmake）在 OHOS 上编译时报以下典型错误：

```
fatal error: 'sys/sysctl.h' file not found
ld.lld: error: undefined symbol: errc
error: use of undeclared identifier '__FBSDID'
error: use of undeclared identifier '__dead2'
warning: incompatible integer to pointer conversion passing 'long' to parameter of type 'const char *'
```

## 触发条件

- 构建系统: makefile（直接 clang 编译）或 autotools
- 阶段: 编译（compilation）/ 链接（linking）
- 平台: OHOS（无 FreeBSD `sys/sysctl.h`、`sysctl(3)`、`errc()`；`sys/cdefs.h` 仅定义 `__dead`，无 `__FBSDID`/`__RCSID`/`__dead2`）

## 根因分析

FreeBSD 源码依赖三个 OHOS 缺失的接口层：

1. **`<sys/sysctl.h>` 与 `sysctlbyname()`**：FreeBSD 专有系统信息接口。bsdmake 中用于
   `machdep.ispc98`（pc98 机器类型）探测，上游注释明确仅 FreeBSD 需要。
2. **`errc()`**：BSD libc 扩展（`errc(exitcode, errnum, fmt...)`），OHOS musl libc 无此符号。
3. **`sys/cdefs.h` 宏**：`__FBSDID(s)` 嵌入 RCS 版本串、`__dead2` 为 `__attribute__((__noreturn__))`，
   OHOS 版 `sys/cdefs.h` 只定义了 `__dead`。

**附加陷阱**：为消除 sysctl 依赖而给整块代码加 `#ifdef __FreeBSD__` 时，若该块内含
`machine = getenv("MACHINE")` 之类的赋值，非 FreeBSD 分支下 `machine` 成为未初始化局部变量，
后续 `if (machine == NULL)` 读垃圾值 → 运行时随机段错误（bsdmake 实测 rc=139）。

## 解决方案

### 推荐方案

1. **头文件守卫**：`<sys/sysctl.h>` 的 include 加 `#ifdef __FreeBSD__` / `#endif`。
2. **调用本体守卫**：`sysctlbyname()` 调用块加 `#ifdef __FreeBSD__`，但**保留块内
   `machine = getenv("MACHINE")` 赋值**在外（getenv 是 POSIX，任何平台都应执行），
   避免未初始化 UB。
3. **宏注入**：编译参数提供缺失宏：
   ```bash
   clang -D'__FBSDID(x)=' -D'__dead2=__attribute__((__noreturn__))' -c *.c
   ```
4. **errc 等价替换**：`errc(2, EAGAIN, fmt, ...)` → `errno = EAGAIN; err(2, fmt, ...)`
   （`err()` 在 OHOS 存在，语义一致）。

### 禁止做法

- ❌ 整块 `#ifdef __FreeBSD__` 包裹含 getenv 赋值的代码 → 未初始化局部变量 UB，随机段错误。
- ❌ 提供空 stub 头/空壳函数绕过编译 → R8 禁止空壳，且掩盖真实平台差异。

## 验证

```bash
# 干净构建 + 消费者测试
conan create archives/b/bsdmake/24 --build=missing
# test_package 4 组功能断言应全通过：
#   variable expansion + rule execution passed
#   dependency graph passed
#   error propagation passed
#   MAKESYSPATH sys.mk passed
```

## 关联条目

- 相关: R8（补丁平台宏守卫需实质逻辑）、R33（编译器从 conan 环境获取）

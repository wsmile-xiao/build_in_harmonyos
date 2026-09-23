# colrc 0.3.7 适配笔记

## 适配问题

### 1. _GNU_SOURCE 预处理器检查错误
**问题**: colr.h 中使用 `#elif _GNU_SOURCE < 1` 导致预处理器错误
**原因**: `_GNU_SOURCE` 是特性宏，值可能未定义，不能直接用于数值比较
**解决**: 删除该检查块（84-88 行），该块仅用于测试目的

### 2. COLR_GNU 宏在 musl 环境下的定义
**问题**: 原代码无条件定义 `COLR_GNU`，但该宏控制 GNU 扩展的使用（如 asprintf）
**原因**: OHOS 使用 musl libc，不应启用 glibc 专用特性
**解决**: 将 `#define COLR_GNU` 改为条件定义 `#if (defined(__GLIBC__) && (__GLIBC__ >= 2))`，并将 `printf.h` 的包含条件改为 `#if COLR_GNU` 值判断
**R8 合规**: 使用 `__GLIBC__` libc 特征检测，不使用 `__OHOS__` 平台宏

### 3. ioctl 函数签名不匹配
**问题**: tests/test_colr_term.c 中 `ioctl(0, TIOCGWINSZ, &ws)` 第二个参数类型不匹配
**原因**: POSIX 标准 ioctl 的 request 参数是 `int`，但上游使用 `unsigned long`
**解决**: 在 test_package 中用 `(int)TIOCGWINSZ` 强制转换

## 编译命令

```bash
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 测试

上游测试使用源码自带的 `test/snow.h`，通过 `make -C test clean test_colrc` 构建并执行 `./test/test_colrc --quiet`。依赖 glibc `printf.h` 的 `colr_asprintf` 测试在 OHOS musl 下按条件编译跳过，其余 snow 测试继续执行；测试覆盖的 `ioctl` 声明和定义均按 OHOS 的 `int` 签名适配。
---

**编译结束**: 2026-09-04 16:24
**最终状态**: built

# E999 — OHOS musl libc 缺 glibc 专有符号（malloc_stats）与 64 位整数对齐溢出

## 错误特征

上游测试/库代码在 OHOS（musl 系 libc，clang 15.0.4 aarch64）构建时出现三类典型症状：

1. 链接失败：`ld.lld: error: undefined symbol: malloc_stats`（`src/test.c: allocated_bytes` 引用）；
2. 测试挂起（timeout）：`new_iqueue((uint32_t)-1)` 后 `while (aligned_capacity < capacity)` 死循环；
3. 测试断言失败：`src/test.c:953: TEST failed`（clearsignal_iqsignal 循环，64 位下 i≥2^32）。

## 触发条件

- 构建系统：上游纯 Makefile / 含 glibc 专有扩展的 C/C++ 库
- 阶段：linking（malloc_stats）/ runtime（死循环）/ testing（断言失败）
- 平台：OHOS aarch64（libc 为 musl 系，无 glibc 专有扩展），64 位目标更常见

## 根因分析

| # | 症状 | 根因 |
|---|------|------|
| ① | undefined symbol: malloc_stats | OHOS libc（musl 系）无 glibc 专有 `malloc_stats()`；上游在 `#ifdef __linux` 下编译该路径，OHOS 定义了 `__linux__` 但 libc 无此符号 |
| ② | 测试挂起死循环 | `new_iqueue()` 用 `uint32_t aligned_capacity`，64 位下 `capacity=(uint32_t)-1` 时左移越过 2^32 溢出为 0，`while (0 < capacity)` 永不退出；32 位下 `(size_t)` 上限检查可返回 EINVAL，64 位下该检查不可达 |
| ③ | TEST failed（clearsignal） | `clearsignal_iqsignal()` 返回 `uint32_t`，测试循环 `for (size_t i = 1; i; i <<= 1)` 用 size_t 计数，64 位 i≥2^32 时与 uint32_t 返回必然不等 |

## 解决方案

### 推荐方案

1. **glibc 专有符号守卫**：`#ifdef __linux` → `#if defined(__linux) && defined(__GLIBC__)`，非 glibc（OHOS/musl）走上游自带的 `#else` 回退分支（本例 `allocated_bytes()` 返回 0）。
2. **64 位对齐溢出修复**：`uint32_t aligned_capacity` → `size_t`，并在左移前检测 `aligned_capacity > ((size_t)(uint32_t)-1) / 2` 即返回 `EINVAL`（与 32 位行为一致）。
3. **测试计数类型对齐**：循环计数 `size_t i` → `uint32_t i`，与公开 API 返回类型一致。

### 禁止做法

- ❌ 在 patches 新增行使用 `__OHOS__` 平台宏（PF5/R8 拦截）
- ❌ 直接调用 `malloc_stats()`（OHOS/musl libc 不存在该符号）

## 验证

```bash
make -j1 makedir iqueue
clang -Iinclude -std=c99 -O3 src/test.c bin/iqueue.a -lpthread -o bin/iqueue_test
./bin/iqueue_test        # exit 0，12/12 测试函数、371 断言全过
```

## 关联条目

- 相关: E245（libc 符号缺失类，但 E245 是 vhangup 内核 syscall 未封装，非 glibc 专有扩展）
- 部分覆盖: E392 / DRAFT-commander（raw makefile Conan 配方陷阱：make cwd）；DRAFT-fusion（CMake 无 install 规则手动打包）
# E429: Backtrace Test Functions Optimized Away Despite `__attribute__((noclone))`

## 问题描述

libbacktrace 等回溯测试库在 OHOS aarch64 + Clang 环境下，测试用例中的 `__attribute__((noclone))` 标记的回调函数（如 `callback_one`、`callback_two`）仍被编译器优化为尾调用或省略栈帧指针，导致 backtrace 测试无法捕获预期的独立函数栈帧。

GCC 的 `noclone` 属性在 Clang 中不被识别或忽略，优化级别 `-O2` 下默认启用尾调用优化和栈帧省略。

## 根因

- Clang 不支持 GCC 的 `__attribute__((noclone))`
- `-O2` 默认启用 `-foptimize-sibling-calls` 和省略 frame pointer
- 测试代码期望每个回调函数有独立栈帧入口，但实际被内联或合并

## 解决方案

**仅对测试编译目标**添加以下 CFLAGS（不影响库本身）：

```makefile
TEST_CFLAGS = -fno-optimize-sibling-calls -fno-omit-frame-pointer

# 应用到具体测试
btest_CFLAGS = $(AM_CFLAGS) $(TEST_CFLAGS)
stest_CFLAGS = $(AM_CFLAGS) $(TEST_CFLAGS)
```

或在 conanfile.py 的 `generate()` 中：

```python
if self.settings.os == "OHOS":
    tc = AutotoolsToolchain(self)
    # 仅测试需要，库不用
    tc.extra_cflags.append("-fno-optimize-sibling-calls")
    tc.extra_cflags.append("-fno-omit-frame-pointer")
    tc.generate()
```

## 验证

```bash
make check
# 检查测试日志中 backtrace 输出是否包含预期函数名
# 例如 libbacktrace: 33/33 tests passed
```

## 适用范围

- libbacktrace
- 任何依赖栈帧完整性的测试库（如 sanitizer 测试、profiler 测试）

## 参考

- E077: post-install ELF 修改后重签名
- E129: HMDFS 权限语义与 Makefile install 交互
- 上游 libbacktrace issue #27: Clang noclone attribute ignored

---

**草稿状态**: 待主编审核后提升为正式条目
**最后更新**: 2026-09-02

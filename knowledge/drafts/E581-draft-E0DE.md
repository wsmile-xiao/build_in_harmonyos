# E581: 老 autoconf C 模式 ptrdiff_t 检测误判，宏定义与 libc++ 头冲突

## 错误特征

- `cstddef:51:9: error: expected unqualified-id`
- `using ::ptrdiff_t _LIBCPP_USING_IF_EXISTS;` 展开报错
- `config.h:343:19: note: expanded from macro 'ptrdiff_t'`
- `#define ptrdiff_t long` 出现在 config.h

## 触发条件

1. 2001-2006 年代 autoconf 生成的 configure（zhcon 0.2.6 实测）
2. configure 检测 `ptrdiff_t`（AC_CHECK_TYPE 风格）在 **C 模式** 编译，且 `$ac_includes_default` 不含 `<stddef.h>`
3. OHOS 上误判 `ac_cv_type_ptrdiff_t=no`
4. conan 构建使用 `-stdlib=libc++`（libc++ 的 `<cstddef>` 有 `using ::ptrdiff_t`）

## 根因

老 autoconf 的 ptrdiff_t 检测测试程序不含 `<stddef.h>`，C 模式下无法看到 ptrdiff_t 定义 → 误判 no → config.h 写入 `#define ptrdiff_t long`。libc++ 的 `<cstddef>` 声明 `using ::ptrdiff_t _LIBCPP_USING_IF_EXISTS`，宏展开成 `using ::long` → "expected unqualified-id" 编译错误。

## 解决方案

在 configure 脚本的 ptrdiff_t 检测块前，针对 `*-linux-ohos` 强制缓存变量：

```sh
case "$host" in
  *-linux-ohos*) ac_cv_type_ptrdiff_t=yes ;;
esac
```

libc++ 已提供该类型，属事实修正。修复后 config.h 输出 `/* #undef ptrdiff_t */`，不再定义冲突宏。

## 验证证据

- zhcon 0.2.6 修复后：`checking for ptrdiff_t... (cached) yes`
- config.h 中 `/* #undef ptrdiff_t */`
- conan-verify G2 conan create 干净构建通过

## 适用边界

- 适用：老 autoconf 项目（`ptrdiff_t` 用 C 模式检测）+ OHOS/libc++ 编译 C++ 源
- 不适用：新 autoconf（已含 stddef.h）；非 libc++（libstdc++）场景可能不触发
- 类似风险类型：`size_t`/`off_t` 等老式 AC_CHECK_TYPE 宏定义均可能与其他头冲突

## 关联条目

- similar_to: E130（OHOS SDK libc++ 头特殊行为相关）
- 与 E580 互补：E580 是平台宏 `defined(linux)` 失效，E581 是类型检测宏冲突

# E429：OHOS `<utmpx.h>` 只声明 struct utmpx —— 用 configure 缓存变量 ac_cv_header_utmpx_h=no 绕过（无平台宏）

> Contributor: OpenDesk Agent D3C5 | Status: Draft | Updated: 2026-09-15
> Source: libproc2 4.0.6 适配（procps-ng 4.0.6，src/w.c 编译失败）

## 错误特征

- `call to undeclared function 'setutxent' / 'getutxent' / 'endutxent'`
  （clang -Wimplicit-function-declaration）
- `error: incompatible integer to pointer conversion assigning to 'utmp_t *'
  (aka 'struct utmpx *') from 'int'`
- 链接期：`undefined symbol: setutxent / pututxline / endutxent`
  （与 E121 的链接期签名一致，但本例先出现在**编译期**）

## 触发条件

- 构建系统: autotools（configure 的 `AC_CHECK_HEADERS([... utmpx.h])` 判定为 yes）
- 阶段: compilation（`config.h` 定义 `HAVE_UTMPX_H` 之后）
- 目标平台: OHOS / HarmonyOS PC（aarch64）

## 根因分析

OHOS sysroot **存在** `<utmpx.h>`（`clang -E -H` 可解析到
`.../sysroot/usr/include/utmpx.h`），因此 autoconf 的 `AC_CHECK_HEADERS` 判定
`ac_cv_header_utmpx_h=yes` → `config.h` 定义 `HAVE_UTMPX_H`。

但该头**只声明 `struct utmpx`**：`setutxent/getutxent/endutxent/getutxline`
等函数既没有声明，也没有被 libc 导出（`<utmp.h>` 反而提供可用的 stub API：
`setutent/getutent/endutent/utmpname`，实测 `getutent()` 返回 NULL）。
于是源码按 utmpx 分支编译即报隐式声明/类型转换错误，链接也无法通过。

关键点：**这是"头文件存在但 API 不存在"的探针假阳性**，不是缺头文件，所以
单纯加 `-I`/装依赖都无效。

## 解决方案

### 推荐方案（无平台宏，满足 R8/PF5）

在配方 `generate()` 中针对 OHOS 追加 configure 缓存变量，让源码走 `<utmp.h>` 分支：

```python
tc = AutotoolsToolchain(self)
if self.settings.os == "OHOS":
    tc.configure_args.append("ac_cv_header_utmpx_h=no")
```

- 只覆盖这一次 `AC_CHECK_HEADERS` 探针结果，不改动源码、不引入 `__OHOS__` 宏；
- 与 E121 的"改源码 `#undef HAVE_UTMPX_H`"等价，但不需要 patches/ 里出现平台宏。

### 禁止做法

- ❌ 只在 CFLAGS 里加 `-I...` 或安装"utmpx 兼容库"（问题是 API 不存在，不是头文件缺失）
- ❌ 在 patches/ 里用 `#ifdef __OHOS__` 包一层空壳 stub（R8：补丁默认禁平台宏；
  且空壳 stub 属 R8 禁止的"无实质逻辑"写法）

## 验证

```bash
# 复现（显式打开探针结果时的报错）
clang -fsyntax-only -I. -Ilocal -Ilibrary/include -DHAVE_UTMPX_H src/w.c   # exit=1

# 验证修复：configure 后 config.h 不再定义 HAVE_UTMPX_H
grep -n HAVE_UTMPX_H config.h        # → /* #undef HAVE_UTMPX_H */
```

实测（libproc2 4.0.6，OHOS 6.0 / clang 15）：`make -j1` exit 0，
`make check` 8 总 / 7 PASS / 1 FAIL（与 utmpx 无关的环境性失败），
`conan create` exit 0，`conan-verify` G0-G4 PASS。

## 关联条目

- 相关: E121（utmpx 不可用的链接期签名与源码补丁方案）、E007（config.guess 平台识别）

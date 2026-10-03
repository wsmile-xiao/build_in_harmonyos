# `TRUE`/`FALSE` 未定义：先用宿主编译器复现，再判定是不是平台问题

> Draft: `DRAFT-RT-APP-10-TRUE-FALSE-UNDEFINED`
> Stem: `rt-app-1.0-upstream-true-false-undefined` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-RT-APP-10-TRUE-FALSE-UNDEFINED
- **严重度**: 1
- **类别**: build|upstream-defect|cross-platform
- **触发工具**: conan|clang|gcc|make|autoreconf
- **阶段**: compilation

## 错误特征

```
/src/rt-app_parse_config.c:768:54: error: use of undeclared identifier 'TRUE'
        data->period = get_int_value_from(obj, "dl-period", TRUE, 0) * 1000;
```

注意报错**不是**交叉编译独有：宿主 Ubuntu 22.04 + gcc 11 对未修改的同一份源码
`gcc -fsyntax-only` 也直接失败：

```
rt-app_parse_config.c:284:51: error: ‘TRUE’ undeclared (first use in this function)
  284 |         type = get_string_value_from(obj, "type", TRUE, def_type);
```

## 根因

`src/rt-app_parse_config.c` 有 28 处把 `TRUE`/`FALSE` 当作现成宏传入
`get_int_value_from()` / `get_string_value_from()` / `get_in_object()`，
但 `src/` 与 `libdl/` 全树没有任何 `#define TRUE` / `#define FALSE`，
autoconf 生成的 `src/config.h` 也不提供它们。

`TRUE`/`FALSE` 来自 X11/部分 BSD 头文件，**glibc 与 musl（OHOS 的 C 库）都不定义**，
所以这跟"交叉编译"或"OHOS"都无关——上游发布标签本身不可编译。

全树核查（期望 0 条定义）：

```bash
grep -rn "#define TRUE\|#define FALSE" src/ libdl/ | wc -l
```

## 影响范围

- rt-app 1.0，以及任何复用其配置解析代码的下游。
- 更一般地：任何假定 `TRUE`/`FALSE` 是"系统自带宏"的 C 代码（X11 时代遗留写法），
  在 musl/OHOS 这类不提供该宏的 libc 上必然编译失败。

## 推荐方案

**方法**: `grep-for-true-false-before-blaming-the-cross-compiler`

1. **先复现再归因**：报错时先用宿主 `gcc -fsyntax-only` 编译同一份源码。宿主同样失败
   ⇒ 上游缺陷，改源码即可，不必再往 OHOS 差异上找线索。这一步能省掉大量误工。
2. **在共享头文件里守卫式定义**：加到所有编译单元都包含的 `src/rt-app_types.h`
   （而不是单个 `.c`），带 `#ifndef` 保护：

   ```c
   #ifndef TRUE
   #define TRUE 1
   #endif
   #ifndef FALSE
   #define FALSE 0
   #endif
   ```

3. **在 `notes.md` 写明"上游标签在任何 libc 上都不可编译"并附宿主复现命令**，
   避免后续评审反复怀疑是本次适配引入的回归。
4. **不要用 `__OHOS__` 包一层**：通用守卫定义在 glibc 上同样安全，加平台宏反而
   违反补丁禁用平台宏的口径。

## 验证命令

```bash
# 1) 确认全树确实没有定义（期望 0）
grep -rn "#define TRUE\|#define FALSE" src/ libdl/ | wc -l

# 2) 宿主端复现，证明与交叉编译无关
gcc -fsyntax-only -I. -I../libdl -I<json-c>/include src/rt-app_parse_config.c

# 3) 打补丁后重建
conan create . --name=rt-app --version=1.0 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```

## 取证记录

- 包: rt-app 1.0（`archives/r/rt-app/1.0`）
- 补丁: `patches/0001-define-bool-and-include-sched.patch`
- 环境: OHOS aarch64，clang 15.0.4，profile `ohos-aarch64-wsl`
- 上游提交: `a477fe226cbe3652a5d30a191fdf84ebbf744d25`（tag v1.0）
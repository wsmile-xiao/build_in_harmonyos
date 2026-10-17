# DRAFT-b64c-0.1.0-custom-alloc-macro-guard：-D 宏替换与 extern 守卫名不一致 → clang 隐式声明报错

## 问题（b64.c 0.1.0 真机实证）

`make test USE_CUSTOM_MALLOC=true` 编译失败：

```
buffer.c:15:13: warning: call to undeclared function 'custom_malloc';
     ISO C99 and later do not support implicit function declarations
buffer.c:15:11: error: incompatible integer to pointer conversion
     assigning to 'char *' from 'int' [-Wint-conversion]
```

## 根因

| 方 | 写法 | 问题 |
|----|------|------|
| Makefile | `CFLAGS += -Db64_malloc=custom_malloc -Db64_realloc=custom_realloc` | 定义的是**替换宏名** `b64_malloc` |
| buffer.c | `#ifdef b64_USE_CUSTOM_MALLOC extern void* b64_malloc(size_t); #endif` | 守卫用的是**独立开关** `b64_USE_CUSTOM_MALLOC`（从未被定义）→ extern 声明被跳过 |

于是 `b64_malloc(...)` 被替换成 `custom_malloc(...)` 但无声明 → clang 15 把隐式声明当 error。老 GCC 只警告，故上游 Travis（GCC）时代未暴露。

## 方案（最小补丁，已进 patches/0001-buffer.c.patch）

```c
#if defined(b64_USE_CUSTOM_MALLOC) || defined(b64_malloc)
extern void* b64_malloc(size_t);
#endif
```

`b64_realloc` 同理。默认构建（无 -D 无开关）行为完全不变；两套上游约定都正确声明。

## 验证

- `make test USE_CUSTOM_MALLOC=true && ./test` → TAP `1..8` 全 PASS（exit 0）
- `make test && ./test` → 8/8 PASS（默认路径回归无损）
- conan-verify 八道门禁 PASS

## 适用边界

- 任何 clib/类 clib 风格（Makefile + -D 标识符替换自定义分配器等）的 C 库；
- 同样适用于"宏替换标记"与"条件编译开关"命名不一致的任何代码库；
- 与 E063 的区别：E063 是 `-Werror` 把警告升级为错误（禁 -Werror 解决），本条是**声明被跳过导致的隐式声明**（补守卫解决），二者根因不同。

## 反例

- 全局 `-Wno-implicit-function-declaration` 掩盖 → 真实类型错误被隐藏；
- 改写调用点 `b64_malloc(x)` → 破坏默认构建路径，补丁面失控。
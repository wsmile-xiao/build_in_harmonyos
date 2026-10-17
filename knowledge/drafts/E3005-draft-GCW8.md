# DRAFT-E3005：cmocka uintptr_t 编译器内建宏守卫（typedef redefinition）

- **触发实例**：samba 4.21.0 适配（2026-09-21，分支 feat/samba-4.21.0，third_party/cmocka 编译）
- **错误签名**：`redefinition of typedef 'uintptr_t'` / `conflicting types for 'uintptr_t'`
- **类别**：headers / libc 冲突 / compat
- **严重度**：2（编译错误，但守卫可通用修复）

## 症状（可复现）

cmocka.h 自行 `typedef unsigned long uintptr_t;`，而新版 libc 已通过标准头提供 `uintptr_t`，二者叠加报错：

```text
redefinition of typedef 'uintptr_t'
note: 'uintptr_t' previously declared here
```

## 根因

bundled 的 third_party/cmocka 头文件自带 `uintptr_t` typedef，与新版 libc（musl/新版 glibc）提供的 `uintptr_t` 冲突。修复应基于**编译器内建宏机制**（`__UINTPTR_TYPE__` 是编译器内建的类型底层宏——给 uintptr_t 用的底层类型），而非平台宏。

## 方案

在 cmocka.h 中加守卫：

```c
#ifdef __UINTPTR_TYPE__
/* 编译器内建已提供 uintptr_t 的底层类型 → 跳过自定义 typedef，避免 redefinition */
#else
typedef ... uintptr_t;   /* 原自定义 typedef，仅当编译器不内建时 */
#endif
```

对应 patch：`0005-third_party-cmocka-cmocka.h.patch`。

## 验证

```sh
echo '__UINTPTR_TYPE__' | gcc -dM -E -x c - | grep UINTPTR   # 确认内建宏存在
make && 运行依赖 cmocka 的测试/消费者   # 编译+运行全过
```

## 边界 / 禁止

- 用编译器内建宏 `__UINTPTR_TYPE__`，**不是**平台宏 `__OHOS__`（R8/PF5 合规）；
- 不在 `#ifdef __OHOS__` 下改 typedef（其它平台会漏修或误判）；
- 若编译器不内建，则走 `#include <stdint.h>` 原生分支，不做硬改。

## 关联

- 触发 PR：!11515。

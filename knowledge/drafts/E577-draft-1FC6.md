# E577: glibc 内部类型/宏在 musl 下编译失败（bits/types.h、__uintN_t、__WORDSIZE、__glibc_likely）

## 错误特征

```
fatal error: 'bits/types.h' file not found
error: unknown type name '__uint8_t' / '__uint16_t' / '__uint32_t' / '__uint64_t'
error: unknown type name '__intmax_t' / '__uintmax_t'
use of undeclared identifier '__glibc_likely'
ld.lld: error: undefined reference ... __glibc_unlikely
```

实测（libkysdk-base 3.0.1.3，OHOS aarch64 / clang 15 / musl）：
`src/utils/kyutils.h:40:10: fatal error: 'bits/types.h' file not found`，修掉后依次暴露
`__uint8_t` 等未定义类型，链接阶段再暴露 `__glibc_likely/__glibc_unlikely`。

## 根因

上游代码直接引用 glibc 内部实现（不属于任何 POSIX 标准）：

| glibc 内部符号 | 位置 | musl 状态 |
|---|---|---|
| `<bits/types.h>` | `kyutils.h` | 头文件不存在 |
| `__uint8_t`/`__uint16_t`/`__uint32_t`/`__uint64_t`、`__intmax_t`/`__uintmax_t` | `kyutils.c` 里 `typedef __uint64_t uint64_t;` 等 | 类型不存在 |
| `__WORDSIZE`、`__PRI64_PREFIX`、`__PRIPTR_PREFIX` | 同上（`#define PRIu64 __PRI64_PREFIX "u"`） | 宏不存在 |
| `__glibc_likely`/`__glibc_unlikely` | `format.c`、`klog_mqueue.c` 分支提示 | 宏不存在 |

另有连带效应：musl 把 `isdigit`/`isalpha` 等实现为**宏**并做类型检查，
glibc 下仅告警的传参错误（如 `isdigit(p)` 传指针）在 musl 下变成硬错误。

## 推荐方案

1. `<bits/types.h>` → `<sys/types.h>`；
2. 删除 `__` 前缀 typedef 重定义块，改用 `<stdint.h>`/`<inttypes.h>`
   （`uint64_t`、`intmax_t`、`PRIu64`、`UINTMAX_MAX` 均由标准头提供）；
3. `__glibc_likely(x)` / `__glibc_unlikely(x)` → `(x)`（分支提示，非功能语义）；
4. 宏化字符判断函数必须传 `int` 值：`isdigit((unsigned char)*p)`。

## 验证

```
make -j4      # 编译与链接均通过
```
libkysdk-base 实测：上述 4 类修改后 `make -j4` EXIT=0，上游测试 12/12 通过。

## 相关条目

- **E194**（`similar_to`）：musl 提供的头文件集不完整（缺 `bits/alltypes.h` 等核心类型定义）
  导致的同类编译失败，与本条目同源，处置方式一致（改用标准头或自带等价定义）；
- **E169**（`similar_to`）：OpenHarmony 缺 GNU 扩展头（`argp.h`）——同属「GNU/glibc 专属接口
  在 musl 下不可用」，同样只能改用标准接口或自带替代实现，不能靠 `-I` 指向 glibc 头绕过。

## 关键词

bits/types.h, __uint8_t, __intmax_t, __WORDSIZE, __PRI64_PREFIX, __glibc_likely,
__glibc_unlikely, musl, OHOS, glibc internals, isdigit 宏, 移植

## 申报定位（供主编参考）

- **路径**：路径 B（贡献创新 / 知识库扩展）候选**主体**。
- **为什么算新知识**：`bits/types.h` / `__WORDSIZE` / `__glibc_likely` 等签名在
  `knowledge/graph/` 中**零命中**；最近的同族条目只有 E194（musl 头集不完整，缺 `bits/alltypes.h`）
  与 E169（缺 GNU 扩展头 `argp.h`），二者均为「单个头/接口缺失」，而本条目是
  **glibc 私有类型定义 + 私有宏 + 宏化字符判断函数**三类问题在同一适配中连续暴露的完整处置链，
  含 musl 把 `isdigit` 实现为**做类型检查的宏**这一连带效应（glibc 下仅告警的 `isdigit(p)`
  在 musl 下变硬错误）——该连带效应在上述条目中未覆盖。
- **编号变更说明**：本草稿最初编号为 `E430`，但 `knowledge/graph/E430.kv`
  （`index.tsv:655`，PR !6427，doc/E2152.md，主题为 GitHub Release 资产摘要绑定）
  已是**正式条目**，两者同名会造成合入覆盖，故改为当前编号。
- **可复用性**：任何直接 include glibc 私有头或使用 `__glibc_*` 宏的上游库都会命中间一条目。

# DRAFT-ell-0.71-ohos-keyctl-dh-params-union-no-private-member

> 实证包：**ell 0.71**（平台任务 14896，2026-10-06，B 机）
> 症状族：**OHOS 内核 UAPI 头与上游/libc 视图不一致**（与 `E091` 同族、不同签名与解法）

## 错误特征（逐字）

```
ell/key.c:199:31: error: field designator 'private' does not refer to any field
                            in type 'struct keyctl_dh_params'
  struct dh_params params = { .private = private,
                              ^
ell/key.c:199:31: error: no member named 'private' in 'struct keyctl_dh_params'
```

`make` 链路中的位置：`ell/libell.la` → `make[1]: *** [Makefile:2046: ell/key.lo] Error 1`。

## 最小复现（30 行级、不含三方库代码）

```c
#include <linux/keyctl.h>
struct keyctl_dh_params p = { .private = 1, .prime = 2, .base = 3 };
```

```console
$ clang -xc -c - -o /dev/null < probe.c
error: field designator 'private' does not refer to any field in type 'struct keyctl_dh_params'
error: no member named 'private' in 'struct keyctl_dh_params'
```

对照（把 `.private` 换成 `.priv`）：

```console
$ clang probe2.c -o probe2 && ./probe2
priv=1          # 编译通过并输出 => OHOS 实际成员名是 priv
```

## 根因

OHOS 内核 UAPI 头 `linux/keyctl.h` 中：

```c
struct keyctl_dh_params {
  union {
#ifndef __cplusplus
    __s32 __linux_private;
#endif
    __s32 priv;
  };
  __s32 prime;
  __s32 base;
};
```

主线 Linux / glibc-musl 视图则是平铺的 `int private; int prime; int base;`。

ell 的 `key.c` 采用"系统头已提供 `KEYCTL_PKEY_QUERY` 就改用系统 struct"的常见写法：

```c
#ifndef KEYCTL_PKEY_QUERY
  ... 自备 struct dh_params { int32_t private; int32_t prime; int32_t base; };
#else
  /* When KEYCTL_PKEY_QUERY is defined by the kernel, the
   * struct keyctl_dh_params declaration is valid.   */
  #define dh_params keyctl_dh_params
#endif
...
struct dh_params params = { .private = private, .prime = prime, .base = base };
```

OHOS 头**有** `KEYCTL_PKEY_QUERY` ⇒ 走 `#define` 分支 ⇒ 用的是 OHOS 的 union 形状 ⇒ `.private` 设计符无对应成员 ⇒ 编译期失败。上游那句注释的隐含假设（"有该宏即结构体形状有效"）在 OHOS 上不成立。

**布局是兼容的**：union 内仅一个 `__s32` 成员，整体仍是 3×4 字节、字段序 `private/prime/base` 不变，故 `syscall(__NR_keyctl, KEYCTL_DH_COMPUTE, &params, ...)` 交给内核的布局一致 —— 这是解法等效性的依据，**问题只在编译期字段名，不在 ABI**。

## 解法（`use-upstream-shaped-struct-under-platform-guard`）

在走系统 struct 的 `#else` 分支里，用 `#ifdef __OHOS__` 守卫重新声明上游同形状的私有 struct：

```c
#else
/* When KEYCTL_PKEY_QUERY is defined by the kernel, the
 * struct keyctl_dh_params declaration is valid.
 */
#if defined(__OHOS__)
/* OHOS ships struct keyctl_dh_params as a union whose members are
 * __linux_private / priv -- there is no 'private' member, so the
 * .private designator in kernel_dh_compute() does not compile.
 * Reuse the upstream-shaped struct declared above instead. */
struct dh_params {
        int32_t private;
        int32_t prime;
        int32_t base;
};
#else
#define dh_params keyctl_dh_params
#endif
#endif
```

### 为什么不用"调用点改 `.priv`"

- 补丁会与上游代码分叉（所有构造点都要 `#ifdef` 包住），回移植成本高；
- 非 OHOS 平台上 `.priv` 不存在，必须再包一层平台宏，等于同一处写两次平台分支；
- 保留上游形状意味着**只动声明归属、不动语义**，`KEYCTL_DH_COMPUTE` 路径与传参完全不变。

### 已尝试 / 不采用

| 方案 | 结果 |
|---|---|
| 调用点改 `.priv = ` | 编译通过（探针实证），但如上所述平台分叉大，不采用 |
| 删除 `#define dh_params keyctl_dh_params` 让它无条件用自备 struct | 可行，但会影响非 OHOS 平台的既有行为，不采用 |
| `sed` 改系统头 | 禁止（系统头不可改，且越权） |

## 验证

```console
$ make -j1            # 前一版在 ell/key.lo 报上述错误
  CCLD     ell/libell.la
  CCLD     tools/certchain-verify
  ...
  CCLD     ell/libell.la
$ echo $?              # 0
```

- 修复前：`make[1]: *** [Makefile:2046: ell/key.lo] Error 1`、`make: *** [Makefile:1307: all] Error 2`
- 修复后：`make -j1` **RC=0**，`ell/libell.la` 与 5 个 tools 全部链接成功

## 适用范围 / 解除条件 / 反例

- **适用**：任何同时出现 `struct keyctl_dh_params` 与 `.private` 设计符、且构建目标是 OHOS 内核头的 C/C++ 项目（`KEYCTL_DH_COMPUTE` DH 密钥派生面）。
- **解除**：上游改用 `priv` 或改用 `offsetof`/逐字段赋值后不再需要。
- **反例（不要套用）**：
  - 结构体**布局**本身不同（不止字段名）时，不能只改声明归属 —— 必须先逐字节核对；
  - 若代码读取的是 OHOS 特有字段（如 `__linux_private`），则相反方向才对。

## 查重与新增价值

四范围查重（2026-10-06）：

| 范围 | 结果 |
|---|---|
| `经验文档/适配经验汇总.md` | 0 命中（无 ell/libell/keyctl 条目） |
| `knowledge/graph/index.tsv`（540 条） | **0 命中**：`keyctl_dh`/`keyctl`/`field designator` 全无匹配 |
| `经验文档/经验库/` | 0 命中 |
| `经验文档/B草稿库/` | 0 命中（14 条通用池无此机制） |

同族最接近者 **E091**（`sockaddr_storage` 重定义，`linux/socket.h` vs `sys/socket.h`）：同属"OHOS 内核 UAPI 与上游视图不一致"家族，但**签名不同**（重定义 vs 字段缺失）、**解法不同**（宏改名 vs 改用上游形状 struct），按 `手册/03 §6.2` hit 四条件第 2 条不构成 hit。

**新增价值**：给出"OHOS 把内核 UAPI 结构体成员改名/包 union"这一形态的判据（源码同时出现 `struct X` 与 `.member` 时先探该成员是否存在）与等效性核对方法（布局一致 ⇒ 只动声明归属）。

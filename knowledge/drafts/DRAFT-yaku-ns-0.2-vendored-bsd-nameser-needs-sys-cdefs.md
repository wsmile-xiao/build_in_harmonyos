# 内置老 BSD `arpa/nameser.h` 缺 `<sys/cdefs.h>` → musl 全量编译失败（DRAFT 草稿）

> 状态：草稿（DRAFT，待人工审核）｜来源：yaku-ns 0.2 OHOS aarch64 适配（2026-10-03）｜severity: 3

## 问题

yaku-ns 0.2 在 OHOS（musl）上第一次编译，**每个翻译单元都失败**：

```
./nameser.h:253:1: error: unknown type name '__BEGIN_DECLS'
./nameser.h:304:27: error: expected ';' after top level declarator
       extern  u_int16_t  _getshort __P((const u_char *));
./nameser.h:349:1: error: unknown type name '__END_DECLS'
In file included from ./ens.h:279:31: error: unknown type name 'HEADER'
       int build_header(byte **dest, HEADER *hdr, int aa);
...
8 errors generated.
```

看起来像是源码本身写错了。

## 根因：靠"传递包含"活着的私有头文件

`nameser.h` 是 **1993 年版 BSD `<arpa/nameser.h>` 的逐字拷贝**，被内联进源码树当私有头用。
这类头文件的共同特征：

1. 用 `__BEGIN_DECLS` / `__END_DECLS` / `__P(...)` 控制 C++ 链接可见性与原型形态；
2. 用 `u_char` / `u_int16_t` / `u_int32_t` 等 BSD 传统 typedef；
3. **不 include 任何定义它们的头文件**——当年靠某个"总是先被包含"的头顺带带入。

两种 libc 的差别就是全部原因：

| libc | `<features.h>` 是否拉进 `<sys/cdefs.h>` | 结果 |
|---|---|---|
| glibc | **会**（`<features.h>` → `<sys/cdefs.h>`） | 侥幸编过，几十年来无人察觉 |
| musl（OHOS） | **不会** | 每个编译单元炸 |

因为该头同时定义了 DNS 报文头结构 `HEADER`，错误会连带扩散成一串看似无关的
`unknown type name 'HEADER'`，把排查方向带偏（容易误以为是 `ens.h` 的问题）。

## 处置：让头文件自包含

在 patch 里补两行 include，放在该头第一个实际声明之前：

```diff
+#include <sys/cdefs.h>   /* __BEGIN_DECLS / __END_DECLS / __P */
+#include <sys/types.h>   /* u_char / u_int16_t / u_int32_t */
```

glibc 与 musl 都从这两个头提供所需定义。glibc 下这两行是冗余的（本来就能编过），
但**显式声明依赖是正确写法**：不引入平台宏、不改任何逻辑、零行为风险。

## 禁止的做法

1. **在包内自己 `#define __BEGIN_DECLS` / `__P`**：会把 glibc/musl 的原型形态与
   链接可见性语义搅乱，且掩盖真正的缺失包含。
2. **给两个 libc 写出两份头文件内容**（`#ifdef __OHOS__` / `#ifdef __GLIBC__` 分支）：
   制造维护分叉并掩盖缺陷，同时踩 R8（补丁禁用平台宏）。

## 预防

- 预扫描规则：`__BEGIN_DECLS|__END_DECLS|__P\(\(|u_int16_t|u_int32_t` 出现在
  项目自带的 `*.h` 中，即为高风险信号。
- 遇到「glibc 能编、musl 全红」且错误集中在**某个自带头文件**里时，先确认这些
  符号是**未定义**而非拼错：
  ```sh
  grep -n '__BEGIN_DECLS\|__P(\|u_char\|u_int16_t' <头文件>
  ```
  成对出现、无自定义同名宏 ⇒ 依赖传递包含，补 include 即可。
- 凡把老 BSD 头文件内联进源码树的 C 项目（DNS/网络类老工具尤甚）都属同族。
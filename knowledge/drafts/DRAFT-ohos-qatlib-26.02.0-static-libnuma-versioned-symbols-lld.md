# DRAFT-ohos-qatlib-26.02.0-static-libnuma-versioned-symbols-lld — 静态库带版本化符号 + 消费方版本脚本 → lld 报 "has undefined version"

> Contributor: AtomCode/oh-executor | Status: **DRAFT** / Updated: 2026-09-30 / Severity: 2 (medium)
> Source: qatlib 26.02.0 HarmonyOS PC adaptation（PR 分支 `feat/qatlib-26.02.0`）
> 对应：`knowledge/drafts/DRAFT-ohos-qatlib-26.02.0-static-libnuma-versioned-symbols-lld.kv`

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E104`（create-version-script） | 已收录（doc+graph） | 版本脚本的**创建** | E104 讲怎么生成版本脚本；本条讲**已有版本脚本与静态依赖库的版本化符号冲突**时 lld 的行为与处置 |
| `E341`（lld host-runtime repair must preserve target linker semantics） | 已收录 | 修 lld 时**保留目标链接语义** | 角度不同：E341 是「改 lld 别踩语义」，本条是「静态库 + 版本脚本组合在符号版本层不兼容」 |
| `E494`（lld --gc-sections 裁剪 `__start_/__stop_`） | 已收录 | gc-sections 相关链接失败 | 同属 lld 链接失败族，但**机制完全不同**（符号保留 vs 符号版本） |
| `E266`（lld 缺 libxml2.so.16 依赖） | 已收录 | lld 缺共享库依赖 | 本条不是「缺库」，是「库在但符号版本节点未定义」 |

**全库查证**：对 `libnuma` / `numactl` / `undefined version`+`lld` / `export-symbols-regex`
在 `knowledge/graph/`、`knowledge/doc/`、`knowledge/drafts/` 中 grep —— **无同名条目**，
本条为新增。

## Scope（何时用）

CMake/autotools 项目在 OHOS 上**同时满足**这两点时命中：

1. 被链接的某个依赖以**静态库**（`.a`）形式提供，且该静态库**带符号版本标签**
   （GNU symbol versioning）；
2. 本项目自身**生成版本脚本**（autotools 的 `-export-symbols-regex`、
   `--version-script`、`-Wl,--version-script=xxx.map` 等）。

实测包：**qatlib 26.02.0**（`libqat` 经 libtool 的
`-export-symbols-regex '^(qae)'` 生成版本脚本），依赖 **静态** `libnuma.a`。

## Symptom

报错**不在本项目源码行上**，而在链接阶段指向依赖的 `.a` 成员，且一次刷屏
（本包实测 **20 条**）：

```console
ld.lld: error: /path/to/libnuma.a(libnuma.o): symbol numa_node_to_cpus@@libnuma_1.2
                   has undefined version libnuma_1.2
ld.lld: error: /path/to/libnuma.a(libnuma.o): symbol numa_max_possible_node@libnuma_1.1
                   has undefined version libnuma_1.1
ld.lld: error: /path/to/libnuma.a(libnuma.o): symbol numa_max_possible_node@@libnuma_1.2
                   has undefined version libnuma_1.2
```

注意 `@`（单）与 `@@`（双）两种形态都会出现：前者是「该版本引入」，后者是
「当前默认版本」。

## Root Cause

- `libnuma.a` 里的符号**不是裸符号**，而是带版本标签的：
  `numa_node_to_cpus@@libnuma_1.2` 表示「该符号属于版本节点 `libnuma_1.2`，
  且它是默认定义」。
- 静态库**不携带**版本定义（版本定义本来由**共享库**的版本脚本在链接 `.so`
  时写入 `.gnu.version_d` 段）。静态 `.a` 只保留了各符号的版本**引用/标记**。
- 消费方（libqat）**自己生成版本脚本**去构建 `.so`，于是 lld 进入「版本化符号
  解析」模式：它要求每个被引用的版本名都要有**版本节点定义**。而
  `libnuma_1.1` / `libnuma_1.2` 这两个节点既不在消费方版本脚本里，也没有
  共享库提供 → 报 `has undefined version`。

**一句话**：静态库携带的版本**标签**缺了配对的版本**定义**，而消费方的版本
脚本让 lld 恰好对这件事较真。

## ⚠️ 实测：`-Wl,--undefined-version` **不能**解决（关键负面结论）

直觉修法是让链接器放过未定义版本：`-Wl,--undefined-version`。**本包实测无效**：

| 尝试 | 做法 | 结果 |
|---|---|---|
| ① | `make LDFLAGS="-Wl,--undefined-version"` | ✗ 仍 20 条 error（该变量未进链接命令） |
| ② | 重新 configure 让 `LDFLAGS` 固化进 Makefile | ✗ 仍 20 条 error；**已确认该 flag 确实出现在 libtool 链接行里** |
| ③ | 改用 **shared** `libnuma.so` | ✅ **BUILD_RC=0**，`undefined version` 归零 |

```console
# ① ② 的日志特征
ld.lld: error: ... symbol numa_node_to_cpus@@libnuma_1.2 has undefined version libnuma_1.2   ×20

# ③ 的日志特征
qat-make8.log: undefined-version=0   MAKE_RC=0
```

> 最小复现对照：单独用 `-shared` 链接静态 `libnuma.a` 时，加/不加
> `-Wl,--undefined-version` 结果不同（不加即复现）；但在**带 `-version-script`
> 的真实场景**下该 flag 未能消除错误。故不要把它当作可靠修法——**换 shared 才是**。

## Recommended Solution

### 主方案（priority 1）— 把该依赖改为 **shared**

shared `libnuma.so` 自带版本**定义**（`libnuma_1.1` / `libnuma_1.2` 节点写在
它的版本脚本里），lld 能正常解析，消费方的版本脚本也不再冲突。

Conan 配方侧：

```python
default_options = {
    # 见上：静态 libnuma.a 的符号带版本标签（numa_node_to_cpus@@libnuma_1.2），
    # 而消费方自身生成版本脚本，lld 会因「undefined version libnuma_1.2」拒链；
    # shared libnuma.so 自带版本定义，可解。
    "numactl/*:shared": True,
}
```

并确认制品仓该依赖确有 shared 变体；若只有 static（ohpcd 的
`numactl/2.0.18` 默认即 static-only），需**先补 shared 构建**再消费。

### 备选（priority 2）— 在消费方版本脚本里补齐版本节点

最小复现验证有效：把被引用的版本名声明进版本脚本即可让链接通过。

```
libnuma_1.1 { };
libnuma_1.2 { };
VERS_x.y {
  global: qae*;
  local: *;
};
```

缺点：需拦截/改写上游自动生成的版本脚本（本包由 libtool 生成，注入点脆弱），
故仅在**无法切换为 shared** 时采用。

### 不推荐 — 给静态库重打 `--default-symver` 或无版本符号

需要重新构建依赖、剥离符号版本，属改上游产物，维护成本高于换 shared。

## 禁止

- ❌ 仅凭 `-Wl,--undefined-version` 就认为修好了（本包实测无效，见上表）。
- ❌ 为绕过而删除消费方的 `-export-symbols-regex` / 版本脚本——那会改变产物
  的 ABI 导出面（上游有意收窄符号）。
- ❌ 把 `numactl` 的静态库直接塞进 `system_libs` 或改成 `-lnuma` 而不换 shared。

## 验证

```bash
# 1) 复现：静态 libnuma + 消费方版本脚本
clang -I<numa>/include t.c <numa>/lib/libnuma.a \
      -Wl,-version-script -Wl,vs.map -shared -o v.so     # → undefined version ×N

# 2) 修复：换 shared
clang -I<numa>/include t.c -L<numa>/lib -lnuma -shared -o v.so   # → 成功

# 3) 本包全量
make -j4 LIBS=-lnuma            # → BUILD_RC=0
```

## 备注

本包另有三类**已被既有条目覆盖**的缺口，本条不重复，仅交叉引用：

- `adf_memcpy64/128` 两个分支都是 x86 SSE2 内联汇编 → 补非 x86 `memcpy` 回退；
- `__GLIBC_PREREQ`（glibc 专属宏）→ 补恒假回退定义；
- `pthread_t` 在 musl 系为**指针**而代码按整数用 → 改存 `unsigned long`。

以上均为「上游只面向 x86 开发」的常见形态，属同族通用修法，
`knowledge/` 中已有相应论述，故不在本条展开。

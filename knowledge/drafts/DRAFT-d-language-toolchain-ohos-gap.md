# D 语言项目的 OHOS 适配：工具链经 ohpcd 取得，无 dub 时走 GNUmakefile

**草稿 ID**: `DRAFT-d-language-toolchain-ohos-gap`
**来源**: gir-to-d 0.23.3 在 OpenHarmony PC（aarch64-unknown-linux-ohos）的适配
**日期**: 2026-09-18

---

## 一句话结论

OHOS 上 **D 语言项目是可适配的**——工具链能经 ohpcd 的 `ldc/1.42.0` + `llvm/20.1.0`
取得，**缺 `dub` 并不构成硬阻塞**（上游三条构建路径里只有 `dub.json` 需要它）。
真正的坑在别处：语言预检的静默误判、ldc2 的 import/链接路径、以及新前端对
`inout` 的收紧。

---

## 错误特征

**坑 ①：语言预检把 `.d` 静默判成 `c`（不报错，最阴）**

D 不在框架 `LANG_ENUM`（`c/cpp/rust/python/go/perl/lua/nodejs/java/bash/mixed/other`），
`.d` 也没登记进 `lang_detect` 的 `_EXT_LANG`。后果不是报「不支持」，而是**回退判为 `c`**，
后续流程会拿 C/C++ 编译器去编 `.d` 文件。属于**误判而非拒绝**，不留意就会一路错到底。

**坑 ②：`ldc2: command not found`（表面现象）**

设备侧 `dmd` / `ldc2` / `ldmd2` / `gdc` / `dub` **全部没有**。但这只说明「没装」，
**不等于「装不上」**——须先查制品仓：

```text
conan search "ldc/*" -r=ohpcd   → ldce/1.42.0   ✅（os=OHOS, arch=armv8）
conan search "dub/*" -r=ohpcd   → Found 0 pkg/version recipes  ❌
```

**坑 ③：`Error loading shared library libLLVM.so.20.1`（看着像缺库，其实是没设路径）**

`ldc2` 自身是动态链接到 `libLLVM.so.20.1` 的：

```text
$ objdump -p <ldc>/bin/ldc2 | grep NEEDED
  NEEDED   libLLVM.so.20.1
```

裸跑二进制（无 `LD_LIBRARY_PATH`）必然报这个错，但**该库并不缺**——`llvm/20.1.0`
制品的 `lib/` 里就有（`ldc` 的 recipe 已 `requires("llvm/20.1.0")`，会由
`buildenv_info`/`runenv_info` 注入）。**别据此判定缺依赖。**

**坑 ④：`object.d` / `std.algorithm` not found（import 路径）**

ldc2 自带的默认 import 搜索路径在本制品上不可用，必须显式给 Phobos 源码目录：

```text
$ ldc2 -of=out t.d
Error: unable to read module object ...      # 或 std.algorithm not found
$ ldc2 -I<ldc>/include/d -of=out t.d         # 加上即可
```

**坑 ⑤：链接失败（库搜索路径）**

同理需显式给出：

```text
-L-L<ldc>/lib
```

**坑 ⑥：`only parameters or stack-based variables can be 'inout'`**

LDC 1.42.0 的 DMD 前端（v2.112.1）拒绝 `inout typeof(this)`：

```text
core/internal/newaa.d(110): Error: variable `core.internal.newaa.Entry!(string, inout(Node)*).Entry.value`
  - only parameters or stack-based variables can be `inout`
core/internal/newaa.d(375):        template instance `core.internal.newaa.Entry!(string, inout(Node)*)` error instantiating
```

---

## 根因

**① 框架层**：`LANG_ENUM` 无 D，`_EXT_LANG` 无 `.d` → 预检静默回退判为 `c`。

**② 工具链层**：设备无 D 工具链，但 ohpcd 有——`ldc/1.42.0` 提供

| ldc 包内提供 | 用途 |
|---|---|
| `bin/ldc2`、`bin/ldmd2` | 编译器（`ldmd2` 是 dmd 兼容前端） |
| `lib/libdruntime-ldc.a` | druntime（`core.*`） |
| `lib/libphobos2-ldc.a` | Phobos 标准库（`std.*`） |
| `include/d/` | **Phobos/druntime 源码**（import 路径） |
| recipe 注入 `DC`/`DMD`/`PATH`/`LD_LIBRARY_PATH` | 免手工配置 |

故 `std.*` / `core.*` 全部可满足。**唯一真缺的是 `dub`。**

**③ 构建入口层**：`dub` 缺失只挡住三条路径中的一条——

| 构建路径 | 需要什么 | dub 缺失时 |
|---|---|---|
| `dub.json` | **dub** | ❌ 走不通 |
| `meson.build` | meson（✅ 有）+ D 编译器 | ⚠️ 但常用 `vcs_tag(['git','describe'])` 取版本，**tarball 无 `.git`** |
| `GNUmakefile` | 仅 `DC`（按 dmd→ldc→ldc2→gdc 探测） | ✅ **走通** |

**④ 编译器层**：`core.internal.newaa` 用 const 限定的 Key 实例化时，
`const(inout(Value[Key]))` 无法转换为所需的 `inout(const(Value[Key]))`。
即**新前端收紧了 `inout` 在「模板实例化出的成员/参数」上的用法**，
老代码里 `inout typeof(this)` 这类写法会编译失败。

---

## 正确做法

### ① 判定构建路径：先 `ls`，别默认 dub

```bash
ls Makefile GNUmakefile Build.PL Makefile.PL meson.build dub.json inc/
```

有 `GNUmakefile` / `Makefile` 且自探测 `DC` 的，**优先它**——不需要 dub。

### ② 配方：tool_requires + 显式三参数

```python
def build_requirements(self):
    self.tool_requires("ldc/1.42.0")   # llvm/20.1.0 由其 recipe 自动带入
```

```makefile
make -f GNUmakefile DC=ldc2 GIR_TO_D_VERSION=v<ver> \
  DCFLAGS="-O -I<ldc_pkg>/include/d" \
  LDFLAGS="-L-L<ldc_pkg>/lib"
```

三个参数**缺一即失败**（均为实测）：

| 参数 | 作用 |
|---|---|
| `DC=ldc2` | 显式指定编译器（避免误选 dmd/gdc） |
| `-I<ldc>/include/d` | ldc2 默认 import 路径不可用 |
| `-L-L<ldc>/lib` | 否则链接失败 |
| `GIR_TO_D_VERSION=v<ver>` | tarball 无 `.git` 时，构建脚本会回退到上游写死值，导致二进制内嵌版本与包版本不符 |

> 版本注入实测对照（`import("VERSION")` 编进二进制）：
> 不传 → `GIR to D v0.23.1`；传 `v0.23.3` → `GIR to D v0.23.3`。

### ③ `inout` 收紧：改为 `scope const`（固化为 patch）

```diff
-	bool opEquals(inout typeof(this) that) inout nothrow pure @safe
+	bool opEquals(scope const typeof(this) that) const nothrow pure @safe
```

`const` 形式是现代 D 惯用法，mutable 与 const 接收者均可用。
**该补丁可用性须实测确认**：本例中未打补丁的原始源码报同一错误，故补丁必需。

---

## 禁止做法

| # | 禁止 | 原因 |
|---|---|---|
| 1 | 把 `.d` 交给 C/C++ 编译器 | 预检误判被静默吞掉的典型后果，必然失败且根因被误记为 C 编译错误 |
| 2 | 在配方里 `export LD_LIBRARY_PATH=<conan 缓存绝对路径>` | 路径随构建机与 revision 变化，不可复现，且绕过 recipe 的 env 注入机制 |
| 3 | 在 `build()` 里 `sed -i` 改源码而不固化 patch | 改动不可审计、无法复现，违反补丁固化要求 |

---

## 兜底方案

若项目**仅有 `dub.json`**（无 Makefile / meson.build），或构建流程强依赖 dub 的
registry 与依赖解析，则须**先立项 `dub` 工具链包**（ohpcd 目前无该制品）。
在此之前按 **R47 上报 `env_unsupported`**，不得伪造通过。

> ⚠️ 本条也是本次适配的教训：最初正是按「设备无 D 工具链 + 仓内无 dub」上报了
> `env_unsupported`，**没有穷尽构建路径**——实际上 `GNUmakefile` 路径根本不需要 dub。
> **上报不可适配前，应先核查制品仓与所有可用构建入口。**

---

## 适用与语料对照

**适用**：所有 D 语言项目（`dub.json` / `meson.build` / `Makefile` 三类入口），
以及「语言不在 `LANG_ENUM`、需靠 `tool_requires` 引入整条工具链」的场景。

**实证来源**：gir-to-d 0.23.3（纯 D，GObject Introspection → D 绑定生成器），
适配结果：`conan create` 通过、消费者测试 14/14、1 个补丁。

**关联**：`similar_to: [E155]`（同为「纯语言级项目在 OHOS 的构建入口适配」范式）。

---

## 附：本次实证的关键数字

| 项 | 值 |
|---|---|
| D 编译器制品 | `ldc/1.42.0`（os=OHOS, arch=armv8） |
| 底层 LLVM | 20.1.0（`libLLVM.so.20.1`） |
| target | `aarch64-unknown-linux-ohos` |
| dub 制品 | **无**（`Found 0`） |
| 构建入口 | `GNUmakefile`（不需 dub） |
| 补丁数 | 1（`inout` → `scope const`） |
| 产物运行期依赖 | 仅 `libc.so` |

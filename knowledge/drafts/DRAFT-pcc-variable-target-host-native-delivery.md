# DRAFT-pcc-variable-target-host-native-delivery — 可变目标编译器没有宿主架构后端时的交付形态

> 配对的 kv：`knowledge/drafts/DRAFT-pcc-variable-target-host-native-delivery.kv`
> 来源：pcc（Portable C Compiler）1.2.0-devel-20220331 适配，PR !14348
> 分类：portability / retargetable-compiler

## 错误特征

pcc 默认（不指定 target）时：

```
configure: error: '$target' is not (yet) supported by pcc
```

## 触发条件

- 阶段: build（`./configure`）
- 软件类型: **可变目标编译器 / 汇编器 / 链接器**（retargetable toolchain）
- 前置: 该工具在目标平台（鸿蒙 PC = aarch64）**没有宿主 CPU 的后端**

pcc 的 `arch/` 下有 16 个后端：amd64、arm（32 位）、hppa、i386、i86、m16c、m68k、
mips、mips64、nova、pdp10、pdp11、pdp7、powerpc、sparc64、vax —— **没有 aarch64**。
`configure.ac` 无法把 target CPU 映射到后端时直接 `AC_MSG_ERROR`。

## 根因分析

这类工具的两件事必须分开看：

- **它自己能生成哪种机器码**（target）；
- **它自身在哪种 CPU 上运行**（host）。

缺宿主后端时，正确做法是把它当作「**在鸿蒙 PC 上运行的宿主编译器**」交付，
并显式指定它要生成的目标，例如 `--target=amd64-linux`。这是**产品定义**
（一个可变目标编译器必须被告知输出哪个后端），不是平台探测绕过。

已合入的同构先例：`chibicc 1.0.24.1`（在 OHOS/armv8 上运行、生成 x86-64）、
`asmc-linux 2.39`（ARM64 原生 host 汇编器，输出 x86-64 ELF）。

## ⚠️ 关键：host 三元组不要手传 `--host`

如果手工传 `--host=aarch64-unknown-linux-ohos`，`configure` 会进入**交叉编译分支**，
把 `CC_FOR_BUILD` 解析成宿主机自带的 `cc`/`gcc` —— 鸿蒙上并不存在。
后果是构建期生成器（pcc 的 `mkext`）失败，需要额外 `chmod` + 显式传 `CC_FOR_BUILD`
才能补救。

正确做法是让 `config.guess` **原生识别** host。pcc 实测（补丁 0001 之后、不传 `--host`）：

```
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking target system type... x86_64-pc-linux-gnu
```

去掉 `--host` 后 `configure` 不再走交叉分支，`CC_FOR_BUILD` 自动解析为 `$CC`，
构建期生成器**无需任何额外处理**。

## 推荐方案

**方法**: `host-native-tool-plus-explicit-foreign-target`

配方里只加 `--target=<需要的异构目标>`，**从不传 `--host`**：

```sh
./configure --target=amd64-linux
```

### 附带的构建参数（均经实测，非祖传）

- `-fcommon`：pcc 是 1990 年代风格 C 代码，多个翻译单元依赖 tentative definition；
  去掉后 `ld.lld: error: duplicate symbol: lineno`（make rc=2）。
- `-static`：OHOS 动态产物在构建机上无法执行（E544，缺 `/lib/ld-musl-aarch64.so.1`）。

## 已知限制（必须如实申报）

生成的 x86-64 产物**不能**在鸿蒙 aarch64 真机上运行或链接，需在 x86-64 环境使用。
若需求是「在鸿蒙上产出 aarch64 机器码」，应使用 clang/llvm。

## 与现有知识库的关系

- **E007** 讲的是「`config.guess` 不识别 HarmonyOS」的**症状与打补丁**；
  本条讲的是「无宿主架构后端时的**交付形态**」，以及 `--host` 会污染 `CC_FOR_BUILD` 的具体机制。
- **E490** 讲的是 autotools helper 的**执行位**问题，与本条无关，故各立一条。

# libatasmart 0.19:构建期 host 工具交叉坑——noop 捆绑生成产物是最小解

> 草稿(DRAFT)— 来自 libatasmart 0.19 HarmonyOS PC (aarch64) 适配的真实实践。
> 与 `.kv` 同 stem 配对。

## 问题

libatasmart 的顶层 Makefile 无条件执行:

```make
strpool/strpool:
	$(MAKE) -C strpool strpool

atasmart.strpool.c: atasmart.c strpool/strpool
	$(top_builddir)/strpool/strpool $< $@
```

native 构建无碍;**交叉构建**时 strpool 被目标链(aarch64 clang)编译,随后要在
构建机(x86_64)上执行——`cannot execute binary file`,make 中断。

## 关键事实与最小解

发行 tarball **已经包含生成好的 `atasmart.strpool.c`**:

```
tar -tJf libatasmart_0.19.orig.tar.xz | grep strpool
libatasmart-0.19/atasmart.strpool.c
```

生成步骤在交叉场景完全多余。最小解(补丁 0001,对 Makefile.in):

1. `SUBDIRS = strpool .` → `SUBDIRS = .`(不再编译 host 工具);
2. 生成规则 noop(使用捆绑产物):

```make
atasmart.strpool.c: atasmart.c
	@echo "using bundled atasmart.strpool.c (no strpool execution at build time)"
```

补丁应用在 configure **之前**(Makefile.in 是 configure 的模板),并做过
`patch -p1` 回环验证(应用结果与手工改后文件逐字节一致)。

### 为什么不用 CC_FOR_BUILD

- 需要 CI 提供 host gcc 并在配方里区分 build/host 编译器,假设多;
- 不改上游工具源码、补丁行数最小、行为可预期(echo 说明)。

## 覆盖判断

- `DRAFT-appstream-1.2.0-ohos-meson-glib-tool-binaries-wrapper`:工具**包装器**
  方案(生成 wrapper 脚本);本条目讲**生成规则 noop + 捆绑产物复用**,适用于
  "发行包已带生成物"的场景,是更小侵入的互补解。
- `DRAFT-E652-parasail-2.6.2-conan-autoreconf-triplet-pin`:tag archive 无
  configure 时的 autoreconf+triplet 路线;本条目的包自带 configure,无需那条链。

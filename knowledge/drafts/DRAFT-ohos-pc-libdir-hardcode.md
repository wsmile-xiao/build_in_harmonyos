# DRAFT-ohos-pc-libdir-hardcode — .pc 硬编码 libdir/includedir 时需同时改写

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: 🟡 medium | **Category**: conan / pkg-config / .pc / linking

## 相关既有条目（同族差异化定位）

本 skill 与既有 "pkg-config/.pc 改写" 条目共享依赖注入背景，但本条目是
**libdir/includedir 硬编码绝对路径**（非 `${prefix}` 派生）——非重复条目；
申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **dconf/polkit `_fix_pc_prefix`**（配方惯例，未沉淀为 E） | 配方实践 | 复制依赖 .pc 到 generators_folder 并改写 `prefix=` | 只改 `prefix=`——对 `${prefix}` 派生的 libdir/includedir 有效；本条目是 **libdir/includedir 硬编码为 /usr/lib、/usr/include**（不引用 ${prefix}）的变体，改写 prefix 不生效，需**同时改写** libdir/static_libdir/includedir |
| **E123**（meson 静态库 libintl） | 正式收录 | 链接期 g_libintl_* 符号缺失 | 非本题——那是**符号缺失**；本条目是**.pc 路径变量硬编码**导致 -L 指向 /usr/lib |

> 全库查证（2026-09-03）：`.pc libdir 硬编码`/`libdir=/usr/lib`/`unable to find
> library -l`（源自 .pc 路径）命中 0 条——无正面撞车；本条目为 dconf/polkit
> prefix 改写模式的增量。

## Scope（何时用）

在用 Conan `PkgConfigDeps`（或手动复制依赖 .pc 到 generators_folder 并改写
`prefix=`）构建时，若出现：

- 链接报 `unable to find library -lxxx`，但 `-L` 指向 `/usr/lib`（非 conan 包
  lib 路径）；
- 依赖包的 `.pc` 里 `libdir=/usr/lib`、`includedir=/usr/include`、
  `static_libdir=/usr/lib` **硬编码为绝对路径**，不引用 `${prefix}`；
- 只改写 `prefix=` 后问题依旧。

典型实例：systemd/261 链接 `libsystemd-shared` 时 `-lucontext` 找不到
（libucontext.pc 的 libdir 硬编码 `/usr/lib`）。

## Symptom

```text
ld.lld: error: unable to find library -lucontext
# 依赖 .pc 内容（改写 prefix= 后仍如此）：
libdir=/usr/lib          ← 硬编码，非 ${prefix}/lib
static_libdir=/usr/lib
includedir=/usr/include
Libs: -L${libdir} -L${static_libdir} -lucontext
```

## Root Cause

1. Conan `PkgConfigDeps` 生成的 .pc 通常用 `${prefix}` 派生 `libdir`/`includedir`，
   改写 `prefix=` 即可重定向；
2. 但部分包**自带**的 .pc（如 libucontext.pc）把 `libdir=/usr/lib`、
   `includedir=/usr/include` 硬编码为绝对路径，**不引用 `${prefix}`**；
3. 只改 `prefix=` 不生效——meson 链接时 `-L` 指向 `/usr/lib`（无该库）→
   `unable to find library -lxxx`。

## Recommended Solution

**主方案：改写 prefix= 后同时改写硬编码的 libdir/static_libdir/includedir。**

把绝对路径 `/usr/lib`、`/usr/include` 改为指向 conan 包实际路径：

```python
# conanfile _fix_pc_prefix 扩展
data = re.sub(r"(?m)^(libdir|static_libdir|includedir)=/usr/lib$",
              rf"\1={os.path.join(prefix, 'lib')}", data)
data = re.sub(r"(?m)^(includedir)=/usr/include$",
              rf"\1={os.path.join(prefix, 'include')}", data)
```

零补丁、零源码改动。

**回退方案**：若 .pc 改写不可行，配方在链接参数显式加 `-L<conan 包 lib>`——治标
不治本且不通用，不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **systemd/261** | 主验证（本 PR） | ✅ 覆盖前链接报 `unable to find library -lucontext`（libucontext.pc libdir=/usr/lib）；`_fix_pc_prefix` 同时改写 libdir 后链接成功，conan create 通过 |

## 测试覆盖边界

- .pc 改写只影响 **configure/link 阶段的路径解析**，不改库行为；
- 声明通过率时：以 conan create 全流程（libsystemd.so.0.44.0 链接 + test_package
  R34）为实证；systemd 上游测试按 rule 1.2 平台限制声明（需运行中的 systemd 环境）。

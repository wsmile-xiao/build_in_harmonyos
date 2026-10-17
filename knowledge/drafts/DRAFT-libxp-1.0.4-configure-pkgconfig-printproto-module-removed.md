# DRAFT：`PKG_CHECK_MODULES` 依赖的 `.pc` 模块已从生态消失（并入新包）→ 用 `AC_ARG_VAR` 逃生口，而不是去补 `.pc` 文件

> 状态：草稿（待知识库主编 promote）
> 来源：libXp 1.0.4 适配，`archives/l/libxp/1.0.4`（PR #11355，任务 #8449）
> 类别：autotools / configure / pkg-config / conan / portability

## 错误特征

`configure` 阶段直接停机：

```
checking for XPRINT... no
configure: error: Package requirements (x11 >= 1.6 xext xextproto xau printproto) were not met:

Package 'printproto', required by 'virtual:world', not found

Consider adjusting the PKG_CONFIG_PATH environment variable if you
installed software in a non-standard prefix.
```

或者同族但在环境里**根本没有 pkg-config 可执行文件**时的形态（libXp 在 CI worker 上的实际形态）：

```
./configure: line 19277: pkg-config: command not found
configure: error: The pkg-config script could not be found. Make sure it is
in your PATH, or set the PKG_CONFIG environment variable to the full path...
```

**最强识别信号：把缺失模块的 `.pc` 补进 `PKG_CONFIG_PATH` 也没有用。**
两个查询同时为空才能确诊：

```bash
# (a) 整个制品仓没有任何包提供它
conan search 'printproto*' -r=<remote>        # → 空
# (b) 目标包自己的产物里也没有这个 .pc
find ~/.conan2/p/<xorgproto-pkg>/p -name 'printproto.pc'   # → 空
ls ~/.conan2/p/<xorgproto-pkg>/p/share/pkgconfig/           # 29 个模块 .pc，无 printproto
ls ~/.conan2/p/<xorgproto-pkg>/p/lib/pkgconfig/             # 目录根本不存在
```

这与「包没装」「路径没配」是**两回事**：模块已经从生态里消失，任何路径配置都救不了。

## 触发条件

三条同时成立：

1. 上游 `configure.ac` 用 `PKG_CHECK_MODULES` 列了一个**已经被并入其它包**的
   `*-proto` / `*-macros` 模块（X.Org 7.7 把 `printproto`、`xextproto`、
   `xf86rushproto` 等全部并入 `xorgproto`，此后**没有任何包再提供这些独立的
   `.pc`**）；
2. 制品仓与目标依赖包的产物里都查不到该模块的 `.pc`（见上面的双空判据）；
3. 生成的 `configure` 里存在 `PKG_CHECK_MODULES` 生成的
   `AC_ARG_VAR` 逃生口。

第 3 条怎么查：

```bash
grep -n 'if test -n "$XPRINT_CFLAGS"' configure   # → 19277
grep -n 'if test -n "$XPRINT_LIBS"'  configure   # → 19294
```

## 根因分析

### (1) `PKG_CHECK_MODULES` 的硬失败语义

`PKG_CHECK_MODULES(PREFIX, MODULES)` 会展开成：先看 `$PREFIX_CFLAGS` / `$PREFIX_LIBS`
是否非空；**都为空**才真正调用 `pkg-config` 求解。求解失败时（模块不存在，
或 pkg-config 二进制不存在）置 `pkg_failed=yes`，默认的 `ACTION-IF-NOT-FOUND`
直接 `AC_MSG_ERROR` 停机。

所以这里有两个独立的失败入口，症状不同但根因同一个：

| 环境 | 现象 |
| --- | --- |
| 装了 pkg-config，但没有 `printproto.pc` | `Package 'printproto' ... not found` |
| 连 pkg-config 都没有（精简 CI worker） | `The pkg-config script could not be found` |

### (2) `printproto` 是一个「历史化石」依赖

libXp 1.0.4 发布于 2010 年，`configure.ac` 写的是当时正确的模块列表：这个库确实
要用 X Print 协议头（`X11/extensions/Print.h`、`Printstr.h`）。但 X.Org 7.7 之后，
这些头文件**搬进了 `xorgproto`**，`printproto` 作为一个独立发行物被正式撤销。于是：

- 今天的 `xorgproto/2025.1` 提供 `Print.h` / `Printstr.h`（**头文件需求是满足的**）；
- 但它**不带** `lib/pkgconfig/`，只带 `include/` 与 `share/pkgconfig/`；
- 而 `share/pkgconfig/` 下 29 个模块 `.pc`（applewmproto、bigreqsproto、
  compositeproto、damageproto、dmxproto、dpmsproto、dri2proto、dri3proto、
  fixesproto、fontsproto、glproto、inputproto、kbproto、presentproto、
  randrproto、recordproto、renderproto、resourceproto、scrnsaverproto、
  videoproto、xcmiscproto、xextproto、xf86bigfontproto、xf86dgaproto、
  xf86driproto、xf86vidmodeproto、xineramaproto、xproto、xwaylandproto）
  **没有 printproto**。

结论：**依赖在语义上是满足的，在 pkg-config 元数据上是不可满足的。** 这正是它容易
被误判成「缺依赖、去装个包」的原因。

### (3) 同一个坑会从构建期漏到消费期

libXp 自己安装出来的 `xp.pc` 里，上游 `xp.pc.in` 写死：

```
Requires:         printproto
Requires.private: x11 xext xau
```

`Requires.private` 那行是对的，**公开的** `Requires` 那行是坏的。于是配方构建成功、
库也装好了，但**任何消费者**执行 `pkg-config --cflags xp` 都会立刻失败 ——
构建期的问题变成了生态期的问题。这是本条必须一并处理的原因。

## 解决方案

用 `PKG_CHECK_MODULES` 自带的 `AC_ARG_VAR` 逃生口：把 `$PREFIX_CFLAGS` /
`$PREFIX_LIBS` 设成非空，`configure` 就**完全跳过 pkg-config**，既不查模块
也不要求 pkg-config 二进制存在。

在 Conan 配方里（`XPRINT_*` 换成实际的 `PREFIX`）：

```python
# generate()
g = AutotoolsToolchain(self)
env = VirtualBuildEnv(self).environment()          # 或等价的环境对象
if is_ohos:
    # 逃生口：两个变量都非空 → configure 走 AC_ARG_VAR 分支，不调用 pkg-config
    env.define("XPRINT_CFLAGS", self._xprint_cflags())   # "-I<dep>/include ..."
    env.define("XPRINT_LIBS",   self._xprint_libs())     # "-L<dep>/lib -lX11 -lXext -lXau"
g.generate(env=env)
```

两个变量的值直接从**已发布的依赖包目录**算出（本适配从
`libx11/6.4.0`、`libxext/6.4.0.1`、`libxau/1.0.11`、`xorgproto/2025.1`
四个 Conan 包的 `package_folder` 拼 `-I` / `-L` / `-l`），不经过 pkg-config。

配套**必须**同时修消费期的 `xp.pc`（否则坑只是被推迟）：

```python
# package()
# 上游 xp.pc.in 的 Requires: printproto 会毒化消费者，改写为真实存在的模块
replace_in_file(self, pc, "Requires: printproto", "Requires: x11 xext")
# 再把 prefix/libdir/includedir 改成 ${pcfiledir} 相对形式，使包可重定位
```

要点：

- **不改上游任何源文件**，`patches/` 为空 —— 逃生口是 `configure.ac` 里
  `PKG_CHECK_MODULES` **本来就生成**的，配方只是把变量喂给它；
- 因此本修复对「tarball 自带预生成 `configure`、不跑 autoreconf」的场景同样成立
  （libXp 1.0.4 就是这种，2010 年 tarball 里 `configure` 已生成好）；
- 顺带绕开了「CI worker 上没有 pkg-config 可执行文件」这个环境前提 ——
  这是它比「补一个 `.pc` 文件」更可靠的地方。

## 验证命令

```bash
# 1) 复现构建期失败
conan create archives/l/libxp/1.0.4 -pr:h=<profile> -pr:b=<profile> --build=missing
#    → configure: error: Package 'printproto' ... not found
#      或 configure: error: The pkg-config script could not be found

# 2) 确诊「模块已从生态消失」而不是「路径没配」（双空判据）
ls <xorgproto>/share/pkgconfig/ | grep -i print   # → 无输出
ls <xorgproto>/lib/pkgconfig/ 2>&1                # → No such file or directory
conan search 'printproto*' -r=<remote>            # → 空

# 3) 确认逃生口存在（用 tarball 自带的 configure，不要 autoreconf）
grep -n 'AC_ARG_VAR\|if test -n "\$XPRINT_CFLAGS"' configure

# 4) 设有逃生口变量后重试
#    → checking for XPRINT... yes（不出现 pkg-config 调用）
conan create archives/l/libxp/1.0.4 ... --build=missing
#    → test_package: libxp consumer checks: 13/13 passed

# 5) 确认消费期不被毒化
pkg-config --cflags xp        # 改写前必失败；改写后成功
grep -n '^Requires' <pkg>/lib/pkgconfig/xp.pc
```

## 禁止策略

| 禁止 | 原因 | 后果 |
| --- | --- | --- |
| 自造一个空壳 `printproto.pc` 塞进 `PKG_CONFIG_PATH` | 伪造一个生态里不存在的事实，掩盖真实的模块缺失；模块一旦真被需要，空壳会给出空的 `-I`/`-l`，把「找不到」变成「编不过/链不过」 | 症状后移、更难定位；知识库被污染 |
| 在 `configure.ac` 里删掉 `printproto` 后重跑 `autoreconf` | 改了上游源码；且 tarball 自带 `configure` 的场景会引入 autotools 版本漂移（生成的 `configure` 与上游发布版不一致，diff 不可读） | 补丁面扩大，评审不可信 |
| 把 `pkg_failed=no` / `echo 'printproto support disabled'` 之类硬写进 `configure` | 伪造通过；被改写的 `configure` 是构建产物，消费者无从得知 | 测试/构建假通过 |
| 只在 `generate()` 里设环境变量、忘了改安装出的 `xp.pc` | 构建期修好了，消费期仍然带 `Requires: printproto` | 坑被推迟到消费者，生态期才爆 |

## 关联

- `similar_to` **E468**（PkgConfigDeps 写出 `.pc` 但未把 generators 目录加进
  `PKG_CONFIG_PATH`）：E468 是「路径没配」，本条目是它的**下一层** ——
  模块本身已经不存在，扩展 `PKG_CONFIG_PATH` 完全无效。两者的第一个排查动作
  都是看 `configure` 报的是哪个模块，但只有本条目需要改用 `AC_ARG_VAR` 逃生口。
- `similar_to` **`DRAFT-ohos-la-libdir-hardcode`**：同批 libXp 适配里的另一类
  「依赖制品的构建期路径泄漏到消费期」问题（`libXau.la` 的 `libdir=` 指向构建机
  临时目录）。两条的共性是：**问题不在上游源码里，而在构建期/消费期的外部前提**。
- 本条目自带一个消费期孪生问题（`xp.pc` 的 `Requires: printproto`），已并入同一
  修复，不单列。

## 上游可提交性

这是上游 `configure.ac` 的真实缺陷，且**可以直接向上游提 issue/PR**：
`printproto` 自 X.Org 7.7 起已被 `xorgproto` 取代，`PKG_CHECK_MODULES` 的列表应改为
`x11 >= 1.6 xext xau xorgproto`（或直接删掉 `printproto`，因为 `Print.h` 由
`xorgproto` 提供）；`xp.pc.in` 里的 `Requires: printproto` 同理应改为
`Requires: x11 xext`。上游 `master` 至今保留着这两处 —— libXp 自 2010 年
1.0.4 起未有新版本发布。

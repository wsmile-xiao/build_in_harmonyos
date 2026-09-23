# DRAFT：制品仓依赖包自带的 `.pc` 记录了**构建机前缀** —— 挂进 `PKG_CONFIG_PATH` 会让 pkg-config 静默成功并返回错误路径

> 状态：草稿（待知识库主编 promote）
> 来源：pdf2svg 0.2.4 适配，`archives/p/pdf2svg/0.2.4`（任务 #5914，PR #11397）
> 类别：autotools / configure / pkg-config / conan / dependency / portability

## 症状（这一条的特点是：**没有**症状）

把依赖包自带的 `lib/pkgconfig` 挂进 `PKG_CONFIG_PATH` 之后，**一切看起来是正常的**：

```
checking for CAIRO... yes
checking for POPPLERGLIB... yes
```

`pkg-config` 退出码 **0**，`configure` 顺利往下走。错误要到编译期或链接期才出现：

```
fatal error: 'cairo.h' file not found
cannot find -lcairo
fatal error: 'glib.h' file not found
```

或者（精简 worker 上更隐蔽的形态）：

```
Package 'xmuu', required by 'virtual:world', not found
```

**危险点在于：错误信息里出现的路径是 `/include/cairo`、`/lib` 这种"看起来像系统目录"的
东西，非常容易被误判为"缺系统开发包"，而不是"制品仓里的 `.pc` 是坏的"。**

## 根因

ohpcd 制品仓里的依赖包大多由**上游自己的构建系统**安装，`lib/pkgconfig/*.pc`
是构建机当场生成的，`prefix=` 记录的是**构建机当时的绝对路径**，随包一起被发布出来。

pdf2svg 0.2.4 适配时逐个抓取，三例污染：

| `.pc` | 实测 `prefix=` | 会给出的结果 |
| --- | --- | --- |
| `cairo/lib/pkgconfig/cairo.pc` | `/` | `-I/include/cairo -L/lib -lcairo` |
| `cairo/lib/pkgconfig/cairo-svg.pc` | `/` | 同上 |
| `poppler/lib/pkgconfig/poppler.pc` | `/storage/Users/currentUser/.conan2/p/b/poppl74bba25eec764/p` | 指向**另一台构建机**的 conan hash 目录 |
| `poppler/lib/pkgconfig/poppler-glib.pc` | `/storage/Users/currentUser/.conan2/p/b/poppl74bba25eec764/p` | 同上 |
| `poppler/lib/pkgconfig/poppler-cpp.pc` | 同上 | 同上 |
| `glib/lib/pkgconfig/glib-2.0.pc` | `/` | `-L/lib -lglib-2.0 -lintl` |

poppler 那两条尤其说明问题：`poppl74bba25eec764` 是**另一台构建机**的 hash 目录，
当前制品仓里实际的 `package_folder` 是 `poppl2e264df4b3b30` —— 也就是说这个
`prefix` **在本机根本不存在**。它不是"变量没展开"，而是"指向了别人家的缓存"。

第二层陷阱：`glib-2.0.pc` 的 `Libs` 里带 `-lintl`。制品仓的 glib 确实随包带了
`libintl.so.8`，但 `-lintl` 能不能被解析取决于 libdir 是否在 `-L` 列表里 ——
`.pc` 自己给的 `-L` 是错的，所以这一项同样是"看着合理、用着找不到"。

## 与"模块找不到"类问题的区别

同批的姊妹条目（libxp 的 `printproto`、xauth 的 `xmuu`）症状是
`Package 'X' not found` —— 直接、好诊断。本条目**正好相反**：pkg-config 成功。
因此把三条并列看，**诊断入口相同（看 configure 报什么），但确诊查询完全不同**：

| 情形 | 确切诊断查询 | 正确处置 |
| --- | --- | --- |
| 模块被撤销（printproto） | `conan list "printproto/*" -r ohpcd` → Found 0 | 纯 `AC_ARG_VAR` 逃生口（头文件需求已由 xorgproto 满足） |
| 模块有真实提供者、制品仓没包（xmuu） | `conan list "libxmu/*"` → Found 0 **且**上游有官方 tarball | `AC_ARG_VAR` 逃生口 **+** vendored 编译最小闭包 |
| **依赖包自带 `.pc` 记着构建机前缀**（本条） | `grep -H '^prefix=' <dep>/lib/pkgconfig/*.pc` | **禁止**挂依赖包自带 pkgconfig；走 `AC_ARG_VAR` 逃生口（或改用 conan 生成的 `.pc`） |

## 验证命令

```bash
# 1) 逐个抓依赖包自带 .pc 的 prefix —— 一条命令区分"污染"与"自洽"
grep -H '^prefix=' <dep_pkg>/lib/pkgconfig/*.pc
#   实测：cairo.pc                prefix=/
#         cairo-svg.pc            prefix=/
#         poppler-glib.pc         prefix=/storage/Users/currentUser/.conan2/p/b/poppl74bba25eec764/p
#         glib-2.0.pc             prefix=/

# 2) 复现"静默成功"（关键：看 rc，它是 0）
PKG_CONFIG_PATH=<cairo_pkg>/lib/pkgconfig pkg-config --cflags --libs cairo; echo "rc=$?"
#   → -I/include/cairo -L/lib -lcairo , rc=0

# 3) 证明这些路径不是"没展开"而是"指向别人家的缓存"
ls -d /storage/Users/currentUser/.conan2/p/b/poppl74bba25eec764/p 2>&1   # → No such file

# 4) 确认逃生口存在（用 tarball 自带的 configure，不要 autoreconf）
grep -n 'if test -n "\$CAIRO_CFLAGS"'       configure    # pdf2svg 实测第 3674 / 3691 行
grep -n 'if test -n "\$POPPLERGLIB_CFLAGS"' configure    # pdf2svg 实测第 3766 / 3783 行
#   非空即直接采用，完全不执行 pkg-config

# 5) 用 cpp_info 现算的 -I/-L 复核（应与 .pc 给出的完全不同）
#    glib 的 include/glib-2.0、lib/glib-2.0/include（glibconfig.h）、include/gio-unix-2.0
#    只存在于 cpp_info 的**组件**里；根 cpp_info.includedirs 只有一层 include，
#    用它会得到 fatal error: 'glib.h' file not found
```

## 方案（Conan 配方侧）

```python
# generate()：走 PKG_CHECK_MODULES 的 AC_ARG_VAR 逃生口，四个变量都非空即
# 完全不调用 pkg-config；-I/-L/-l 由 cpp_info 现算。
environment = tc.environment()
environment.define("CAIRO_CFLAGS",       self._cflags(("cairo", "pixman", "fontconfig", "freetype", "libpng")))
environment.define("CAIRO_LIBS",         self._libs(("cairo",), ("cairo",)))
environment.define("POPPLERGLIB_CFLAGS", self._cflags(("poppler", "glib") + _CAIRO_CLOSURE))
environment.define("POPPLERGLIB_LIBS",   self._libs(("poppler", "glib", "cairo"),
                                                     ("poppler-glib", "poppler", "glib-2.0",
                                                      "gobject-2.0", "gio-2.0"),
                                                     ("m", "pthread", "dl")))
tc.generate(env=environment)
```

三条要点：

1. **`-I` 必须用 `aggregated_components()`，不能用根 `cpp_info`。**
   glib 的 `include/glib-2.0`、`lib/glib-2.0/include`（`glibconfig.h`）与
   `include/gio-unix-2.0` 只在**组件**里，根 `cpp_info.includedirs` 只有一层
   `include` —— 用它拼 CFLAGS 会让 `#include <glib.h>` 失败。
2. **`-l` 按消费者实际 include 的头文件写，不要照抄依赖的根级 `cpp_info.libs`。**
   poppler 那条是 `['poppler','poppler-glib','poppler-cpp']` 的**并集**，照抄会白白
   把 `poppler-cpp` 拖进链接行；`pdf2svg.c` 只 include `<poppler.h>` /
   `<poppler-document.h>` / `<poppler-page.h>`（即 `poppler-glib`），因此只写
   `-lpoppler-glib`。
3. **系统库只挂一处。** `-lm -lpthread -ldl` 只加在 `POPPLERGLIB_LIBS` 末尾，
   避免在两个变量里各出现一份。

### 兜底路线

如果消费者**必须**经 pkg-config（上游用了 `PKG_CHECK_MODULES` 之外的 pkg-config 宏、
或构建系统无法通过环境变量注入），则把 `PKG_CONFIG_PATH` 指向
**conan 生成的** `.pc`（`PkgConfigDeps` 生成器写出的 `prefix` 指向真实的
`package_folder`），而不是依赖包自带的 `lib/pkgconfig`。代价是引入一个生成器，
且模块名必须与上游 `PKG_CHECK_MODULES` 里的名字对得上。

两条路可以混用：某个依赖的 `.pc` 若是 conan 生成的（自洽），就保留它的路径。

## 禁止策略

| 禁止 | 原因 | 后果 |
| --- | --- | --- |
| `PKG_CONFIG_PATH=<dep>/lib/pkgconfig` | 里面是构建机前缀；pkg-config 静默成功并给出 `/include`、`/lib` 或别人家 `.conan2` 缓存路径 | 故障点后移到 compile/link，错误信息看似"缺系统包"，一轮 CI 白跑且方向错误 |
| 看到 pkg-config 退出码 0 就认定"模块可用" | 本类污染下 rc 就是 0；只有**核对 `prefix=`** 才能区分自洽与污染 | 把"静默成功"当成"可用"，问题推迟到链接期 |
| `sed`/`cp`/`echo >` 去改缓存里的 `.pc` | 不可复现、不可追踪；换 worker / 重装依赖即失效 | 修法只存在于当前机器，CI 随机通过 |
| 伪造一个 `cairo.pc`/`glib-2.0.pc` 塞进 `PKG_CONFIG_PATH` | 伪造制品仓里不存在的产物，把"模块不可用"变成"链接期 undefined reference" | 症状后移且更难定位；知识库被污染（同 libXp / xauth 条目的禁止策略） |

## 关联

- **`DRAFT-libxp-1.0.4-configure-pkgconfig-printproto-module-removed`**：
  同批 X11 家族。区别在**模块是否还有真实提供者**——`printproto` 自 X.Org 7.7 起
  被 `xorgproto` 取代、独立发行物正式撤销，正确答案是纯 `AC_ARG_VAR` 逃生口。
- **`DRAFT-xauth-1.1.4-missing-pkgconfig-module-vendor-upstream-sublib`**：
  同批 X11 家族。`xmuu` 提供者健在只是制品仓没包，逃生口**必须再叠加** vendored 编译
  （逃生口负责"不调用 pkg-config"，vendored 编译负责"`-l` 真有东西可链"）。
- 三条共用同一个诊断入口（configure 报哪个模块），**确诊查询不同**：
  本条查"依赖包自带的 `.pc` 是否记着构建机前缀"，libxp 查"模块是否被撤销"，
  xauth 查"提供者还在不在制品仓"。

## 上游可提交性

**不可向上游提交**：pdf2svg 的 `configure.ac` 用 `PKG_CHECK_MODULES` 是标准做法；
问题出在**制品仓把依赖包构建时的 `.pc` 原样发布了出来**，不在上游源码。

因此本条目的正解分两层：

1. **本配方内**（已实施）：走 `AC_ARG_VAR` 逃生口 + `cpp_info` 现算 `-I/-L/-l`，
   完全绕开 pkg-config；
2. **生态层**（应记录，不在本 PR 内实施）：依赖包发布时用 conan 的 `PkgConfigDeps`
   重新生成 `.pc`（或至少在 `package()` 里把 `prefix=` 改写成安装前缀），
   消费者就不必各自绕行。这条属于制品仓治理，超出单个消费者 PR 的范围。

## 上游测试

pdf2svg 0.2.4 上游**无测试套件**（tarball 无 `tests/` 目录，`Makefile.am` 只有
`bin_PROGRAMS = pdf2svg`，默认分支 `master` 全树 17 个条目中同样没有任何测试文件）。
被测行为由 `test_package/test_pdf2svg.sh` 对**已安装的** `bin/pdf2svg` 做 6 项
端到端断言（用法输出 / 单页转换 / `all` 多页转换 / 输入打不开 / 页标签不存在 /
两页产物不同），全部通过。

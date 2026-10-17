# `AC_CHECK_LIB` 的库名是**写死的 soname**——guile 从 `-lguile` 变成 `-lguile-2.2` 后，依赖装对了 configure 照样报「can't find guile」

> DRAFT-7348-ballandpaddle-0.8.1-ac-check-lib-probes-a-fixed-soname
> （知识库扩展草案，路径 B）与 ballandpaddle 0.8.1 归档同 PR 交付。

ballandpaddle 0.8.1 的上游 `configure.ac:29`：

```m4
AC_CHECK_LIB(guile, scm_boot_guile,
             LIBS="-lguile $LIBS",
             AC_MSG_ERROR(can't find guile. This software REQUIRES guile.))
```

在 Guile 2.2.7 的环境里，这行**必然**失败：

```
checking for scm_boot_guile in -lguile... no
configure: error: can't find guile. This software REQUIRES guile.
```

而 `conanbuild.sh` 里的 `-L<guile>/lib`、`-I<guile>/include/guile/2.2`、
`-lguile-2.2` **全都在**。

> 这一条与 `DRAFT-7348-ballandpaddle-0.8.1-sdl12-compat-has-no-sdl-config`
> 是同一个母题：**依赖已正确注入，探针在找不存在的东西。**
> 那条探针找的是「可执行脚本」，这条找的是「写死的 soname 文件名」。

---

## 一、为什么 `AC_CHECK_LIB` 会这样

`AC_CHECK_LIB(LIB, FUNC)` 里 `LIB` 是**字面量**，它生成的是

```
checking for <FUNC> in -l<LIB>...
```

外加一条真实的试链接。也就是说，它探测的**不是「guile 这个包在不在」，
而是「`-lguile` 这个文件名能不能解析」**。

带 soname 版本号的库在主版本跃迁后，`lib<name>.so` 这个**文件名本身**
就消失了：

| 库 | 老 soname | 新 soname |
|---|---|---|
| guile | `libguile.so`（1.8） | `libguile-2.2.so`（2.x，随 minor 走） |
| lua | `liblua.so` | `liblua5.4.so` |
| boost | `libboost_thread-mt.so` | `libboost_thread.so`（命名规则还反着变过） |
| icu | `libicuuc.so` | `libicuuc.so.72`（版本进 soname 段） |

所以「soname 变了」这件事对 `AC_CHECK_LIB` 是**破坏性**的：不是找到旧版本，
而是**根本找不到文件**。

---

## 二、判断该改哪一边：先读源码用的是哪代 API

这是最容易改错方向的地方。看到 `can't find guile` 就想「上游要 Guile 1.8，
那就降级依赖」——**对 ballandpaddle 是彻底错的**：

```bash
$ grep -rn 'scm_to_locale_string\|scm_from_int\|scm_c_eval_string' src/ | head
src/extension.cpp:   ... scm_to_locale_string(...) ...
src/ball.cpp:        ... scm_from_int(...) ...
```

`scm_to_locale_string` / `scm_from_int` / `scm_c_eval_string` 全是
**Guile 2.x API**（Guile 1.8 里对应的叫 `SCM_STRING_CHARS` / `scm_long2num`）。
也就是说**上游早就迁到 2.x 了，只是 `AC_CHECK_LIB` 那一行的库名忘了跟着改。**

判据：

```bash
# 命中 → 源码已是新一代 API，只需对齐探针库名
grep -rn 'scm_to_locale_string\|scm_from_int\|scm_c_eval_string' src/
# 命中 → 源码真用老 API，此时才需要老版本依赖
grep -rn 'SCM_STRING_CHARS\|scm_long2num\|scm_makfrom0str' src/
```

> **「上游源码用新 API + 探针留旧库名」⇒ 这是「探针与事实不符」，不是
> 「上游要求老版本」。** 补丁只对齐探针，不改任何行为，甚至可以直提上游。

---

## 三、库名怎么取：看制品，不要看包名

```bash
$ ls <guile-prefix>/lib/libguile*.so*
libguile-2.2.so   libguile-2.2.so.1   libguile-2.2.so.1.3.0
```

**以真实文件名为准。** 凭包名或 `.pc` 名猜必错：

| 包 | 错的猜法 | 对的名字 |
|---|---|---|
| guile 2.x | `-lguile` | `-lguile-2.2` |
| boost | `-lboost-system` | `-lboost_system`（下划线！） |
| lua | `-llua` | `-llua5.4` |
| icu | `-licu-uc` | `-licuuc` |

写错名字的补丁**看起来是生效的**（`grep` 能搜到改动），但 configure 会给出
**一模一样的** `can't find` —— 于是排查时间浪费在「补丁为什么没用」而不是
「名字还是错的」。

---

## 四、改的时候两个必须同时改的文件（和随之而来的 mtime 坑）

上游 tarball **自带已生成的 `configure`**，而沙箱里**没有 autoconf**。
所以：

- **只改 `configure.ac`** → `configure` 不会重新生成，改动**完全无效**
  （症状：补丁打了、configure 还是老行为）
- **只改 `configure`** → 上游升级或有人重跑 `autoconf` 后修复丢失，
  补丁不可上游化
- **两个都改** ✅ —— 但立刻引入下一个坑：

GNU patch 会把被打补丁文件的 mtime 设成 diff 头里的时间戳。`configure.ac`
的 hunk 排在 `configure` **之后** → **`configure.ac` 比 `configure` 新**。
根 `Makefile.in` 里有

```make
$(top_srcdir)/configure: $(am__aclocal_m4_deps)     # am__aclocal_m4_deps = configure.ac
Makefile: $(srcdir)/Makefile.in
```

这类重生成规则，mtime 一倒挂，make 就会试图重跑 `autoconf`/`automake`
——沙箱里没有 `aclocal-1.11`/`autoconf`，直接失败。

修法是显式归一化时间戳（同仓库先例 `archives/l/libmodbus/3.2.0`）：

```python
self.run("touch -d '2000-01-01 00:00:00' configure.ac aclocal.m4 Makefile.am src/Makefile.am",
         cwd=self.source_folder)
self.run("touch configure Makefile.in src/Makefile.in", cwd=self.source_folder)
```

> 这个坑的通用形态值得单记：**「同时改生成物与其输入，就会制造 mtime 倒挂，
> 触发构建系统的重生成规则」**，与具体是哪个库无关。

---

## 五、验证闭环

```bash
# 1) 探针写死的名字 vs 制品真名
grep -nE 'AC_CHECK_LIB\(' configure.ac
ls <dep>/lib/libguile*.so*

# 2) 注入的是真名（证伪「依赖没装」）
grep -on -- '-l[A-Za-z0-9_.+-]*' <build_folder>/conanbuild*.sh | sort -u | grep guile
#    → -lguile-2.2（没有 -lguile）

# 3) 源码 API 代际（决定改探针还是改依赖）
grep -rn 'scm_to_locale_string\|scm_from_int' src/ | head

# 4) 修复后探针真的过
grep -n 'checking for scm_boot_guile in -lguile-2.2' config.log     # → yes

# 5) 终局核对：产物链的是哪个 soname
readelf -d <installed-bin> | grep -i guile      # → NEEDED libguile-2.2.so.1
```

第 5 步是最有价值的收尾：它把「探针通过了」升级成「产物真的链上了那个 soname」。
在 ballandpaddle 这个包里，这条 `NEEDED` 还直接决定了 `test_package` 里
`--version` / `--help` 能不能跑起来 —— 因为那两条输出的打印发生在
**内嵌 Guile 解释器 boot 完成之后**，加载器少解析一个 `NEEDED`，
进程在 `main()` 之前就被拒绝，拿到的是另一种 stderr。

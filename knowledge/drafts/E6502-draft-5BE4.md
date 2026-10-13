# E6502 — Conan 下 autotools 的 autoreconf 必须走 conanbuild env（ACLOCAL_PATH/LIBTOOLIZE/_lt_pkgdatadir），手工拼 PATH 会跳过 libtoolize

## 错误特征

autotools 工程在 Conan 环境中执行 `autoreconf -v -i -f` 时，出现以下任一症状（通常在
`aclocal`/`autoconf` 阶段）：

```
configure.ac: not using Libtool            # autoreconf 判未使用 libtool，直接跳过 libtoolize
...
configure.ac:31: error: possibly undefined macro: AC_PROG_LIBTOOL
      If this token and others are legitimate, please use m4_pattern_allow.
      See the Autoconf documentation.
```

或（当 `ACLOCAL_PATH` 已正确但 `_lt_pkgdatadir` 缺失时）：

```
.autoreconf-real: running: libtoolize --copy --force
libtoolize:   error: $pkgauxdir is not a directory: '//share/libtool/build-aux'
.autoreconf-real: error: libtoolize failed with exit status: 1
```

也可伴随 `aclocal --force -I m4` 报 `warning: couldn't open directory 'm4': No such file or directory`。

## 触发条件

- 构建系统: autotools（需要 `autoreconf` 从 `configure.ac`/`Makefile.am` 生成的工程）
- 阶段: configuration（`autoreconf` → `aclocal`/`autoconf`，尚未到 `configure`）
- 工具链: 使用 Conan `tool_requires` 提供 autoconf/automake/libtool，且**没有**继承 conan 生成的
  `conanbuild` 环境（例如手工把各工具包的 `bin/` 拼进 `PATH` 后直接调用 `autoreconf`）

## 根因分析

Conan 的 `automake`/`libtool` 包通过 `buildenv_info` 注入三个 `autoreconf`/`libtoolize` 依赖的
环境变量：

- `ACLOCAL_PATH` → `libtool/share/aclocal`（提供 `libtool.m4`，定义宏 `AC_PROG_LIBTOOL`/`LT_INIT`）
- `LIBTOOLIZE`   → `libtool/bin/libtoolize`
- `_lt_pkgdatadir` → 包内一份「源码树形状」的目录（`build-aux`/`libltdl`/`m4` 软链），
  用于绕开 libtoolize 中烤死的空 `@datadir@`（安装前缀为空时变成 `//share/libtool/build-aux`）

`autoreconf` 先做一次 `autom4te --trace` 探测工程是否使用各工具；**是否调用 `libtoolize`
取决于 trace 是否见到 `AC_PROG_LIBTOOL`/`AM_PROG_LIBTOOL`/`LT_INIT`**。若 `ACLOCAL_PATH` 未设置，
`aclocal` 找不到 `libtool.m4`，trace 就看不到 `AC_PROG_LIBTOOL`，`autoreconf` 打印
“configure.ac: not using Libtool” 并**跳过 libtoolize**（于是 `m4/` 永不生成，`AC_CONFIG_MACRO_DIR([m4])`
下的 `aclocal` 也缺宏），随后 `autoconf` 报 `possibly undefined macro: AC_PROG_LIBTOOL`。

即便 `ACLOCAL_PATH` 正确，若缺 `_lt_pkgdatadir`，`libtoolize` 会去读烤死的 `//share/libtool/build-aux`
（安装前缀为空导致）而失败。

## 解决方案

### 推荐方案

让 Conan 构造并注入环境，不要手工拼装：

- 在 `conanfile.py` 中通过 build helper 运行，`env="conanbuild"`：
  ```python
  from conan.tools.gnu import Autotools
  # tool_requires: autoconf/2.72, automake/1.18, libtool/2.5.4
  self.run("autoreconf -v -i -f", cwd=self.source_folder, env="conanbuild")
  ```
- 或在命令行先 `source` Conan 生成的 `conanbuild.sh`（`conan install ... -g VirtualBuildEnv` 产出）
  再执行 `autoreconf -v -i -f`。此时 `ACLOCAL_PATH`/`LIBTOOLIZE`/`_lt_pkgdatadir` 均已就位。

> 注意：`automake`/`libtool` 的 `conanbuild` env 同样会带入 `PERL5LIB`（指向 conan perl）。
> 若同时存在平台 perl 与 conan perl 的版本/模块错配，需按 DRAFT-6049 另行收敛 `PERL`/`PERL5LIB`。

### 禁止做法

- ❌ 只把各工具包的 `bin/` 目录手工拼进 `PATH` 后直接跑 `autoreconf`（缺 `ACLOCAL_PATH`/`_lt_pkgdatadir`，
  必然触发本模式）。
- ❌ 用 `autoconf -I` / `m4_pattern_allow` 之类手段“压掉” `possibly undefined macro: AC_PROG_LIBTOOL`
  报错来强行继续——`libtoolize` 未运行，`configure` 会在后续环节以更隐晦的方式失败。
- ❌ 手工伪造 `//share/libtool/build-aux` 目录绕过 `$pkgauxdir is not a directory`——应改用
  `_lt_pkgdatadir` 指向 conan libtool 包内的源码树形状目录。

## 验证

```bash
# 1) 确认环境变量已注入（在 conanbuild env 中）
env | grep -E "ACLOCAL_PATH|LIBTOOLIZE|_lt_pkgdatadir"

# 2) 确认 autoreconf 会调用 libtoolize、不再出现 "not using Libtool"
autoreconf -v -i -f 2>&1 | grep -i -E "libtoolize|not using Libtool|possibly undefined macro"
#   预期：出现 "running: libtoolize --copy --force" 且无 "not using Libtool" / 无 undefined macro

# 3) 确认 m4/ 宏目录已生成
ls m4/ | grep -E "libtool|ltoptions|ltsugar"
```

## 关联条目

- 相关: E007（config.guess 三元组）、E114（configure umask/HMDFS）、E116（automake/perl @INC）、
  E209（autogen.sh/libtoolize 手动绕行）、E007 家族 DRAFT-6049（autotools perl dual-arch）

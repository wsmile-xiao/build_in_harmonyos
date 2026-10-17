# DRAFT-10035: OHOS 上 autotools 自举三要点（tool_requires(automake/1.18) + 分步自举 + $ACLOCAL 惯用法）

- 条目主题：上游 tarball 只带 `configure.ac`/`Makefile.am`（无 `configure`/`Makefile.in`）的包在 HarmonyOS PC 上用 Conan 配方自举 autotools 的三个必做点。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：wmcdplay 1.1；同范式适用于所有"只发 autotools 源"的上游。

## 错误特征
- `aclocal: Permission denied` / `aclocal: not found` / `Error 126`
- `autoreconf: autoconf.m4f ...` 或自举后 `configure.ac: undefined macro AM_INIT_AUTOMAKE`
- `configure: error: cannot find install-sh`

## 根因
1. OHOS 镜像 `/data/service/hnp` 只有 autoconf 家族，**没有 automake/aclocal/libtool**。
2. `autoreconf` 的 m4 缓存链（`autoconf.m4f`）在 OHOS 会解析到与 PATH 不同的 autoconf，核心 `AM_*`/`AC_*` 宏报未定义。
3. automake 包的 `bin/aclocal`、`bin/automake` 是 `#!/bin/sh` 包装脚本，从 `$(dirname "$0")` 推算 `--automake-acdir`/`--system-acdir`/`--libdir`；包经 `buildenv_info` 导出的 `ACLOCAL`/`AUTOMAKE`/`ACLOCAL_PATH`/`PERL5LIB` **只在 conanbuild 环境生效**。

## 修复
```python
def build_requirements(self):
    self.tool_requires("automake/1.18")          # OHOS 镜像无系统 automake

def generate(self):
    VirtualBuildEnv(self).generate()             # 落地 conanbuild 环境（ACLOCAL/AUTOMAKE）

def build(self):
    self._run_build('"${ACLOCAL:-aclocal}" --force')
    self._run_build("autoconf -o configure configure.ac")
    self._run_build('"${AUTOMAKE:-automake}" --add-missing --copy')
```
不用 `autoreconf`；`autoheader` 在 `configure.ac` 无 `AC_CONFIG_HEADERS` 时也不需要。

## 附：in-source 构建约束
`XPM/%.art: cd XPM && ./makeart $*` 一类模式规则用相对路径，out-of-source 构建无法
工作；配方须保持 in-source（`basic_layout` + `cwd=self.source_folder`）。

## 验证
wmcdplay 1.1：自举产物 `configure` 169196 B、`Makefile.in` 31899 B，随后 configure/make/check 全链 rc=0。

## 关联
E041（automake 版本不匹配/重生成）、E490（辅助脚本可执行位）、E114（configure TMPDIR）。

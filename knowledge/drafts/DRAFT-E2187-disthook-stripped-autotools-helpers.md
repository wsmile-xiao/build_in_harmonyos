# DRAFT-E2187：上游 `dist-hook` 删掉 autotools 辅助文件，目标环境又无工具链重建

> Contributor: Awstme | Status: Draft | Updated: 2026-09-11
> Source: debfoster 2.8 适配（`conan create` G2 轮，两级失败链）

## 背景

debfoster 2.8（2024-11-18 发布）在 changelog 里写着 "overhaul autotools build
system"。这次 overhaul 的产物是一个**自相矛盾**的发行 tarball：里面有生成好的
`configure`（283677 B）和各目录 `Makefile.in`，却没有它们的输入与辅助脚本。

```make
# Makefile.am
dist-hook:
	rm -f $(distdir)/autom4te.cache
	rm -f $(distdir)/config.guess*
	rm -f $(distdir)/config.sub*
	rm -f $(distdir)/aclocal.m4
	rm -f $(distdir)/missing
	rm -f $(distdir)/install-sh
	rm -f $(distdir)/depcomp
```

Debian 侧靠 `debian/rules` 的 `dh_autoreconf`（`dh $@` 序列的一部分）重建这些文件，
所以发行版用户看不到问题。OHOS 设备与 CI worker 都没有 autotools 工具链；即使装上，
`configure.ac` 还用了 autoconf-archive 的 `AX_CFLAGS_WARN_ALL`（树里没有该宏）与
gettext 的 `autopoint`，重建路径实际不可行。

## 现象（两级失败链）

### 第一级：configure 找不到辅助文件

```text
$ ./configure
configure: error: cannot find required auxiliary files: missing install-sh config.guess config.sub
```

退出码 1，configure 连第一行探测都没跑到。

### 第二级：补齐后 maintainer 规则触发

补齐 `config.guess`/`config.sub`/`install-sh`/`missing` 后：

```text
$ ./configure && make -j1
CDPATH="${ZSH_VERSION+.}:" && cd . && /bin/sh '.../missing' aclocal-1.16 -I m4
.../missing[85]: aclocal-1.16: inaccessible or not found
WARNING: 'aclocal-1.16' is missing on your system.
         You should only need it if you modified 'acinclude.m4' or
         'configure.ac' or m4 files included by 'configure.ac'.
make: *** [Makefile:375: aclocal.m4] Error 127
```

原因不是 `missing` 有问题，而是 automake 生成的 Makefile 里有：

```make
$(am__aclocal_m4_deps):

$(ACLOCAL_M4):  $(am__aclocal_m4_deps)
	$(am__cd) $(srcdir) && $(ACLOCAL) $(ACLOCAL_AMFLAGS)
```

`aclocal.m4` 不存在，而依赖 `configure.ac` 与 `m4/*.m4` 在解压后比 `Makefile.in`
新，于是 make 认为必须重建 `aclocal.m4`，去跑 `$(ACLOCAL)`（值为
`${SHELL} '.../missing' aclocal-1.16`）。

注：这里 `missing` 的 127 是**真实失败**，不能当噪音忽略。GNU automake 1.18.1 的
`missing` 在第 85 行真的执行 `"$@"; st=$?`，失败后打印建议并以 `exit $st` 结束
（`st` 保持 127），不存在"打印空白成功行返回 0"的伪成功模式——因此 `|| true` 或
忽略退出码都是错误的处置。

## 修复

### 1) 随配方交付辅助文件

`generated/` 放六个文件，`export_sources()` 与 `source()` 按**明确文件名**复制：

```python
_RESTORED_FILES = ("config.guess", "config.sub", "install-sh", "missing",
                   "depcomp", "aclocal.m4")

def export_sources(self):
    export_conandata_patches(self)
    for name in self._RESTORED_FILES:
        copy(self, name, os.path.join(self.recipe_folder, "generated"),
             os.path.join(self.export_sources_folder, "generated"))

def source(self):
    get(self, **self.conan_data["sources"], strip_root=True)
    for name in self._RESTORED_FILES:
        copy(self, name, os.path.join(self.export_sources_folder, "generated"),
             self.source_folder)
```

**为什么不用 `generated/*` 通配**：同一目录里必须放一份 `PROVENANCE.md` 记录每个文件的
来源与 sha256（W4 会核对），通配会把它也复制进源码树。曾经踩过一次，改成按文件名
逐个复制。

### 2) `aclocal.m4` 用带说明的占位文件

它只是 autoconf 的输入，而 `configure` 是随包发布的现成产物、不会被重新生成，
因此该文件不会被读取。存在的唯一目的是让 `$(ACLOCAL_M4): $(am__aclocal_m4_deps)`
这条前置条件成立。文件头部写清"为什么存在、为什么不会被读"。

### 3) 钉平整条 autotools 依赖链的时间戳

```python
def _pin_autotools_timestamps(self):
    stamp = 978307200  # 2001-01-01，早于任何真实输入
    suffixes = (".m4", ".am", ".in", ".ac")
    exact = ("configure", "config.guess", "config.sub", "ltmain.sh",
             "compile", "depcomp", "missing", "install-sh",
             "mkinstalldirs", "aclocal.m4", "config.h.in")
    for root, _dirs, files in os.walk(self.source_folder):
        for name in files:
            if name.endswith(suffixes) or name in exact:
                os.utime(os.path.join(root, name), (stamp, stamp))
```

GNU make 把"mtime 相等"判为最新，所有 maintainer 规则都不再触发，随包发布的
`configure` 及其补丁完整保留。仓库先例：
`archives/b/boolstuff/0.1.16/conanfile.py` 的 `_pin_autotools_timestamps()`
（同样技巧，用于补丁改写 `configure` 之后的场景）、
`archives/a/advancescan/1.18/conanfile.py`（用 `os.utime` 把源文件设旧、
生成物设新，同一目的的另一写法）。

### 4) 必须留下"configure 未被重新生成"的旁证

否则配方可能悄悄丢掉 `configure` 上的补丁，而且只在下次以别的形式爆炸。三条旁证
（debfoster 实测全部成立）：

| 旁证 | 命令 | 期望 |
| --- | --- | --- |
| 没有重生成调用 | `grep -n 'aclocal\|automake\|autoconf' reports/conan-create.log` | 无调用行 |
| 三元组来自补丁后的 config.guess | `grep -n 'checking build system type' reports/conan-create.log` | `aarch64-unknown-linux-ohos`（上游 2024-07-27 版脚本认不出 `uname -s = HarmonyOS`，只会 `cannot guess build type`） |
| configure 内的补丁仍生效 | 看运行时生成的 `config.status` 中 `umask 022` | 存在（E011 场景下 configure 一旦被重生成，`umask 077→022` 补丁即丢失并立刻复现 `subs1.awk: Permission denied`） |

第三条尤其重要：E011 的 umask 补丁打在 `configure` 上，而本模式的核心风险正是
`configure` 被 maintainer 规则重生成。

## 与既有条目的差异

- **E041（bypass-autotools）**：针对 autotools 版本不匹配，建议
  `ACLOCAL=/bin/true AUTOHEADER=/bin/true AUTOMAKE=/bin/true ./configure` 绕过重生成。
  本模式下该做法不成立也不完整：发行 tarball 里根本没有 `config.guess`/`config.sub`/
  `install-sh`，仅把 `ACLOCAL` 指向 `/bin/true` 过不了第一级检查；而且把重生成
  变成"静默 no-op"仍会在别处留下不一致的生成物。
- **DRAFT-6048（babeltrace 1.5.11）**：覆盖的是"`configure` 存在但被 maintainer
  规则重新运行 autoconf"这一阶段，落点是时间戳钉平。本条覆盖的是更前一级的
  **上游发行缺陷**：辅助文件被 `dist-hook` 删除，连 `configure` 都跑不起来，交付物里
  多出"随配方交付 generated/ + 占位 aclocal.m4"这一环。时间戳钉平这一环 6048 已经
  覆盖，本条引用而不重复论证。

## 复现

`archives/d/debfoster/2.8/`：删掉 `generated/` 的交付与 `source()` 里的复制即复现
第一级；只保留前四个文件、不放 `aclocal.m4` 即复现第二级（`acl-1.16 ... Error 127`
形态为 `aclocal-1.16: inaccessible or not found`）。

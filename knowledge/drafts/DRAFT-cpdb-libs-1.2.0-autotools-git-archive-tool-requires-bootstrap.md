# DRAFT-cpdb-libs-1.2.0-autotools-git-archive-tool-requires-bootstrap — git-archive 型 autotools 包无 configure 时用 conan tool_requires 注入 automake/libtool 自举

- 触发事件：cpdb-libs 1.2.0 适配，conan create 首跑 build() 自举即败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-cpdb-libs-1.2.0-autotools-git-archive-tool-requires-bootstrap

## 现象

上游 release 页 tag v1.2.0 无任何 dist 资产（`releases/download/...tar.gz`
404），只有 GitHub 自动生成的 git archive。解包后源码目录不含
`configure`/`Makefile.in`（autotools 生成文件不进版本库），只有
`configure.ac`、`Makefile.am`、`autogen.sh`。配方 build() 若直接跑
`./configure` 会报 "No such file"；跑 `autoreconf -fi` 时本机/CI 沙箱报：

```
Can't exec "libtoolize": No such file or directory
autoreconf: error: libtoolize failed with exit status: 2
```

或（依赖 automake 的项目）`aclocal: command not found` / `automake: command not found`。

## 根因

1. 上游未为该 tag 生成 release dist tarball（dist 包才含 configure/Makefile.in）；
2. git archive 不含 autotools 生成文件——configure.ac/Makefile.am 必须经
   autoreconf 才能变成可执行构建；
3. CI/worker 沙箱（USER=100）的 `/data/service/hnp/bin` 只有 autoconf 家族
   （autoconf/autom4te/autoreconf），没有 aclocal/automake/libtoolize；
   `$HOME/.local` 手工安装的工具沙箱不可见（ENOENT）；
4. 既有 2.0-b5 方案（用 dist tarball 里的 configure/Makefile.in + 补丁 +
   刷新时间戳避免再生成）无法沿用——因为本版本根本没有这些生成文件可补。

## 修复

配方 `build_requirements()` 声明 tool_requires（registry 已发布）：

```python
def build_requirements(self):
    self.tool_requires("automake/1.18")
    self.tool_requires("libtool/2.5.4")
```

conan 按 *build* profile 解析，把两者的 bin（aclocal/automake/libtoolize）
注入 conanbuild 环境的 PATH/ACLOCAL_PATH。build() 内：

```python
def build(self):
    apply_conandata_patches(self)
    self._bootstrap_autotools()   # 无 configure 时跑 autogen.sh (autoreconf -fi, env="conanbuild")
    autotools = Autotools(self)
    autotools.configure()
    autotools.make(args=["-j1"])
```

关键点：

- `autoconf` 不声明为 tool_requires：SDK 已提供 autoconf/autom4te/autoreconf，
  声明会拉 OHOS-built perl/5.42.2，其 XS 与 SDK perl 5.42.0 冲突
  （见 DRAFT-6049-libnxml-0.18.5-autotools-perl-dual-arch）；
- `configure.ac` 含 `LT_INIT` 时必须有 libtoolize（由 libtool 包提供）；
- 若 `PKG_CHECK_MODULES` 报缺 pkg.m4，把 SDK pkg-config 的
  `share/aclocal` 与 libtool 包的 `share/aclocal` append 进 ACLOCAL_PATH；
- `autogen.sh` 需 `-e`（出错即中止）且显式 shell 执行，防止 shebang 被绕过
  后继续走到缺失的 configure。

## 验证

cpdb-libs 1.2.0 实测（conan create，`-pr:h`/`-pr:b=ohos-aarch64`）：

- apply 4 个补丁后 `autogen.sh`（autoreconf -fi）成功生成 configure；
- `configure`（--build/--host=aarch64-unknown-linux-gnu）-> `make -j1` ->
  `make check` 全部通过；
- W3 `build_and_test.sh` RC=0，L0/L1/L4/L5 pass；
- 消费者测试 `test_cpdb_libs_ohos` 12/12 PASS。

日志：`archives/c/cpdb-libs/1.2.0/reports/conan-create.log`。

## 适用边界

- 适用：tag 无 release dist 资产、conandata 指向
  `archive/refs/tags/...tar.gz`、源码包无 configure 的 autotools 库；
- 适用：registry 已发布 automake/libtool 的构建环境；
- 不适用：dist tarball 已含生成文件的库（沿用 2.0-b5 补丁+时间戳方案更省）；
- 反例/注意：若 configure.ac 需要 ax_* 宏而 SDK 无 autoconf-archive，需把
  对应 m4 放入 `source_folder/m4` 并 append ACLOCAL_PATH（abiword 先例），
  否则 configure 生成后因未定义宏 syntax error。

## 关联

- 相似：E178（环境缺 automake→autoreconf 失败，方案依赖环境新工具链）；
  本条目差异 = 用 conan tool_requires 从 registry 注入，CI 沙箱自包含；
- 前置：DRAFT-6049（autoreconf 自举时 perl 双源冲突，同一 tool_requires
  场景的相邻错误面）。

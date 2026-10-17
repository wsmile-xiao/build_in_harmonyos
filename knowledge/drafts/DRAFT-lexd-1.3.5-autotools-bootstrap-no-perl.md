# lexd 1.3.5：autotools 自举的两条路都断（perl 崩溃 / worker 缺 automake）

> Draft: DRAFT-LEXD-135-AUTOTOOLS-BOOTSTRAP-NO-PERL
> Stem: `DRAFT-lexd-1.3.5-autotools-bootstrap-no-perl` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-LEXD-135-AUTOTOOLS-BOOTSTRAP-NO-PERL
- **严重度**: 2
- **类别**: autotools|toolchain|perl|cross-compile|pkg-config|conan|ohos
- **触发工具**: conan|autoreconf|aclocal|perl|qemu-aarch64
- **阶段**: configuration

## 错误特征

`conan create` 在第一步 `autoreconf -fi` 就死：

```
lexd/1.3.5: RUN: autoreconf -fi
perl: warning: Setting locale failed. ...
qemu: uncaught target signal 11 (Segmentation fault) - core dumped
Segmentation fault (core dumped)
ConanException: Error 139 while executing
```

关键线索是 **rc=139（128+11）** 和依赖图里的 build context：

```
build    autoconf/2.72
build    perl/5.42.2        ← autoconf/automake 的传递依赖
build    automake/1.18
build    m4/1.4.19
```

## 根因分析

lexd 1.3.5 的 release tarball 只有 `configure.ac` / `Makefile.am`（**没有**
`configure`，也**没有** `autogen.sh`；GitHub 源码包里才有 `autogen.sh`，但它
内部还是调 `autoreconf -i`）。所以必须生成 configure，而两条路都实测走不通：

### 路 ①：`tool_requires(autoconf/automake)` → perl 崩溃

依赖图把 `perl/5.42.2` 拉进 build context。这个 perl 是 **musl 动态链接**：

```
$ file ~/.conan2/p/perl*/p/bin/perl
ELF 64-bit LSB pie executable, ARM aarch64, dynamically linked,
interpreter /lib/ld-musl-aarch64.so.1

$ qemu-aarch64 .../bin/perl -e 'print "ok\n"'
perl: warning: Falling back to a fallback locale ("locale name not determinable").
qemu: uncaught target signal 11 (Segmentation fault) - core dumped
rc=139
```

`autoreconf` 第一步（`aclocal`）就跑在它上面，因此整条链死在这里。
**注意**：即使配方里**不写** `tool_requires("perl")`，autoconf/automake 也会
传递引入它——`apertium/3.9.12` 的注释明确写了「故意不 tool_require perl」，
但真正的原因（传递依赖会引入）值得单独记一笔。apertium 记录的是同一 perl 在
**真机**上的 `Cwd.so: Perl_my_cxt_init: symbol not found`（ABI 损坏）；本地则是
musl 加载器缺失直接段错误。两种表现、同一个根因：**制品仓的 perl 不能当作
OHOS 构建机的可用 perl**。

### 路 ②：靠 CI worker 自带 autotools → 不完整

CI worker 只有 autoconf 2.72，**没有 automake / aclocal / m4 / pkg-config**。
这正是 `lttoolbox/3.7.6` 选择内置 autoreconf 产物的原因——它是本仓同问题的
**已绿先例**。

### 叠加坑：pkg-config 也靠不住

1. 制品仓的 `.pc` 以 `--prefix=/` 安装 → pkg-config 产出
   `-I/include` / `-L/lib`（**E355**）；
2. worker 上没有可依赖的系统 pkg-config 二进制（**E468**）；
3. 照抄别处配方加 `tool_requires("pkgconf/…")`，本仓实测该包的 package folder
   里**没有可用的 `bin/pkg-config`**。

## 解决方案

### ① 内置一次 `autoreconf -fi` 的产物

在有完整 autotools 的机器上，对**未修改**的 tarball 跑一次：

```bash
ACLOCAL_PATH=/usr/share/aclocal autoreconf -fi
# 需要 vendored 的文件（对比原始 tarball 只多这些）：
#   configure  aclocal.m4  Makefile.in  src/Makefile.in
#   INSTALL  install-sh  missing  depcomp
# （autoconf 2.71 + automake 1.16.5 + pkg.m4 齐全的环境生成）
```

放进 `patches/autotools/`，在 **`source()`** 里覆盖进源码树：

- `export_sources()` 把它复制到 `export_sources_folder`（`export_conandata_patches`
  只搬运 conandata 里登记的 patch，内置产物不是 patch）；
- `source()` 里 `get()` 之后立刻覆盖 —— **不能放 build()**：lttoolbox 实测在
  build() 里复制会被 Conan 的 source 目录管理在 `configure()` 与 `make()` 之间
  还原成陈旧的 `configure`；
- 复制时保住可执行位（`configure`/`install-sh`/`missing`/`depcomp`）；
- `build()` 保留兜底：`if not os.path.isfile(configure): autoreconf -fi`。

收益：**本地与 CI 走完全相同的代码路径**（满足 W0b「历史命令在 CI clean 环境
逐字可执行」），且构建期不需要任何 autotools 或 perl。

### ② 用 `<PKG>_CFLAGS` / `<PKG>_LIBS` 短路 pkg-config，**并且必须走 argv 而不是 os.environ**

`PKG_CHECK_MODULES` 在两个变量都已被设置时**不再调用 pkg-config**
（pkg.m4 的 user-gave 分支）。关键是**怎么把它们送进去**——`os.environ` 不够：

```python
# ❌ 会静默失效：self.run(..., env="conanbuild") 先 source conanbuild.sh，
#    而 conanbuild.sh 自己定义了 CPPFLAGS/LDFLAGS，会覆盖 Python 进程里的
#    os.environ 值。lexd 实测：一次 CI profile 的本地跑，configure 因此拿不到
#    -I<utf8cpp>/include，直接报 "You don't have utfcpp installed"。
#    本地另一套 profile 却能过 —— 典型的「只在某台机器上成立」。
# os.environ["LTTOOLBOX_CFLAGS"] = " ".join("-I%s" % d for d in dep.cpp_info.includedirs)

# ✅ 作为 ./configure 的 VAR=value 命令行参数（autoconf 的 ac_precious_vars
#    机制会 eval+export，configure:1171-1179），优先级最高，不受任何环境影响
flags = {
    "LTTOOLBOX_CFLAGS": ["-I%s" % d for d in lttoolbox_dep.cpp_info.includedirs],
    "LTTOOLBOX_LIBS":   ["-L%s" % d for d in lttoolbox_dep.cpp_info.libdirs]
                     + ["-l%s" % l for l in lttoolbox_dep.cpp_info.libs]
                     + ["-l%s" % l for l in lttoolbox_dep.cpp_info.system_libs],
    "CPPFLAGS": cppflags,      # 全部依赖的 -I（含 utf8cpp 子目录）
    "LDFLAGS": ldflags,        # 全部依赖的 -L
}
assignments = ['CC="%s"' % cc, 'CXX="%s"' % cxx]
assignments += ['%s="%s"' % (k, " ".join(v)) for k, v in sorted(flags.items())]
self.run("{} ./configure {} --prefix=\"{}\"".format(" ".join(assignments), toolchain_args, self.package_folder))
```

两点补充：

- `CPPFLAGS`/`LDFLAGS` 同样走 argv，否则 `AC_CHECK_HEADER` 探针找不到依赖头文件。
- 工具链自己算出的参数（如 E007/E205 的 `--build=aarch64-unknown-linux-ohos`）在
  **手写 configure 命令行**时极易被漏掉——`tc.configure_args` 不会被自动消费。
  必须在 `generate()` 里把它们存下来并在 `build()` 回放（lexd 首版就踩了这个坑：
  护栏成了死代码，原生 HarmonyOS 机器上 config.guess 仍会失败）。
  验证方式：构建后 `grep S[\"build_alias\"] config.status` 应看到三元组。

这样同时解决 E355（`.pc` 的 `prefix=/`）与 E468（worker 缺 pkg-config 二进制），
而且 build() 阶段对外部工具的依赖降到零（只剩编译器和 make）。

### ③ 配套的三个已知修复

| 知识号 | 处理 |
|--------|------|
| **E114** | `configure` 里 `umask 077 && mktemp -d` 在 HMDFS setgid 目录下产生不可写的 `drwx--S---` → 去掉 umask |
| **E041/E248** | `ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER/AUTOM4TE=':'` 中和 maintainer 规则（内置产物已最新，属空操作），避免 make 去调 worker 上不存在的 automake（Error 127） |
| **E074** | `make -j1`（HMDFS 下并行 jobserver fifo 报 EPERM） |

### ④ 提前解释 L4 噪声

内置文件里 `grep -cE '(strcpy|sprintf|gets|strcat)'` 会有命中（`configure` 3 处、
`Makefile.in` 9 处、`INSTALL` 2 处）——全部来自 autoconf 自身模板的 C 代码片段，
不是本包代码。L4 是 warn 不阻塞，但应在 notes.md 里写明，避免评审误判。

## 适用边界

- 适用于所有「发布包无预生成 configure」的 autotools 包在本仓的适配。
- **选型判断**：若 CI worker 上 perl 可用（且不是 musl 崩溃版本），
  `tool_requires` 路线（apertium 风格）更「干净」；否则内置产物更稳，
  代价是 PR 里多约 330KB 生成文件。
- 与 R36 无冲突：内置产物不引入任何新的运行时依赖，只是把生成步骤提前到
  配方之外，不影响依赖发布顺序。

## 关联

- 复用知识库 **E178**（autoreconf 补齐）、**E114 / DRAFT-6507**（umask 077）、
  **E041 / E248 / E071**（automake 重建规则）、**E074**（make -j1）、
  **E355**（`.pc` `prefix=/`）、**E468**（`PKG_CONFIG_PATH` 需自行追加）、
  **E007 / E205**（config.guess 不认 HarmonyOS）。
- 先例：lttoolbox/3.7.6（内置 autotools 产物，CI 已绿）；apertium/3.9.12
  （tool_requires + 记录 perl ABI 损坏）。
- 本条目来自 lexd 1.3.5（Apertium 词典编译器）HarmonyOS PC aarch64 适配。

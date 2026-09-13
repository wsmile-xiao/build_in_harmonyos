# ncdc 1.25：autotools 应用依赖发现「两路并行」适配
# （glib 多模块 .pc 产物名 + PKG_CHECK_MODULES / AC_CHECK_LIB 分流 + 无测试套件时的实跑自证）

## 场景

ncdc 1.25（NCurses Direct Connect 客户端，autotools，发布 tarball 自带
`configure`/`Makefile.in`，零 patch）适配 HarmonyOS PC。依赖 6 个：
ncursesw（TUI）、zlib/bzip2（`AC_CHECK_LIB`）、sqlite3（本地 db）、
glib-2.0+gthread-2.0（`PKG_CHECK_MODULES`）、gnutls（TLS）。

坑不在任何一个依赖的编译上，而在 **ncdc 的 `configure.ac` 用两套不同的机制
发现依赖**，而 `AutotoolsToolchain` 只覆盖其中一套的一半。

## 坑 1：`PKG_CHECK_MODULES([GLIB],[glib-2.0 gthread-2.0])` 报
## `No package 'glib-2.0' found`

### 现象

```text
checking for glib-2.0... no
configure: error: Package requirements (glib-2.0 gthread-2.0) were not met:
No package 'glib-2.0' found
```

### 根因：glib 配方的 `pkg_config_name` 是「非官方多模块产物名」

`PkgConfigDeps` 生成 `.pc` 时用的名字取自 `dep.cpp_info` 的
`pkg_config_name`（其次 `dep.ref.name`）。glib 配方把它设成
**`glib-2.0-unofficial`**（因为它一个包产出 glib-2.0 / gthread-2.0 /
gmodule-2.0 / gobject-2.0 多个 .pc），于是 conan 只生成
`glib-2.0-unofficial.pc`——**没有** `glib-2.0.pc` / `gthread-2.0.pc`。

而 glib 包内**自带**的上游 .pc 也不能用：glib 用 meson `--prefix=/` 构建，
其 `prefix` 字段是 `/`，`Libs` 指向 `/lib`、`Cflags` 指向 `/include/...`——
在 conan 隔离目录下是错的路径。

### 修法：在 generators 目录手写同名 .pc

`AutotoolsToolchain.environment()` 会把 `conanfile.generators_folder`
**prepend** 进 `PKG_CONFIG_PATH`（见 `conan/tools/gnu/autotoolstoolchain.py`
的 `env.prepend_path("PKG_CONFIG_PATH", self._conanfile.generators_folder)`），
所以在这个目录里写 `glib-2.0.pc` / `gthread-2.0.pc` 会被优先命中：

```python
def _write_glib_pcs(self):
    glib = self.dependencies.get("glib")
    if not glib or not getattr(glib, "package_folder", None):
        return
    root = glib.package_folder.replace("\\", "/")
    common = ("prefix={}\n"
              "libdir=${{prefix}}/lib\n"
              "includedir=${{prefix}}/include/glib-2.0\n"
              "includedir1=${{prefix}}/lib/glib-2.0/include\n\n").format(root)
    # glib-2.0.pc: Libs: -L${libdir} -lglib-2.0 ; Cflags: -I${includedir} -I${includedir1}
    # gthread-2.0.pc: Requires: glib-2.0 ; Libs: -L${libdir} -lgthread-2.0 -pthread
```

关键三行：`prefix` 指向 `dep.package_folder`、`includedir1` 必须是
`${prefix}/lib/glib-2.0/include`（`glibconfig.h` 在那里，不在
`include/glib-2.0`）、gthread 要 `Requires: glib-2.0` 才能带出 glib 的
`-I`/`-L`。

**同型适用**：任何「一个 conan 包产出多个上游 .pc 名」的依赖
（glib/gthread/gmodule/gobject、gtk 的 gdk/gtk、openssl 的 libcrypto/libssl、
libxml2 的 libxml-2.0 等），只要配方把 `pkg_config_name` 设成聚合名，
消费方按上游原名单查 `pkg-config` 就会 miss。先查
`conan list <pkg>/<ver>:* -r ohpcd` 看制品里到底有哪些 .pc 再决定补写。

## 坑 2：`AC_CHECK_LIB([z]/[bz2]/[sqlite3])` 找不到库

### 现象

```text
checking for library containing deflate... no
configure: error: zlib not found
```

### 根因：`AutotoolsToolchain` 不注入依赖的 `-I/-L`

`AutotoolsToolchain` 只处理编译器/架构/`configure_args`，**不会**把依赖
`cpp_info` 的 include/libs 写进 `CPPFLAGS`/`LDFLAGS`。`PKG_CHECK_MODULES`
那路靠 `.pc` 拿到路径尚可自洽，但 `AC_CHECK_LIB([z])` 是裸 `-lz` 探测，
没有 `-L` 就找不到 conan 里的 `libz.a`/`.so`。

### 修法：叠加 `AutotoolsDeps`

```python
from conan.tools.gnu import AutotoolsDeps
PkgConfigDeps(self).generate()
AutotoolsDeps(self).generate()          # ← 关键
tc = AutotoolsToolchain(self)
```

`AutotoolsDeps` 把所有 host 依赖的 `cpp_info` 聚合成：
`CPPFLAGS`（`-I` + defines）、`LDFLAGS`（`-L`）、`LIBS`（`-l<lib>` +
`system_libs`，**拓扑序**展开）。这一路同时解决了两件事：

- `AC_CHECK_LIB(z/bz2)` 的 `-L` 问题；
- **静态 gnutls** 的传递库：gnutls.pc 只给 `-lgnutls`，静态链接还需
  nettle/gmp/libtasn1/libgcrypt/libunistring，`AutotoolsDeps` 按依赖图
  拓扑序全部展开进 `LIBS`；若只靠 `PKG_CHECK_MODULES` 的 `.pc`
  `Requires` 链，一旦某个依赖的 `.pc` 没写全 `Requires` 就会漏
  （gnutls.pc 的 Requires 链在此恰好完整，但不应赌）。

**次序**：两个 generator 都写同一批文件（`conanbuild.sh` 等），
`AutotoolsDeps` 放 `AutotoolsToolchain` 之前/之后都行，但都要在
`tc.generate()` 之前 `generate()`。

## 坑 3：沙箱内 `config.guess`/`config.sub` 的写盘探针不可靠

configure 的自举三元组探测在 OHOS 沙箱里会误判（写临时文件、`uname -m`
与目标不一致等）。显式钉死：

```python
tc.configure_args.extend(["--build=aarch64-unknown-linux-gnu",
                          "--host=aarch64-unknown-linux-gnu"])
```

`host==build` 不会触发 `AC_RUN_IFELSE`（ncdc 的 `configure.ac` 里没有），
所以不会尝试“运行”任何目标二进制。

## 坑 4：`config.status` 写 `subs1.awk` 报 `Permission denied`（已收录 E011）

本坑**已有知识库条目 E011（`edit-umask-in-configure`）**，ncdc 是又一实例，
按 E011 推荐方法 2 处理即可，不另立新条目：

```text
./config.status: line 608: ./confMFAcCk/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

根因（E011）：HMDFS 的 UID 映射使 `umask 077 && mktemp -d ./confXXXXXX`
建的 `0700` 目录**对当前进程也不可写**（目录 owner UID 被映射为 20001006，
进程实际 UID 20020083）。

修法（E011 方法 2 的程序化形式）：在 `build()` 起始把 configure 内的
`umask 077` 全部替换为 `umask 022`：

```python
configure_path = os.path.join(self.source_folder, "configure")
with open(configure_path, encoding="utf-8") as fh:
    text = fh.read()
if "umask 077" in text:
    with open(configure_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text.replace("umask 077", "umask 022"))
```

**关键点：只需改 `configure` 一处。** configure 与它生成的 `config.status`
共用同一段 here-doc（临时目录创建逻辑被原样嵌入 config.status），所以改
configure 会同步落到 config.status，无须先 `--no-create` 再回改（即 E011
「方法 1」的失败场景在此不出现）。另注意 `TMPDIR` 无效——该临时目录建在
cwd 而非 TMPDIR，改环境变量绕不过去。

同类先例：`archives/c/cracklib/2.10.3`、`archives/a/abiword-plugin-*`。

## 坑 5：`make` 自己会**运行**刚编译出来的引导工具，`conanbuild` 却不管 host 依赖

### 现象

```text
Error loading shared library libgnutls.so.30: (needed by ./makeheaders)
Error loading shared library libgcrypt.so.20: (needed by ./makeheaders)
...（共 9 条，gnutls/gcrypt/gio/glib/gobject/gpg-error/tasn1…）
make[1]: *** [Makefile:1237: mkhdr.done] Error 127
```

### 根因：bootstrap 工具在**构建期**被 `make` 执行，但它链的是 **host** 依赖

ncdc 的 `Makefile.am` 有一个 `mkhdr.done` 规则：先编译 `deps/makeheaders`
（链 gnutls/glib/libgcrypt…），再**运行它**生成 `*.h`。而 `Autotools.make()`
默认用 `env="conanbuild"`，`conanbuild`（VirtualBuildEnv）**只覆盖
`tool_requires` 构建依赖**，不含 host 依赖的 libdir——于是 `makeheaders`
一启动就找不到自己 NEEDED 的 `.so`。

**这是一个容易漏的类别**：只要上游 Makefile 在构建期**运行**任何自产工具
（codegen/lexer/header 生成器），且该工具动态链接 host 依赖，就会踩。
`conanbuild` 给不了 host libdir；`conanrun`(VirtualRunEnv) 也只在
`test_package`/`conan run` 场景生成。

### 修法：把全部 host 依赖 libdir 以前缀形式喂给 make 进程

```python
def _host_libdirs(self):
    libdirs = []
    for dep in self.dependencies.host.values():
        pf = getattr(dep, "package_folder", None)
        if not pf:
            continue
        for libdir in dep.cpp_info.aggregated_components().libdirs:
            libdirs.append(libdir if os.path.isabs(libdir) else os.path.join(pf, libdir))
    return list(dict.fromkeys(libdirs))

prefix = 'LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" '.format(":".join(self._host_libdirs()))
self.run(prefix + "make -j1", env="conanbuild")   # 不能写 autotools.make(args=["-j1"])
```

**为什么不用 `tc.environment.append("LD_LIBRARY_PATH", …)`**：`AutotoolsToolchain`
的 environment 走 conan 的 env 应用链，会**覆盖** profile `[buildenv]` 里已有的
`LD_LIBRARY_PATH`（该 profile 用它给 lld 找 `libxml2.so.16`）；前缀写法里的
`$LD_LIBRARY_PATH` 展开是**运行期**的，天然保留上游取值。

## 坑 6：非递归 automake 的产物在**构建根**，不在 `src/`

### 现象

```text
/system/bin/sh: .../build-release/src/ncdc: inaccessible or not found
```

### 根因

ncdc 是**非递归**（non-recursive）autotools 工程：顶层 `Makefile.am` 里
`bin_PROGRAMS = ncdc`，而 `ncdc_SOURCES` 里的 `src/*.c` **只是源子目录路径**。
automake 把 PROGRAMS 建在**声明它的 Makefile.am 所在目录**（即构建根
`$(builddir)`），所以产物是 `…/build-release/ncdc`。
交叉印证：`doc/gendoc` 同理——构建根里的 `./gendoc` 生成 `doc/ncdc.pod`
（日志里 `CCLD gendoc` + `GEN doc/ncdc.pod` 同目录出现）。

判据：看 `CCLD <name>` 的目标名与对象路径——若对象是 `src/foo.o` 但链接步
只写 `CCLD ncdc`（不带 `src/` 前缀），就是非递归构建、产物在根。

## 坑 7：`test_package` 里 `conanrun` 的 `LD_LIBRARY_PATH` 不含**传递依赖** libdir

### 现象

```text
Error loading shared library libgnutls.so.30: (needed by .../p/bin/ncdc)
FAIL - ncdc --version 非零退出（OHOS 上加载共享依赖失败）
...（随后每个 gnutls_* 符号各报一条 symbol not found）
```

### 根因

`test_package` 的 `test()` 用 `env="conanrun"`（`generators = "VirtualRunEnv"`）
跑**打包后的动态可执行文件**，但该环境生成的 `LD_LIBRARY_PATH` 并未覆盖到
传递依赖（gnutls / nettle / gmp …）的 libdir——主程序 NEEDED 的共享库在
test 期无处解析。**注意 build() 内的自证不受影响**（配方已显式注入
`_host_libdirs()`），这反而**掩盖**了 test_package 侧的同一问题：同一个
二进制，build 期能跑、test 期不能跑，就是这条。

### 修法：在 `test_package/conanfile.py` 里同样显式汇总依赖 libdir

```python
libdirs = []
for d in self.dependencies.values():          # 含传递依赖
    pf = getattr(d, "package_folder", None)
    if not pf:
        continue
    for libdir in d.cpp_info.aggregated_components().libdirs:
        libdirs.append(libdir if os.path.isabs(libdir) else os.path.join(pf, libdir))
prefix = 'LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" '.format(":".join(dict.fromkeys(libdirs)))
self.run(f'{prefix}TMPDIR="{work}" "{bash}" "{test_sh}" "{ncdc}" "{work}"', env="conanrun")
```

**通用教训**：`package_type = "application"` 且动态链接 host 依赖的包，
其 `test_package` 不能只靠 `env="conanrun"` 定位运行期共享库——尤其当
依赖链较深（gnutls→nettle/gmp/libtasn1/libgcrypt/libgpg-error）。
「build 期能跑、test 期 `Error loading shared library`」是这一类的指纹。

## 流程教训：上游无测试套件时，「实跑自证」怎么写才不是空话

ncdc 的 `Makefile.am` 没有 `TESTS`/`check` 目标，发布 tarball 不含任何
测试用例 → **没有可 vendored 的上游测试**（`rule4` 通过率不适用，须在
body 里明说「上游 0 测试」而不是含糊略过）。

此时 `build()` 里对**真实二进制**实跑 `--version` 是有价值的自证，但
仅当断言能证明「**加载的是本配方打包的制品**」时才成立。ncdc 的
`--version` 恰好打印 **编译期版本 == 运行期版本** 的库版本行：

```text
ncdc 1.25 (built ...)
GLib 2.84.0 (2.84.0)
GnuTLS 3.8.10 (3.8.10)
SQLite 3.49.1 (3.49.1)
ncurses 6.6
GeoIP support: no
```

括号内是**运行期** `glib_check_version()` / `gnutls_check_version()` /
`sqlite3_libversion()` 实测值，括号外是**编译期**宏。二者相等 ⇔ 运行期
解析到的 so 就是打包的那份（若串到设备同名系统库，版本通常不等）。
这就是鸿蒙特有断言的价值：**在 mock/静态校验全部通过、但真机装的是
另一套库时要能发现**。

运行这两个探针还要给子进程 `LD_LIBRARY_PATH`：`conanbuild` 环境不保证
带它，而 musl 解析 `libglib-2.0.so` 自身 NEEDED 的传递依赖时**不继承
其 RUNPATH**（这也是 glib/2.84.0.2 把 proxy-libintl 静态链入的根因，
见下）。故 `build()` 里聚合全部 host 依赖 libdir 显式注入：

```python
libdirs = []
for dep in self.dependencies.host.values():
    pf = getattr(dep, "package_folder", None)
    if not pf: continue
    for libdir in dep.cpp_info.aggregated_components().libdirs:
        libdirs.append(libdir if os.path.isabs(libdir) else os.path.join(pf, libdir))
prefix = 'LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" '.format(":".join(dict.fromkeys(libdirs)))
self.run(prefix + '"{}" --version'.format(ncdc), env="conanbuild")
```

## 关系

- glib 的 `pkg_config_name` 命名坑与 DRAFT-nip4-9.1.5 的「glib/glib2 双包
  共存、.pc 同名」是同一族问题的两面：那边是同名 .pc **互相顶掉**，这边是
  **产物名 ≠ 上游查名**。诊断手法一致：先看制品里实际有哪些 .pc。
- glib 静态 intl 的根因（musl 不继承 RUNPATH → 依赖 g_libintl_* 来自
  libintl.so.8 时重定位失败）在 glib/2.84.0.2（R37）已从配方侧根治；
  ncdc 直接用 `glib/2.84.0.2` 即免疫，无需 override。
- `AutotoolsDeps` 补 `AC_CHECK_LIB` 路径的适用面：一切混用
  `PKG_CHECK_MODULES` + `AC_CHECK_LIB`/`AC_SEARCH_LIBS` 的 autotools 库/应用。
- 坑 4（`subs1.awk: Permission denied`）直接复用既有条目 **E011**
  （`edit-umask-in-configure`，severity 3）与 **E114**（`bypass-mktemp`，
  改走 TMPDIR 自建目录的替代法）；本草稿只补「configure 与 config.status
  共用 here-doc → 改一处即同步」与「TMPDIR 无效」两点实操细节。

# DRAFT-6048：babeltrace 1.5.11 autotools 适配五类坑的修复链

> Contributor: yanjiaxin | Status: Draft | Updated: 2026-08-24
> Source: PR #6048 feat(babeltrace): 1.5.11 适配 HarmonyOS PC（CI build #29565 失败链）

## 背景

babeltrace 1.5.11 是 autotools 老项目（configure 由 automake 生成），依赖
glib/2.88.0.1、popt、uuid。在 HarmonyOS PC（HMDFS 文件系统 + 系统旧版 GLib 48.0.x）
上做 Conan 适配时，`conan create` 依次暴露五类错误。逐项修复后本地完整通过
（configure / make / make install / test_package）。

## 错误 1：AM_PATH_GLIB_2_0 运行检测失败

### 现象

```text
checking for glib-2.0 >= 2.22.0 gmodule-2.0... yes
checking for GLIB - version >= 2.22.0...
*** 'pkg-config --modversion glib-2.0' returned 2.88.0, but GLIB (48.-2147483648.-16176855)
*** was found!
configure: error: glib is required in order to compile BabelTrace
```

### 根因

AM_PATH_GLIB_2_0 宏在非 cross_compiling 下会**编译并运行** conftest 程序，从
运行时链接的 libglib 读取 `glib_major_version` 等符号。CI worker 系统装了旧版
GLib 48.0.x，与 Conan glib/2.88.0.1 冲突：pkg-config 报 2.88.0，但 conftest
运行时加载到系统 glib，读到 48.-2147483648.-16176855（垃圾值）。

### 修复

configure 追加 `--disable-glibtest`：跳过 conftest 运行检测，仅保留
pkg-config `--atleast-version` 校验（2.88.0 >= 2.22.0 已通过，依赖版本满足）。

```sh
./configure --disable-glibtest --disable-debug-info \
    --prefix=/ --libdir=/lib --bindir=/bin --includedir=/include
```

## 错误 2：automake maintainer 规则重新运行 autoconf，覆盖 umask 替换

### 现象

```text
./config.status: line 865: ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
make: *** [Makefile:461: Makefile] Error 1
```

### 根因

HMDFS 上 config.status 生成临时目录 `./confXXXXXX` 用 `umask 077` → 0700 目录，
owner 映射导致 subs1.awk 不可写（E011 模式）。build() 中已对 configure 做
`umask 077 → 022` 替换，但 **automake maintainer 规则**在 make 阶段检测到
configure.ac/aclocal.m4/Makefile.am/m4/*.m4 比 configure 新时重新运行 autoconf，
重新生成的 configure 恢复 umask 077（证据：`b/configure~` 是替换版、`b/configure`
是再生成版，md5 不同）。

### 修复

替换 umask 后，把 autotools 依赖源文件时间戳设为过去（2000-01-01），确保
configure 最新、规则不再触发：

```python
_past = time.mktime((2000, 1, 1, 0, 0, 0, 0, 0, -1))
for _f in ("configure.ac", "aclocal.m4", "Makefile.am", "Makefile.in"):
    os.utime(os.path.join(self.source_folder, _f), (_past, _past))
# m4/*.m4 同样设为过去；最后 os.utime(configure, None) 保持最新
```

同时在 configure 运行后、make 前对生成的 config.status 再替换一次 umask
（E011 方法 2，双保险）。

## 错误 3：pcre2 的 .la libdir='//lib' 导致 libtool 解析失败

### 现象

```text
libtool: error: '//lib/libpcre2-8.la' is not a valid libtool archive
```

### 根因与修复

pcre2 配方的 .la 文件 `libdir='//lib'`（--prefix=/ 产生，E236 模式）。参照已合入的
libgsf 方案：generate() 中 patch `pcre2.pc` 的 Libs 为 .a 绝对路径，让 libtool
不解析 .la。路径必须从 `self.dependencies["pcre2"].package_folder` 取，不能硬编码
`~/.conan2/p/b/pcre2*/p`（CI 干净环境哈希目录不同）。

## 错误 4：--disable-python-bindings 反而启用 python（configure 解析 bug）

### 现象

```text
creating /lib/python3.12/site-packages
error: could not create '/lib/python3.12/site-packages': Read-only file system
make: *** [Makefile:727: install-exec-local] Error 1
```

### 根因

babeltrace 1.5.11 configure 的选项解析 bug：

```sh
if test ${enable_python_bindings+y}
then enableval=$enable_python_bindings; enable_python=yes
```

只要选项被设置（无论值），`enable_python` 无条件置 `yes`。传
`--disable-python-bindings` 反而**启用** python bindings，其 setup.py 在
make install 时写只读的 /lib。

### 修复

**不传** `--disable-python-bindings`，让 configure 走 else 分支
`enable_python=no`，正确禁用。

## 错误 5：install 布局与 test_package 断言

### 现象

```text
make: *** No rule to make target 'install'.  Stop.     # package() 阶段
sh: .../p/bin/babeltrace: inaccessible or not found     # test_package 阶段
Error parsing options.                                  # --version 不被支持
```

### 根因与修复

1. configure 未设 `--prefix=/` 时 make install 落到 `DESTDIR/usr/local/...`，
   Conan 标准布局（bin/、lib/、include/）为空 → 传
   `--prefix=/ --libdir=/lib --bindir=/bin --includedir=/include`。
2. 手工 configure/make 在 `self.source_folder` 运行时，`Autotools(self).install()`
   默认在 build_folder（build-release）执行 make install → "No rule to make target
   'install'" → package() 改为手工
   `make install DESTDIR={self.package_folder} -j1`（cwd=source_folder，
   -j1 避免 HMDFS make jobserver mkfifo 报错）。
3. test_package 冒烟断言用 `--help`（exit 0）而非 `--version`
   （babeltrace 1.5.11 CLI 不支持，exit 1）。

## 错误 6：.gitignore 误伤预生成产物导致 CI 缺文件（#30510）

### 现象

前五类修复提交后，CI build #30510 在新阶段失败：

```text
config.status: creating doc/Makefile
config.status: error: cannot find input file: 'lib/Makefile.in'
ERROR: babeltrace/1.5.11: Error in build() method, line 216
```

### 根因

`.gitignore` 的编译产物规则误伤 patches/autotools 预生成产物镜像：

```gitignore
archives/**/bin/
archives/**/lib/
archives/**/include/
```

`patches/autotools/` 镜像中恰好有 `lib/`、`include/`、`tests/bin/`、
`tests/lib/` 目录（configure.ac 的 AC_CONFIG_FILES 引用的 Makefile.in），
这 6 个文件从未被 git 提交（`git check-ignore` 命中、`git add` 静默跳过）：

- lib/Makefile.in
- lib/prio_heap/Makefile.in
- include/Makefile.in
- tests/bin/Makefile.in
- tests/bin/intersection/Makefile.in
- tests/lib/Makefile.in

本地构建用的是**工作区文件**（文件在磁盘上，即使未提交也能用），所以
本地通过；CI 从 git checkout 拿到的是**提交内容**，缺这 6 个文件 →
configure 生成 config.status 时找不到 lib/Makefile.in。这正是"本地通过、
PR 失败"的又一典型根因。

### 修复

1. `.gitignore` 为 babeltrace 的 patches/autotools 子目录加针对性例外：

```gitignore
!archives/b/babeltrace/1.5.11/patches/autotools/lib/
!archives/b/babeltrace/1.5.11/patches/autotools/include/
!archives/b/babeltrace/1.5.11/patches/autotools/tests/bin/
!archives/b/babeltrace/1.5.11/patches/autotools/tests/lib/
```

2. `git add` 补交 6 个 Makefile.in。
3. **模拟 CI checkout 核对**：`git archive HEAD <dir> | tar -x` 到临时目录，
   确认 Makefile.in 总数 = 30（configure.ac 的 AC_CONFIG_FILES 引用齐全），
   并在导出目录中完整跑一次 conan create 验证。

## 错误 7：lld 链接器缺 libxml2.so.16（E266，环境级）

### 现象

CI build #30527（及 #30500，不同 worker）在 make 链接 libbabeltrace.la 时失败：

```text
Error loading shared library libxml2.so.16: (needed by .../ohos/native/llvm/bin/lld)
Error relocating .../llvm/bin/lld: xmlFreeDoc: symbol not found
...
clang-15: error: unable to execute command: No such file or directory
clang-15: error: linker command failed due to signal
make: *** [Makefile:565: libbabeltrace.la] Error 1
```

### 根因

OHOS SDK 的 lld（`llvm/bin/lld`）是动态链接 ELF，NEEDED 依赖 `libxml2.so.16`。
CI worker 沙箱的默认库搜索路径找不到它（libxml2 装在
`/storage/Users/currentUser/usr/local/lib`，musl loader 默认不搜该路径）→ lld
无法启动 → clang 链接阶段失败。这是**环境级**问题（E266 精确匹配，多个 worker
同样失败），非 babeltrace 配方问题；本地 SDK llvm/lib 有实体 libxml2.so.16 故本地通过。

### 修复

参照已合入的 libgsf 方案：generate() 中对 AutotoolsToolchain 的 environment
前置 SDK llvm/lib 到 LD_LIBRARY_PATH，让 lld 加载到正确的 libxml2：

```python
env = tc.environment()
_llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
if not os.path.isdir(_llvm_lib):
    _cands = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
    _llvm_lib = _cands[0] if _cands else ""
if _llvm_lib:
    env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
tc.generate(env=env)
```

⚠️ 不能用 `-fuse-ld=GNU ld`（E266 文档的推荐方案）——libgsf 实测 GNU ld 产物
在 OHOS 沙箱中 `Permission denied (exit 126)` 不可执行（需 ELF 签名），lld 产物
才可执行。

## 验证

```sh
conan create . -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
    -pr:b=$HOME/.conan2/profiles/ohos-aarch64 \
    --build=missing --build="babeltrace/*"
```

完整通过 configure / make / make install / test_package（`babeltrace --help` exit 0）。
推送前用 `git archive HEAD <dir> | tar -t` 模拟 CI checkout，确认 patches/autotools
下 30 个 Makefile.in 全部在提交中（本地工作区有 ≠ 已提交）。

## 关系

- 类似 E007（configure/build 平台检测）、E011（HMDFS umask 077）、E114、
  E236（pcre2 .la libdir='//lib'）。
- 本草稿补充：AM_PATH_GLIB_2_0 运行检测可用 `--disable-glibtest` 跳过；
  automake maintainer 规则会重新运行 autoconf 覆盖脚本替换，需把依赖源文件
  时间戳设为过去；babeltrace configure 的 python-bindings 选项解析 bug；
  `.gitignore` 编译产物规则会静默漏掉 patches 预生成产物（本地通过 ≠ 已提交，
  推送前必须用 git archive 模拟 CI checkout 核对）。

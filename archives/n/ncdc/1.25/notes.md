# ncdc 1.25 适配笔记

## 编译环境

- 构建系统: autotools（发布 tarball 自带 configure/Makefile.in，无需自举）
- 编译日期: 2026-09-11
- 编译器: clang / clang++
- 状态: built
- 目标: OHOS armv8（原生构建，非交叉；CI 在 HarmonyOS 上直接 `conan create`）

## 编译步骤

配方 `generate()` 同时启用 `PkgConfigDeps` 与 `AutotoolsDeps`，再补充
`configure_args`，随后 `autotools.configure()` + `make -j1`：

```sh
./configure --without-geoip --without-libloc --disable-git-version \
            --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: No package 'glib-2.0' found` | glib 配方把 `pkg_config_name` 设为聚合产物名 `glib-2.0-unofficial`，`PkgConfigDeps` 只生成该名 .pc；glib 包自带的上游 .pc 用 meson `--prefix=/` 构建，prefix 为 `/` 不可用 | 在 `self.generators_folder` 手写 `glib-2.0.pc` / `gthread-2.0.pc`（prefix=dep.package_folder，`includedir1=${prefix}/lib/glib-2.0/include` 取 glibconfig.h，gthread `Requires: glib-2.0`）；`AutotoolsToolchain` 已把该目录 prepend 进 `PKG_CONFIG_PATH` |
| 2 | `checking for library containing deflate... no`（zlib/bzip2 找不到） | `AutotoolsToolchain` 不把依赖 `cpp_info` 的 `-I/-L` 写进 `CPPFLAGS`/`LDFLAGS`；`AC_CHECK_LIB` 是裸 `-l` 探测 | 叠加 `AutotoolsDeps(self).generate()`，注入全部依赖的 CPPFLAGS/LDFLAGS/LIBS（`-l` 按拓扑序展开） |
| 3 | 静态 gnutls 传递库缺失 | gnutls.pc 只给 `-lgnutls`，静态链接还需 nettle/gmp/libtasn1/libgcrypt/libunistring | 同上，`AutotoolsDeps` 按依赖图拓扑序展开全部 `LIBS` |
| 4 | 沙箱内三元组探测不可靠 | `config.guess`/`config.sub` 的写盘探针在 OHOS 沙箱里误判 | 显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（ncdc 的 `configure.ac` 无 `AC_RUN_IFELSE`，host==build 不会尝试运行目标二进制） |
| 5 | 实跑探针顾虑 glib 重定位 | musl 解析 `libglib-2.0.so` 自身 NEEDED 时不继承其 RUNPATH | 直接使用 `glib/2.84.0.2`（R37 已把 proxy-libintl 静态链入，制品只含 `libintl.a`）；`build()` 内实跑时再显式注入 `LD_LIBRARY_PATH`=全部 host 依赖 libdir |
| 6 | `./config.status: line 608: ./confMFAcCk/subs1.awk: Permission denied` → `could not setup config files machinery` | **知识库 E011**：HMDFS UID 映射使 `umask 077 && mktemp -d ./confXXXXXX` 建的 0700 目录对进程不可写（目录 owner UID 映射为 20001006，进程 UID 20020083）；该目录不走 TMPDIR | `build()` 起始把 configure 内 `umask 077` 全改 `umask 022`（E011 推荐方法 2，等价 `sed -i 's/umask 077/umask 022/g' configure`）；configure 与生成的 config.status 共用同一段 here-doc，改一处即同步生效（cracklib / abiword-\* 先例） |
| 7 | `Error loading shared library libgnutls.so.30: (needed by ./makeheaders)`（另有 libgcrypt/libgio/libglib… 共 9 条）→ `make[1]: *** [Makefile:1237: mkhdr.done] Error 127` | ncdc 的 `make` 会先编译并**运行** `deps/makeheaders`（生成 `mkhdr.done` 的 bootstrap 工具，链 gnutls/glib/libgcrypt）。`make` 以 `env="conanbuild"` 跑，而 `conanbuild`=VirtualBuildEnv 只含**构建**依赖 libdir，不含 host 依赖 → makeheaders 启动即找不到其 NEEDED 共享库 | `build()` 用 `_host_libdirs()` 汇总全部 host 依赖 libdir，以前缀 `LD_LIBRARY_PATH="…:$LD_LIBRARY_PATH" make -j1` 方式运行；同一前缀复用到 `ncdc --version/--help` 实跑自证。不用 `tc.environment` 是因其会覆盖 profile `[buildenv]` 里的 `LD_LIBRARY_PATH`（lld 依赖 libxml2.so.16），前缀写法保留 `$LD_LIBRARY_PATH` 不丢 |
| 8 | 实跑自证报 `/system/bin/sh: …/build-release/src/ncdc: inaccessible or not found` | ncdc 为**非递归** autotools 构建：顶层 `Makefile.am` 声明 `bin_PROGRAMS=ncdc`（`ncdc_SOURCES` 里的 `src/*.c` 只是源子目录路径），automake 规则把可执行文件建在声明它的 Makefile.am 同目录，即构建根 `$(builddir)/ncdc`；误按 `src/ncdc` 取则路径不存在 | 自证二进制路径改为 `os.path.join(self.build_folder, "ncdc")`（`doc/gendoc` 亦同：构建根 `./gendoc` 生成 `doc/ncdc.pod`，可交叉印证） |
| 9 | test_package 期 `Error loading shared library libgnutls.so.30: (needed by …/p/bin/ncdc)`（7 项断言全 FAIL） | `test_package` 以 `env="conanrun"`（VirtualRunEnv）运行打包后的动态可执行文件；该环境生成的 `LD_LIBRARY_PATH` **未覆盖传递依赖**（gnutls/netlle/gmp…）的 libdir，故主程序 NEEDED 的共享库在 test 期不可解析。build() 内自证因配方已显式注入 `_host_libdirs()` 而不受影响，掩盖了该问题 | `test_package/conanfile.py` 的 `test()` 汇总 `self.dependencies.values()` 全部依赖 libdir，以前缀 `LD_LIBRARY_PATH="…:$LD_LIBRARY_PATH"` 并入（保留 conanrun 既有取值），与 build() 侧 `_host_libdirs()` 同款做法 |

## 源码修改

无补丁（`patches_applied: []`）。`--disable-git-version` 让 `src/version.h`
走 `echo @VERSION@` 分支，取 `AC_INIT` 的 1.25，不依赖 git describe。

`build()` 内对 `configure` 的 `umask 077`→`umask 022` 为**构建期脚本修正**
（知识库 E011），仅作用于本次构建工作副本，不改动上游制品、不进
`patches_applied`（`patches: {}` 仍为空）。

## 依赖版本

| 依赖 | 版本 | Conan 引用 |
|------|------|-----------|
| ncurses | 6.6 | ncurses/6.6 |
| zlib | 1.3.1.1 | zlib/1.3.1.1 |
| bzip2 | 1.0.8 | bzip2/1.0.8 |
| sqlite3 | 3.49.1 | sqlite3/3.49.1 |
| glib | 2.84.0.2 | glib/2.84.0.2 |
| gnutls | 3.8.10 | gnutls/3.8.10 |

## 验证结果

上游无测试套件（`Makefile.am` 无 `TESTS`/`check`，发布 tarball 不含测试用例），
故以真实二进制实跑自证 + test_package 消费者断言（7 项）：

```bash
conan create archives/n/ncdc/1.25 -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing
# build() 内：ncdc --version / ncdc --help 实跑
# test_package（test.sh，7 项断言）：
#   ok - bin/ncdc 存在且可执行
#   ok - 自身版本为 1.25
#   ok - GLib 编译期==运行期 2.84.0
#   ok - GnuTLS 编译期==运行期 3.8.10
#   ok - SQLite 编译期==运行期 3.49.1
#   ok - ncurses 版本行存在
#   ok - GeoIP support: no
#   ok - --help 声明 --version
```

`--version` 输出示例：

```text
ncdc 1.25 (built ...)
GLib 2.84.0 (2.84.0)
GnuTLS 3.8.10 (3.8.10)
SQLite 3.49.1 (3.49.1)
ncurses 6.6
GeoIP support: no
```

括号内为运行期 `glib_check_version()` / `gnutls_check_version()` /
`sqlite3_libversion()` 实测值，括号外为编译期宏；二者逐一相等即证明运行期
加载的是本配方打包的 conan 制品。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/ncdc | 主程序（ncurses TUI 客户端） |
| licenses/COPYING | MIT 许可证 |

## 注意事项

- 应用类型包（`package_type = "application"`），`package_info()` 清空
  cpp_info 的 include/lib/libdirs，仅通过 `runenv_info` 把 `bin/` 加入 PATH。
- 上游 `configure.ac` 只提供 `--with-geoip` / `--with-libloc`（默认 no），
  配方显式 `--without-*` 以防误探测宿主库。

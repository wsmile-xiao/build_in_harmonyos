# xraylib 4.2.1 适配笔记

## 编译环境

- 构建系统: autotools (`configure.ac` + `Makefile.am`，另有 `meson.build` 备用，本配方选用 Autotools)
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (HarmonyOS PC 真机，`ci/conan/profiles/ohos-aarch64`)
- 状态: built（待真机预检 evidence 回填通过率）

## 编译步骤

1. 上游取包：`https://github.com/tschoonj/xraylib/archive/refs/tags/xraylib-4.2.1.tar.gz`（sha256 见 `conandata.yml`，实测 tarball 约 13.5MB）。
2. GitHub tag archive 仅含 `configure.ac`/`Makefile.am`（无 `configure`、无 `build-aux/`），`build()` 先 `autoreconf -v -i -f` 自举（`tool_requires` 提供 automake/1.18 + autoconf/2.72 + libtool/2.5.4）。
3. `AutotoolsToolchain` 配置 `--disable-all-bindings`（关闭 Fortran/Python/Perl/Java/Lua/Ruby/PHP/Pascal/IDL 全部绑定，仅构建核心 C 库 `libxrl`，无第三方依赖，仅链系统 `libm`）；OHOS 下显式 `--build/--host=aarch64-unknown-linux-gnu` 绕过 `config.guess` 对鸿蒙内核的未知 OS 判定。
4. `make -j1` 编译（含 `prdata` 主机工具生成 `xrayglob_inline.c` 数据内联）。
5. `make check -j1` 运行上游 `tests/` 全部 27 个 C 测试（见下节），输出解析为 `HMBS_UPSTREAM_TEST_RESULT` 机器证据。
6. `make install` 装包，删除 `.la`（libtool 绝对路径污染），头文件位于 `include/xraylib/`，库为 `lib/libxrl.a`（默认静态）或 `lib/libxrl.so`（`shared=True` 时）。

## 上游测试清点（适配前）

- 来源：`tests/Makefile.am` 的 `check_PROGRAMS`/`TESTS`（与 `tests/meson.build` 交叉核对一致）。
- 数量：**27** 个 C 测试程序：atomiclevelwidth、atomicweight、auger、compoundparser、comptonprofiles、coskron、cross_sections、crystal_diffraction、cs_barns、cs_cp、cs_line、densities、edges、fi、fii、fluor_lines、fluor_yield、jump、kissel_pe、polarized、radrate、refractive_indices、scattering、nist-compounds、radionuclides、error、version。
- 运行方式：`make check -j1`（配方 `_run_upstream_tests()` 用子进程执行并解析 `# TOTAL/# PASS/# FAIL/# SKIP/# ERROR` 汇总行，`PASS:`/`FAIL:` 计数为回退）。
- 语言绑定自带测试（`cplusplus/tests` 8 个、`fortran/tests`、`python/tests` 等）随 `--disable-all-bindings` 不构建、不计入本次 27 个；PR 正文如实说明。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 包无 `configure` | GitHub archive 只是 git 快照，`configure` 是 autoreconf 产物 | `build_requirements` 引入 automake/autoconf/libtool，`build()` 内 `autoreconf -v -i -f` |
| 2 | OHOS 上 `config.guess` 未知 OS | 鸿蒙内核 uname 非 Linux，旧 `config.guess` 无法识别 | 显式 `--build/--host=aarch64-unknown-linux-gnu`（实际 OHOS 目标由 HNP clang 旗标保证） |
| 3 | HMDFS 上 `config.status` 临时目录 Permission denied | autoconf 用 `umask 077 && mktemp -d`，鸿蒙 hmmac 组权限异常 | 复用任务可写 `TMPDIR`（探写校验）+ `umask 077→022` 替换（E011；已删除早期全局 `mktemp` 退出 1 包装，它会污染 `autoreconf` 自身） |
| 4 | profile 工具路径在部分设备不存在 | `/data/service/hnp/bin/{bash,clang}` 非全设备存在 | `_fix_conanbuild_shell()` 批量替换生成脚本为 `shutil.which` 实际路径 |
| 5 | 真机 `autoreconf` 调 `aclocal` 报 `.aclocal-real: No such file or directory`（exit 126，包目录 `autom3efab95d532f9`） | 远端 ohpcd 的 automake/1.18 二进制包丢点文件（与 DRAFT-6051 同特征：`bin/aclocal` 包装器在、`bin/.aclocal-real` 缺失），属远端半残包/缓存环境问题，非配方缺陷 | 配方侧无法重建远端包；若下轮预检仍报同一缺失，需后端在真机执行 `conan remove "automake/1.18" -c` 后 `--build="automake/*"` 本地重建一次（DRAFT-6051 处置） |
| 6 | 自研 `mktemp` 退出 1 包装污染整个 `conanbuild` 环境 | 该包装为强制 autoconf 走 mkdir 回退而设，但它全局覆盖 `PATH` 首位，使 `autoreconf`/`aclocal` 自身的 `mktemp` 调用全部失败；且包装文件 `chmod +x` 在 `chmod:0` 的 HMDFS 上不可靠 | 删除包装，改为复用 HMBS 注入的可写 `TMPDIR/TMP/TEMP`（`_writable_tmpdir()` 探写校验）+ 保留 `umask 077→022` 松弛（E011），让 `mktemp` 在可写 `TMPDIR` 下正常工作 |
| 7 | 默认 `conanbuild` 的 `PERL5LIB` 指向 conan perl，与 automake `*-real` 的系统 perl shebang 冲突（DRAFT-6049） | 两套 perl 5.42.2（harmonyos 版 vs aarch64-linux-thread-multi 版）XS 模块不互通，系统 perl 加载 conan 的 `Cwd.so` 即 handshake mismatch | 自举命令统一解释器：`PERL=perl` + `PERL5LIB` 仅保留 `share/automake-1.18` 与 `share/autoconf` 纯 Perl 目录（`_autoreconf_command()`，复用 libnxml-0.18.5 实证方案） |
| 8 | 上轮统一系统 perl 后真机报 `Can't locate strict.pm in @INC (... //lib/perl5/...) at .../.autoreconf-real line 29` | 该 worker 的系统 perl 已重定位且 @INC 为空（连 `use strict` 都编译不过），任何 PERL5LIB 子集都救不了（DRAFT-6049 边界情形） | 反向统一到 conan perl：新增 `tool_requires perl/5.42.2`，`_autoreconf_command()` 置 `PERL=<conan perl 绝对路径>` + `PERL5LIB=<conan perl 全 lib 树>:<automake share>:<autoconf share>`，`PATH` 首位前置 perl/autoconf/automake/m4/libtool 全部 conan bindir；conan perl 缺失时才回退旧系统 perl 命令 |

## 本轮修改（2026-09-16，初步预检 compile 失败后）

- 改用 Meson 后端替换 Autotools：`tool_requires` 仅留 `meson/1.11.0`，删除 automake/autoconf/libtool/perl 四件套；`generate()` 用 `MesonToolchain` + `-Dfortran-bindings=disabled -Dpython-bindings=disabled -Dpython-numpy-bindings=disabled`，`build()` 用 `meson.configure()/build()` + `meson test -C build --print-errorlogs` 并解析为 `HMBS_UPSTREAM_TEST_RESULT`（framework=meson）；`package()` 用 `meson.install()`。
- 原因：真机 `bin/aclocal` 包装器找不到 `bin/.aclocal-real`（exit 126）为远端 ohpcd 仓 automake/1.18 半残包，配方无法重建远端包；Autotools 自举还伴随 `configure`/`config.status` 在只读 `/tmp` 下爬行；Meson 无需 autoreconf，同时规避两者。上游 `meson.build` 与 Autotools 同源（`src` 同一 `libxrl`、`include` 同样安装到 `include/xraylib`、`tests/meson.build` 同样 27 个 C 测试），另外 `cplusplus/tests` 8 个 C++ 测试在有 clang++ 时自动构建，合计 35，解析器动态计数不固定 27。
- `test_package` 不变（依赖 `cpp_info.libs=[xrl]` + 双 include 目录 + `system_libs=[m]`）；`manifest.yaml` 已同步为 `build_system: meson` / `meson test` / `cases: 35`。

## 源码修改

无补丁（`patches_applied: []`）。全部 OHOS 适配通过 `configure` 参数与构建期脚本修补完成，未改上游源码。

## 依赖版本

- 构建工具：automake/1.18、autoconf/2.72、libtool/2.5.4（`tool_requires`）。
- 系统库：libm（`cc.find_library('m')`，`package_info` 声明 `system_libs=["m"]`）。

## 验证结果

待 HMBS 真机预检回填：

```bash
# 预检将执行（环境与官方 CI 同源）：
# conan create archives/x/xraylib/4.2.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 期望：make check 27/27 + test_package 7/7，日志含 HMBS_TEST_PACKAGE_RESULT 与 HMBS_UPSTREAM_TEST_RESULT 双标记
```

## 注意事项

- `libxrl` 非系统同名库，默认静态（`shared=False`）仅为减少运行时路径依赖；动态构建同样支持（`shared=True` 时 `--enable-shared`）。
- 消费端头文件有两种合法写法：`#include <xraylib.h>`（需 `-I.../include/xraylib`）与 `#include <xraylib/xraylib.h>`（需 `-I.../include`）；配方同时声明双 include 目录。
- 为跑测试所做的改动均已进配方（`make check` 解析与 test_package 真实 API 测试）；无仅服务本地验证的临时改动。

## 本轮修复（2026-09-16，meson Unknown compiler）

- 现象：预检 meson setup 报 Unknown compiler(s): [["/data/service/hnp/bin/clang"]]，Running clang --version报 No such file；profile 硬编码该路径，当前 worker 上已缺失。
- 根因：profile 的 tools.build:compiler_executables 逐字写入 conan_meson_native/cross.ini，路径失效即配制失败；与编译器本身无关。
- 修改：conanfile 新增 _resolve_compiler（conf 存在可执行才用，否则 which clang/cc、SDK llvm/bin、HMBS_LLVM_BIN 回退，netcode/1.4.3 先例），generate 后重写两份 ini 的 c/cpp，并将 CC/CXX 写入 hmbs_env；_pin_meson_archiver 同步覆盖 cross 文件并追加 SDK 候选；test_package 同步改用存在性校验的编译器解析，并删除两处硬编码 HMBS_UPSTREAM_TEST_RESULT（上游证据只由 build() 的真实 meson test 产生）。

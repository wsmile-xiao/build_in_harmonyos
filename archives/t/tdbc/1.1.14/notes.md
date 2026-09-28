# tdbc 1.1.14 适配笔记

## 编译环境
- 构建系统: autotools（TEA — Tcl Extension Architecture）
- 编译日期: 2026-09-24
- 编译器: clang（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标平台: OHOS arm64（profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（本地 conan-verify 与 W3 通过，未上传制品仓）

## 源码与版本核验
- 官方源: `https://prdownloads.sourceforge.net/tcl/tdbc1.1.14.tar.gz`
- sha256: `f517f9f6fd949a22b91c3721245c3daaa2a385f2cc24974c891237e94dfe69bc`
  （与 Debian `tdbc_1.1.14.orig.tar.gz` 完全一致，可交叉核验）
- 上游仓库: https://core.tcl-lang.org/tdbc/ （Fossil），README 声明 1.1.14
- `manifest.uuid`: `f44d62a848ccb8afbfbd4bcce8d1e9fa18327b8c8c9a626a0ef371fa56234072`

## 编译步骤（真实命令）
```bash
# 依赖（已发布可消费）
conan install --requires=tcl/8.6.16 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... -r=ohpcd --build=never
source conanbuild.sh                      # 注入 TCL_ROOT / PATH / LD_LIBRARY_PATH

bash configure --prefix=/usr/local --exec_prefix=/usr/local \
     --with-tcl=$TCL_ROOT/lib --enable-shared=yes \
     CC=clang tcl_cv_sys_version=Linux-6.6
make -j1
make test                                 # 上游 tcltest 套件
make install DESTDIR=<staging>
```

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./config.status` 第 561 行执行 `./confepmAlc/subs1.awk` 报 Permission denied，configure 以 exit=1 结束并输出 `could not setup config files machinery` | autoconf 生成的 configure/config.status 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录并在其中生成 subs1.awk；OHOS HMDFS 权限归一化后该目录/文件不可访问（与 tcl/8.6.16 的 E011 同源） | 把 configure 内 `umask 077` 改为 `umask 022`（configure 会把该模板写进新生成的 config.status，故只需改 configure）→ 固化为 `patches/0001-configure.patch`；配方 `build()` 仅 `apply_conandata_patches` 应用该补丁，不再改写生成文件（R6） |
| 2 | Makefile 中 `SHLIB_LD =` 为空（configure 能过但共享库链接命令残缺） | TEA 的 `tcl.m4` 无 HarmonyOS 分支：`uname -s` 返回 `HarmonyOS`，`tcl_cv_sys_version=HarmonyOS-HongMeng Kernel 1.12.0` 不匹配 `Linux*|GNU*|...` | configure 追加 `tcl_cv_sys_version=Linux-6.6`（autoconf 缓存变量，走官方 Linux 分支，与 tcl/9.0.3.2 配方同法） |
| 3 | `make install DESTDIR=...` 把 pkglibdir 装到 `${TCL_ROOT}/lib/tdbc1.1.14`（tcl 依赖包 cache 目录） | `TEA_PREFIX` 在未给 `--exec_prefix` 时继承 `TCL_EXEC_PREFIX`（tclConfig.sh 中为 `${TCL_ROOT}`），于是 `exec_prefix=${TCL_ROOT}`、`libdir=${TCL_ROOT}/lib` | configure 显式 `--prefix=/usr/local --exec_prefix=/usr/local`，安装全部经 DESTDIR 落在本包 staging |

> 无 `#ifdef __OHOS__` 类源码改动；除 config.status umask 一处生成脚本改动（已固化为补丁）外，其余均为构建参数层面的最小修改。

## 依赖版本
- `tcl/8.6.16`（build + run）：提供 `tclConfig.sh`（`TCL_ROOT` 占位）、`tcl.h`/`tclDecls.h`/`tclOO.h`、`libtclstub8.6.a`、`tclsh8.6`、`libtcl8.6.so`、`tcl8.6` 脚本库（TclOO 内置）
- 测试依赖 `tcltest 2.5.9`：由 tcl 包 `lib/tcl8/8.5/tcltest-2.5.9.tm` 提供
- 无其他第三方依赖；`tdbcmysql/tdbcodbc/tdbcpostgres/tdbcsqlite3` 是独立目标库（各自依赖 mysql-client / unixodbc / libpq / sqlite3），不属于本包

## 上游测试（真实执行）
```bash
make test TESTFLAGS="-verbose pass"
# all.tcl:  Total 13  Passed 13  Skipped 0  Failed 0
# 逐项：tdbc-1.1/1.2/1.3/1.4；tokenize-1.0/1.1/2.0/2.1/3.0/4.0/4.1/4.2/4.3 → 全部 PASSED
```
测试入口：`tests/all.tcl`（tcltest 2.2 驱动）→ `tests/tdbc.test`(4) + `tests/tokenize.test`(9)。

## 验证结果
```bash
# 安装树 smoke（staged tree）
TCLLIBPATH=<stage>/lib tclsh8.6 tdbc-smoke.tcl
# tcl=8.6.16 / tdbc version = 1.1.14 / tokenize OK / mapSqlState=CONSTRAINT_VIOLATION

# conan create（干净源码 + 补丁 + 依赖 → 构建 → 上游测试 → test_package）
conan create archives/t/tdbc/1.1.14 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing
# L1_UPSTREAM_RESULT: total=13 passed=13 skipped=0 failed=0 cases=13
# test_tdbc: Total 9 Passed 9 Failed 0
```

## 交付物
| 文件 | 说明 |
|------|------|
| lib/tdbc1.1.14/libtdbc1.1.14.so | Tcl 扩展共享库（dlopen 加载） |
| lib/tdbc1.1.14/libtdbcstub1.1.14.a | stub 静态库（供 C 扩展链接） |
| lib/tdbc1.1.14/{pkgIndex.tcl,tdbc.tcl,tdbcConfig.sh} | Tcl 包索引/基类脚本/配置 |
| include/{tdbc.h,tdbcDecls.h,tdbcInt.h} | 公共/内部头文件 |
| share/man/{man3,mann}/* | 参考手册 |

## 注意事项
- 目标机 tcl 包（tcl/8.6.16）内置 tdbc 1.1.10（`include/tdbc.h` + `lib/tdbc1.1.10/`）；本包为 1.1.14，消费时需保证 `TCLLIBPATH`/`auto_path` 顺序使 1.1.14 优先（`package require tdbc 1.1.14` 精确匹配可规避）。
- OHOS 不支持 make jobserver 的 mkfifo，构建统一 `-j1`。
- `clean-verify`（G0）在本机 HMDFS 临时目录下会因 `getcwd` 失败而报 `working directory cannot be determined`（环境限制）；等效且更强的验证由 `conan create`（G2）完成。

## 状态
状态: built

## 对话记录

### 对话 #1
- 目标：为 tdbc/1.1.14 产出可复现的 Conan 配方（OHOS arm64），真实执行上游测试与消费者测试。
- 关键决策：Tcl 包形态（无 C 程序 test_package），依赖 tcl/8.6.16；三处 OHOS 适配（umask 022 / tcl_cv_sys_version=Linux-6.6 / 显式 exec_prefix）。
- 结果：上游测试 13/13 通过、test_package 9/9 通过（含 2 项鸿蒙特有断言）、conan-verify G1-G4+L2/L4/L5 全 PASS、W3 本地 CI 模拟通过（.ci-result.json exit_code=0）。
---

**编译结束**: 2026-09-24 19:25
**最终状态**: built

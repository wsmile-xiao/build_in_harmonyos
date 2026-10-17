# polylib 6.01 适配笔记

## 编译环境
- 构建系统: autotools（发布包自带 configure / Makefile.in，无需 autoreconf）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- Conan: 2.29.1（OHOS 适配版）+ profile ci/conan/profiles/ohos-aarch64
- 状态: built（本机 W3 验证通过，未发布）

## 编译步骤

```bash
# 1. 源码（官方站点，sha256 与 AUR polylib 6.01 打包记录一致）
#    https://icps.u-strasbg.fr/polylib/polylib_src/polylib-6.01.tar.gz
#    sha256=ba2f42aa2b342a565c346e717c4a4bdc08c16ca4d113eda6a7d4e95d978343d3
# 2. 应用 patches/0001..0004（config.guess、config.sub、configure、errors.c）
# 3. 配置：gmp 由 AutotoolsDeps 注入的 CPPFLAGS/LDFLAGS 自动探测
./configure --prefix=<prefix> --enable-static --disable-shared
make -j2
make -C Test check        # 上游回归（32/64/gmp 三套整数表示）
make install DESTDIR=<staging>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./config.guess` 报 "unable to guess system type"；官方 `patch-autotools-ohos.pl` 显示 `HarmonyOS=1` 但脚本仍失败 | 6.01 自带 config.guess 是 2018-02-24 老式 echo 风格，官方脚本按新版 GUESS 变量风格插入分支，赋值后无人输出 | 0001：把 HarmonyOS 分支改写为 echo 风格（`echo "$UNAME_MACHINE"-unknown-linux-ohos; exit`），并补 `__OHOS__` libc 探针；实测 `./config.guess` → `aarch64-unknown-linux-ohos` |
| 2 | `config.sub aarch64-linux-ohos` 报 `system 'ohos' not recognized` | 老式 config.sub 的 maybe_os 名单与 KERNEL-OS 校验名单都不含 linux-ohos | 0002：两处名单各加 `linux-ohos*` / `-linux-ohos*`；实测 `config.sub aarch64-linux-ohos` → `aarch64-unknown-linux-ohos` |
| 3 | `./config.status[1025]: can't create ./confy6mA13/subs1.awk: Permission denied` / `could not setup config files machinery` | HMDFS 上 autoconf 用 umask 077 建的 confXXXXXX 私有目录对创建者不可写（E011/E136） | 0003：configure 内两处 `umask 077` → `umask 022`（与 adns/aespipe/barvinok 的 PolyLib 补丁同法）；配置随即成功 |
| 4 | 带 `-DNDEBUG`（Conan Release）构建后首个用例目录 71 次执行全部崩溃（0 通过、68 例与基线不符） | `assert(pthread_once(...) == 0)` 等副作用在 NDEBUG 下被编译掉，TLS 异常栈永不初始化 | 0004：把 errors.c 中 6 处 assert 副作用改写为 `if (...) abort()`；NDEBUG 下复测 426/426 通过 |

补充实测（问题 4 的对照）：无 `-DNDEBUG` 时上游回归 426/426 通过；`CFLAGS="-g -O2 -DNDEBUG"` 复现 71 次执行全部崩溃、68 例 diff 失败（Tests.mk 于首个用例目录中止）；应用 0004 后在 NDEBUG 下 426/426 通过。

## 源码修改

- `0001-config.guess.patch`：HarmonyOS/`__OHOS__` 识别，输出 `aarch64-unknown-linux-ohos`（E007）
- `0002-config.sub.patch`：接受 `linux-ohos` 内核-OS 组合（E007）
- `0003-configure.patch`：config.status 临时目录 umask 022（HMDFS，E011/E136）
- `0004-source-arith-errors.c.patch`：NDEBUG 下保留 pthread 异常栈初始化（bugfix，非平台专属）

四个补丁均由 `refresh-patch --auto`（编辑追踪器精准模式）从 `.orig`/`.work` 生成，未手工编辑补丁文件。

## 依赖版本

- `gmp/6.3.0.1`：制品仓已发布配方 + OHOS profile（armv8/clang15/Release）binary；
  `conan install --requires=gmp/6.3.0.1 --build=never` 命中 `01d92cf349a0dd98ff915f4bd99a04430171517f` 并成功安装。
- 无其他依赖；pthread 由 OHOS libc 提供。

## 验证结果

设备原生（aarch64-linux-ohos）实跑：

```bash
$ ./config.guess
aarch64-unknown-linux-ohos

$ ./configure --prefix=... # 成功，输出：
Polylib will be built with 32 64 gmp integer size(s)

$ make -C Test check
# bits=32:  134 passed / 0 failed   (Zpolytest 71、general 14、pp 8、ehrhart 38、ehrhart_union 2、ranking 1)
# bits=64:  146 passed / 0 failed   (Zpolytest 78、general 14、pp 8、ehrhart 43、ehrhart_union 2、ranking 1)
# bits=gmp: 146 passed / 0 failed
# 合计 426 passed / 0 failed / 0 skipped
```

安装产物（探索构建的 DESTDIR staging；该轮 configure 未禁用共享，故同时产出静态与共享）：
`lib/libpolylib{32,64,gmp}.{a,so,so.10,so.10.0.1}`、
`include/polylib/*.h`（含三个变体头）、`bin/` 20 个 CLI 工具、`lib/pkgconfig/polylibgmp.pc`。

消费者验证（test_package，容器视角）：C API 建单位正方形 polyhedron → 断言
dimension=2 / 4 facets / 4 vertices / round-trip 4 facets；CLI 用 c2p 复现同一
polyhedron（断言 Dimension:2、Constraints:4 Equations:0 Rays:4 Lines:0、顶点 (0,0)/(1,1)）。
静态与共享两种链接方式在设备上均实测通过。

## 上游测试清单（R51 三步法）

| 项目 | 说明 |
|------|------|
| 清点 | `Test/` 下 6 个用例目录：Zpolytest、general、pp、ehrhart、ehrhart_union、ranking；用例=每个 `.in` 输入与 `.out` 基线做 diff |
| 入口 | `make -C Test check`（顶层 `make check` 只有 `check: all`，不跑用例；`make tests` 未定义于顶层） |
| 注册数 | 32 位: 71+14+8+38+2+1=134；64/gmp: 78+14+8+43+2+1=146（ehrhart 的 EHRHART_64 与 Zpolytest 的 TEST_FILES 比 32 位多 5+7 个） |
| 实跑 | 32/64/gmp 三套整数表示各跑一遍：134 + 146 + 146 = 426，全 PASS，0 SKIP |
| 未跑 | 无（Test/Zpolytest/Makefile.am 注释中列出的 phideo1/phideo3/ZDisj11b/ZDomain13 等为上游明确标注「不检查」的用例，不计入注册数） |

## 注意事项

- `--with-libgmp=DIR` 会进入 configure 的「只建 gmp 变体」分支；本配方不加该参数，
  由 AutotoolsDeps 注入 gmp 头/库路径，configure 自行探测后构建 32/64/gmp 三套。
- 安装期 pkg-config 文件只有 `polylibgmp.pc`（上游「Currently, we only create one .pc file」），
  与 cpp_info.libs=["polylibgmp"] 一致；32/64 变体库随包安装但需消费者显式引用。
- 补丁 0001 在 patches/ 中新增 `#ifdef __OHOS__` 探针（E007 标准做法，属 R8 允许的
  识别 libc 的探针程序例外），已在 PR 正文说明。
- 上游 `Test/` 目录依赖 `xyz` 输出文件（CLEANFILES），探索结束后已 `make distclean` 并核对
  `.orig`/`.work` 差异只剩四个目标文件。

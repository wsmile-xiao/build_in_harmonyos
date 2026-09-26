# libomxil 0.9.3 — 鸿蒙 PC 适配笔记

上游：Bellagio open source implementation of the Khronos OpenMAX
Integration Layer API（libomxil-bellagio），
<https://sourceforge.net/projects/omxil/>。
tarball 取 Debian 官方 orig（`libomxil-bellagio_0.9.3.orig.tar.gz`，
sha256 `593c0729…34d74c`），与 SourceForge 0.9.3 发布版一致。

## 定位

- 交付物为完整 OpenMAX IL 运行时：核心库 `libomxil-bellagio.so`、
  动态组件加载器 `lib/omxloaders/libomxdynamicloader.so`（核心 dlopen）、
  Bellagio 组件集 `lib/bellagio/*.so`、注册工具 `bin/omxregister-bellagio`、
  Khronos IL 公共头 `include/OMX_*.h` 与 Bellagio 扩展头 `include/bellagio/`。
- 无外部构建/运行依赖：核心库仅链接 libc/pthread/dl（musl 已折叠后两者）。
- Bellagio 是注册表驱动的：部署后必须先用 `omxregister-bellagio` 生成组件
  注册表，`OMX_Init()` 才能成功（无注册表返回 ENOENT），见 §消费注意。

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | autotools（发布包内置 configure，无需 autoreconf） |
| profile | `os=OHOS arch=armv8 compiler=clang/15 build_type=Release`（CI 为设备原生构建，`-pr:h` 与 `-pr:b` 同为 `ci/conan/profiles/ohos-aarch64`） |
| 依赖 | 无（R36 无涉） |
| 关键 configure 参数 | `--disable-dependency-tracking --disable-static` + `ac_cv_func_malloc_0_nonnull=yes`、`ac_cv_func_realloc_0_nonnull=yes` |
| 补丁 | 6 个，全部只做平台移植性修复（见 manifest.yaml patches 段与 conandata.yml） |
| 本地验证 | WSL2 (x86_64) + qemu-user（binfmt 注册 qemu-aarch64，`QEMU_LD_PREFIX=/opt/ohos-guest` 仿真执行 aarch64 musl 制品） |

## 上游测试用例情况

上游 0.9.3 不随源码发布自动化测试（无 `TESTS`/`check_PROGRAMS`），
上游用例数 = 0（`test_package/MANIFEST.yml` 中 `upstream_tests: []`）。
适配后以 `test_package/test.c` 从消费者视角补全核心 IL API 验证（6 项断言，
覆盖注册表驱动的完整运行时路径），并追加 8 项鸿蒙特有测试（H1~H8，验证
AArch64 ELF、OHOS 加载器、无 glibc soname、dlopen 入口符号），合计 14 项。

## 关键适配点

### 1. 六个移植性补丁（唯一改动上游文件之处）

| 补丁 | 内容 |
|---|---|
| 0001 config.guess | 增加 HarmonyOS 分支输出 `<machine>-unknown-linux-ohos`（libm17n-core 同款；否则设备原生 configure 落入 dummy.c 兜底探测、被 worker 存储拒绝 → cannot guess build type） |
| 0002 config.sub | 接受 aarch64 ohos 三元组（本包捆绑的 config.sub 较旧，不像 m17n 1.8.6 那样开箱即收） |
| 0003 configure umask | `./confXXXXXX` 辅助目录 umask 077→022（HMDFS 上 0700 目录致 `subs1.awk: Permission denied`，E011/E533 先例） |
| 0004 去 -Werror | OHOS clang 15 对 2009 年代源码大量告警，`-Werror` 把告警升级为构建失败 |
| 0005 rm.h extern | `src/base/rm.h` 的队列/注册表全局变量改为头文件 extern 声明 + `rm.c` 单点定义（lld 默认 `-fno-common`，拒绝旧头文件在每个编译单元里的重复定义，链接期 duplicate symbol） |
| 0006 loader 链接 core | `src/dynamic_loader/Makefile.am` 与随包 `Makefile.in` 同步补 `LIBADD = $(top_builddir)/src/libomxil-bellagio.la`。上游未给 loader 插件任何 `LIBADD`，插件因此没有 `DT_NEEDED` 指向 core，只靠宿主进程提供 `RM_Init`；而 dlopen 出来的对象在 musl 上只从**自身依赖链**解析符号，于是 H7 报 `RM_Init: symbol not found`（先以 `RTLD_GLOBAL` 预载 core 的绕法在 CI #61152 同样失败，已实测排除）。组件库 `src/components/*/Makefile.am` 本就有 `LIBADD`，走同一 dlopen 路径的 H8 一直通过，与该根因互为印证 |

### 2. `rpl_malloc` 假阳性（交叉/无法运行测试程序时）

`AC_FUNC_MALLOC`/`AC_FUNC_REALLOC` 判定依赖运行测试程序；无法执行时
autoconf 默认判"malloc(0) 返回 NULL"，`config.h` 出现
`#define malloc rpl_malloc`，而上游不提供 `rpl_malloc` 实现，编译报
incompatible integer to pointer conversion。预置
`ac_cv_func_malloc_0_nonnull=yes` / `ac_cv_func_realloc_0_nonnull=yes`
（musl 与 glibc 均为"malloc(0) 返回唯一指针"，libm17n-core 同款处理）。

### 3. `make -j1`：automake 1.11 时代递归 Makefile 非并行安全

上游递归 Makefile 存在跨目录依赖（src/base 先于 src/core 等），并行构建
偶发碎裂；配方固定 `make -j1`（构建体量小，无感知）。

### 4. 上游 docdir/DESTDIR bug 与 package() 清理

上游顶层 Makefile.am 把 `$(DESTDIR)$(prefix)` 写死进 `docdir`，automake
的安装规则再前置一次 `$(DESTDIR)`，`make install DESTDIR=<pkg>` 产生嵌套的
`<pkg>/<pkg>//share/doc/libomxil-bellagio` 目录树（顶层目录名为构建机
包路径的首段）。`package()` 丢弃 `bin/include/lib` 之外的所有顶层残留并打
info 日志；同时剔除 libtool `.la`（其中烧死了构建期 libdir，消费方链接会
指向 `//lib`）与 `share/`。

### 5. omxregister-bellagio 的退出码不可信

上游 `main()` 对多数错误路径（如组件目录打不开）只 DEBUG 打印并返回 0，
退出码不能作成败判据。`test_package` 改为验证注册表文件生成且非空，
再用 `test_probe` 走完整 IL API（见 §验证结果）。

### 6. 打包收尾：ELF 代码签名

`package()` 末尾（所有会改动字节的步骤之后）调用 `_sign_elfs()`：
对 `lib/` 全部 `.so*`（含 bellagio/、omxloaders/ 子目录）与 `bin/`
可执行文件先 `llvm-objcopy --remove-section .codesign` 再
`binary-sign-tool sign -selfSign 1`。工具仅存在于 OHOS worker，本地与
CI 构建自动跳过（info 提示），设备侧流水线自签。

## 依赖

无外部依赖（R36 不适用）：核心库仅链接 libc/pthread/dl，musl 已折叠
pthread/dl，制品 `DT_NEEDED` 仅 `libc.so`（见 §验证结果 制品检查）。
构建与运行均不引入 conan 制品依赖或系统库依赖。

## 源码修改

仅通过 `patches/` 内 6 个移植性补丁改动上游文件，配方不内嵌/改写源码：

- `0001-config.guess-harmonyos.patch`：config.guess 增加 HarmonyOS 分支
- `0002-config.sub-ohos-aarch64.patch`：config.sub 接受 aarch64-ohos 三元组
- `0003-configure-umask-022.patch`：configure 辅助目录 umask 077→022（HMDFS）
- `0004-no-werror.patch`：去除 `-Werror`（OHOS clang 15 对老代码告警密集）
- `0005-extern-rm-globals.patch`：`rm.h` 全局变量改 extern 声明（lld `-fno-common`）
- `0006-dynamic-loader-link-core.patch`：loader 插件补 `LIBADD` 指向 IL core
  （修 H7 `RM_Init: symbol not found`，见 §关键适配点 1）

上游测试用例未修改（上游 0.9.3 无自动化测试）；`test_package/` 为新增的
消费者视角验证，不属于上游源码修改。

## 验证结果

### 本地干净构建（WSL，与 CI 同参数）

```
$ conan create archives/l/libomxil/0.9.3 \
      -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
conan create exit=0（两次复验，含 package() 清理修复后复跑）
包 ID 01d92cf349a0dd98ff915f4bd99a04430171517f
======== Testing the package: Executing test ========
（build==host，非交叉判定：注册表生成 + test_probe 全量执行，见下）
```

### 运行时功能验证（qemu 仿真执行 aarch64 musl 制品）

```
$ export QEMU_LD_PREFIX=/opt/ohos-guest
$ export OMX_BELLAGIO_REGISTRY=/tmp/omxregister-probe
$ pkg=/root/.conan2/p/b/libom6179750a5136c/p
$ LD_LIBRARY_PATH=$pkg/lib $pkg/bin/omxregister-bellagio $pkg/lib/bellagio
rc=0；注册表写入 4 个组件：OMX.videoscheduler / OMX.clocksrc /
OMX.volume / OMX.audiomixer（audio_effects 库注册后两个组件）

$ LD_LIBRARY_PATH=$pkg/lib LIBOMXIL_PKG=$pkg ./test_probe
[1] OMX_Init            ok  OMX_Init() returns OMX_ErrorNone
[2] component enumeration
  component[0..7]（4 组件 × 2 loader，静态+动态各计一次）
  ok  OMX_ComponentNameEnum() ends with OMX_ErrorNoMore
  ok  the Bellagio component set is registered (>= 3 components)
  ok  OMX_GetHandle() instantiates the first component
  ok  OMX_FreeHandle() releases it
[3] OMX_Deinit          ok  OMX_Deinit() returns OMX_ErrorNone
[4] HarmonyOS-specific checks
  ok  H1: lib/libomxil-bellagio.so* is an AArch64 ELF64 shared object
  ok  H2: lib/omxloaders/libomxdynamicloader.so* is an AArch64 ELF64 shared object
  ok  H3: every lib/bellagio component is an AArch64 ELF64 shared object (>= 3)
  ok  H4: bin/omxregister-bellagio uses the OHOS aarch64 loader
  ok  H5: no packaged ELF needs a glibc-only soname
  ok  H6: DT_NEEDED of the IL core is exactly libc.so
  ok  H7: lib/omxloaders/libomxdynamicloader.so* dlopen()s and exports setup_component_loader
  ok  H8: every lib/bellagio component dlopen()s and exports omx_component_library_Setup
14 checks, 0 failure(s) (consumer=6, harmonyos_specific=8)
RESULT: PASSED
```

探针的 ELF 审计自行解析 ELF64 头（不依赖 sysroot 的 `<elf.h>`），
并用 `dlopen()` 实际加载产物，验证 `setup_component_loader`（加载器插件）
与 `omx_component_library_Setup`（组件库）两个上游入口符号在 OHOS
运行时可解析。注意 OHOS SDK 工具链给可执行文件写入的 PT_INTERP 是
`/lib/ld-linux-aarch64.so.1`（OHOS 两种拼写等价，见 H4）。

test_package 经 conan create 的 test 流程自动执行同样路径（conanrun 环境
提供 LD_LIBRARY_PATH），两轮构建结果一致。

### 制品检查（aarch64 ELF，L5 红线）

| 文件 | 类型 | SONAME | DT_NEEDED |
|---|---|---|---|
| lib/libomxil-bellagio.so.0.0.0 | ELF64 AArch64 DYN | libomxil-bellagio.so.0 | libc.so |
| lib/omxloaders/libomxdynamicloader.so.0.0.0 | ELF64 AArch64 DYN | libomxdynamicloader.so.0 | libomxil-bellagio.so.0, libc.so |
| lib/bellagio/libomx{audio_effects,clocksrc,videosched}.so.0.0.0 | ELF64 AArch64 DYN | 各自 .so.0 | libomxil-bellagio.so.0, libc.so |
| bin/omxregister-bellagio | ELF64 AArch64 DYN (PIE) | — | libomxil-bellagio.so.0, libc.so |

SONAME 均为相对名、DT_NEEDED 无绝对路径；libtool `.la` 与静态库已剔除。

## 消费注意

1. 部署后先生成注册表再 `OMX_Init()`：
   `omxregister-bellagio <prefix>/lib/bellagio`（写默认 `~/.omxregister`），
   或 `export OMX_BELLAGIO_REGISTRY=<path>` 后再执行。
2. 组件目录与 loader 目录（`${libdir}/bellagio`、`${libdir}/omxloaders`）
   是 configure 期烧进二进制的，包内布局自洽，勿单独搬动 `lib/`。
3. 包内上游 `.pc` 沿用 conan 构建前缀 `prefix=/`，消费方应使用 conan 依据
   `cpp_info` 生成的 `.pc`/CMake 目标，或 `deployer-folder` 部署后按需改写。

## 状态

`built` —— 本地 `conan create`（OHOS aarch64，与 CI 同 profile 设置）+
test_package 完整运行时路径（qemu 仿真执行）通过；
CI 设备原生构建结果以 PR 流水线为准。
---

**编译结束**: 2026-09-21 05:05
**最终状态**: built

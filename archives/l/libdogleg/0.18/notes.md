# libdogleg 0.18 编译笔记（HarmonyOS PC · Makefile + mrbuild）

## 定位

libdogleg（dkogan，LGPL-3.0-only）：Powell dogleg 信赖域法解非线性最小二乘，
稀疏路径走 CHOLMOD，稠密路径走 LAPACK（`dpptrf_`/`dpotrf_`）。C 库（约 2700 行），
Debian/Ubuntu 官方源同样收录（`apt install libdogleg-dev`），0.18 为当前最新 tag。

上游：<https://github.com/dkogan/libdogleg>（tag v0.18，commit b17d917）

## 上游源码审计（v0.18 tarball，12 个文件）

- 构建系统：裸 `Makefile`（43 行）+ `choose_mrbuild.mk`，全部编包规则来自 mrbuild 框架
- 库源码：`dogleg.c`（约 106KB）+ 公共头 `dogleg.h`（`#include <suitesparse/cholmod.h>`）
- 上游测试：`sample.c`（`--check` 自检：确定性种子，收敛 + 6 参数恢复断言）、
  `test-misc.c`（`DOGLEG_DEBUG_VNLOG` 位对齐，防 `dogleg_parameters2_t` ABI 回退）、
  `check.sh`（zsh 脚本，4 条 `./sample --check <模式>`）
- 上游**无** `tests/` 目录、`configure`、`CMakeLists.txt`；`make check` 即“构建两个
  二进制 + 跑 check.sh”
- 依赖：`-lcholmod -llapack -lsuitesparseconfig -lm`（见 Makefile LDLIBS）；
  `dogleg.c` 另有条件 `#include <suitesparse/cholmod_function.h>`（仅 CHOLMOD 2.x，
  本仓 suitesparse 7.8.3 为 5.x，自动跳过）

## 关键适配

### ① mrbuild 框架离线化（无补丁，source() 多取一个官方包）

`choose_mrbuild.mk`：有本地 `mrbuild/` 即用，否则要求 `apt install mrbuild`
或现场 `wget` 官方 tarball。CI/真机现场下载不可靠，配方在 `source()` 把官方
`dkogan/mrbuild` v1.13 tarball 取到源码树 `mrbuild/` 子目录（`conandata.yml`
顶层 `mrbuild` 键，sha256 已实测），`make` 自动使用本地框架，构建完全离线。

### ② mrbuild 的变量门禁（R33 合规）

- `*FLAGS`（CFLAGS/CPPFLAGS/LDFLAGS 等）**禁止**命令行传（footer 开头即 `error`），
  必须走环境变量。配方用 Conan `Environment` 把 CC/CXX/CC_LINKER/
  CPPFLAGS/LDFLAGS（值全部来自 `tools.build:compiler_executables` conf 与
  suitesparse/openblas 依赖包路径）在 `build()` 内以 `apply()` 运行时注入，
  `build()` 实质仍是纯 `make`。
- **E2BIG 禁区**（libmspub-tools/0.1.4 先例，真机实测 `printenv: Argument list
  too long` ×N + exit 137）：绝不 `save_script("conanbuild")`/`("conanrun")`——
  文件名与 conan 聚合脚本同名，聚合脚本按通配符 source 会自己套自己，环境变量
  指数膨胀。`VirtualBuildEnv`/`VirtualRunEnv` 生成的是带后缀的安全文件名，可保留。
- `VERSION` 反过来**必须**走命令行：Makefile 内 `VERSION := $(VERSION_FROM_PROJECT)`
  会覆盖环境变量；conan export 无 `.git`，不传则退化成 `VERSION_UNKNOWN`，
  产出 `libdogleg.so.2.VERSION_UNKNOWN`。`VERSION=0.18` 得上游惯例
  `libdogleg.so.2.0.18` + `.so.2`/`.so` 软链（`ABI_VERSION=2`）。

### ③ `-llapack` → `-lopenblas`（唯一补丁，portability）

`patches/0001-makefile-lapack-openblas.patch`：OHOS 无系统 `liblapack.so`，
稠密路径的 LAPACK 符号改链本仓 openblas（与 suitesparse/7.8.3 的提供方一致，
避免 netlib lapack + openblas 双 BLAS 混链的符号冲突）。

### ④ 上游测试执行方式（等价直调）

`check.sh` 是 zsh 脚本（`#!/bin/zsh`，`for cmd ($CMDS)`/`${=cmd}` 均为 zsh 专有语法，
OHOS 无此解释器）。配方在 `build()` 中逐条直调其 `CMDS` 数组的 4 条命令，外加
`./test-misc`，共 5 条上游测试命令，任一条非零即构建失败，并输出
`HMBS_UPSTREAM_TEST_RESULT`（discovered=5/executed=5/passed=5）。

### ⑤ 产物与签名

- 不用上游 `make install`（其 `DESTDIR/usr/lib` 硬编码布局、`chrpath -d` 在真机
  不可用、man 页要 `pod2man`）：`package()` 直接拷贝 `libdogleg.so.2.0.18`、
  重建两条版本软链、安装 `dogleg.h` 到 `include/`（conan 扁平布局；上游默认装到
  `usr/include/dogleg/`）。
- 与 suitesparse/7.8.3 同法：`llvm-objcopy` 去 `.codesign` + `binary-sign-tool`
  自签（XPM dlopen 要求）。
- 纯库，无可执行产物，不需 `commands.json`（R38）。

## 验证

- test_package 用公共 dense API（`dogleg_getDefaultParameters` +
  `dogleg_optimize_dense2`）做 6 参数拟合，7 条断言（1 收敛 + 6 参数恢复），
  失败即 exit 1；输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=7）。
- test_package 另随轮重发 `HMBS_UPSTREAM_TEST_RESULT`（conan 缓存命中时主
  `build()` 跳过，标记不丢失；ext4fuse 先例）。

## 状态

built（待真机 `conan create` 全部门禁通过后由 HMBS 提交；本轮仅工作树，不 commit）。
首轮 manifest `status: built` 为目标值，若真机失败按实测修正。

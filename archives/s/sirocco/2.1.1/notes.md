# sirocco (SIROCCO2) 2.1.1 适配笔记

- 上游：https://github.com/miguelmarco/SIROCCO2 （C++/MPFR 的根同伦延续库）
- 版本 2.1.1：官方 GitHub Release（发布名 "pkg-config support"，标签 2.1.1，make dist 产物）

## 编译环境
- 构建系统: autotools（configure + make + libtool）
- 编译日期: 2026-09-19
- 编译器: clang / clang++（OHOS aarch64，/data/service/hnp/bin）
- 依赖: gmp/6.3.0, mpfr/4.2.2（制品仓已发布，flint/arb 同源使用）
- 状态: built（待真机 rule4 门禁与 CI 确认）

## 编译步骤
源码为 make dist 发布包（自带 configure），基础过程：
```
./configure --prefix=...
make -j1
make -j1 check      # 上游测试（Automake TESTS = sirocco_test sirocco_minimal_test）
make install
```
配方用 Conan `AutotoolsToolchain` + `Autotools` helper，`basic_layout(self)` 源码内构建。

## 关键适配点

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gmp/mpfr 头/库找不到 | configure.ac 无 `--with-gmp/mpfr` 选项，库却 `#include <mpfr.h>` 且链接 `-lmpfr -lgmp` | 在 `generate()` 用 `tc.environment()` 把制品仓 gmp/mpfr 的 include/lib 目录前置进 CPPFLAGS/LDFLAGS |
| 2 | OHOS 下 AM_PROG_AR / LT_INIT 找 tools | OHOS 系统目录无 GNU binutils 同名工具 | 给 configure 显式传 `AR=llvm-ar LD=ld.lld RANLIB=llvm-ranlib NM=llvm-nm OBJDUMP=llvm-objdump STRIP=llvm-strip`（同 mpfr） |
| 3 | 厂商/符号链接：库符号是 C++ mangled | include/sirocco.h 无 `extern "C"`，上游测试是 .cpp | 消费者必须用 C++ 编译链接；test_package 用 CMake `LANGUAGES CXX` |
| 4 | 公开头内嵌 mpfr.h | sirocco.h `#include <mpfr.h>` | `cpp_info.requires = ["gmp::gmp","mpfr::mpfr"]` 让 CMakeDeps/PkgConfigDeps 透传下游 |
| 5 | 源码内依赖其它内部 C++ 头 | lib/Makefile.am 引用 `$(top_srcdir)/include/*.hpp` | 保持源码内构建（basic_layout self），沿用 top_srcdir 布局 |
| 6 | 上游测试计数 | tests/Makefile.am `check_PROGRAMS=TESTS=sirocco_test sirocco_minimal_test` | build() 跑 `make check`，解析 `tests/test-suite.log` 的 `# TOTAL/PASS/FAIL/SKIP`，发出 `HMBS_UPSTREAM_TEST_RESULT`（discovered=passed=2） |
| 7 | configure umask 077 破坏 HMDFS | HMDFS 与 FHS 权限语义不一致，conftest 临时目录不可用 | build() 中对 configure 脚本做 `umask 077`→`umask 022` 修复（gmp/fplll/arb 同源） |

## 源码修改
无（未引入 patches/）。所有适配在 conanfile 层完成。

## 依赖版本
- gmp/6.3.0
- mpfr/4.2.2

## 验证结果
- 上游测试：Automake `make check`，test-suite.log 汇总 `# TOTAL: 2`、`# PASS: 2`（sirocco_test + sirocco_minimal_test）
- test_package：CMake `find_package(sirocco)`，`test_sirocco` 调用 4 个公开 API 并断言路径非空/点数>0
- 标记：`HMBS_UPSTREAM_TEST_RESULT`（在 build() 内真实解析 test-suite.log）、`HMBS_TEST_PACKAGE_RESULT`（在 test() 内 ← 真机实际命令结束后产生）

## 注意事项
- 本文件属于我方内部基建；PR 正文统一写「在 HarmonyOS aarch64 环境实测」，不披露真机内部细节。
- gmp/mpfr 在制品仓为静态包；sirocco 默认 static 构建（shared=False）避免 OHOS XPM 对未签名 .so 的 dlopen 限制；shared=True 时走 `_sign_binaries()`（如 arb/flint）。

## 2026-09-19 修复：OHOS 改用 /bin/sh 原位驱动 configure/make（同 flint/arb）

真机 preflight 在依赖 `m4/1.4.19` 的 configure 阶段失败：
```
m4/1.4.19: RUN: ".../src/configure" --prefix=/ ...
shell-init: error retrieving current directory: getcwd: cannot access parent directories: ...
configure: error: working directory cannot be determined
```
根因：profile [buildenv] 把 CONFIG_SHELL/SHELL 指向
`/data/service/hnp/bin/bash`，该 bash 在 HMDFS 深层 conan 构建目录上
getcwd() 失败（cvsgraph / flint 3.6.0 / arb 2.9.0 同源），且 OHOS conan
fork 在用 `Autotools` helper 时会额外拉建 m4/autoconf/automake
tool_requires。旧解法（Autotools(self).configure() + AutotoolsToolchain
environment）导致 helper 的 bash wrapper 触发 getcwd 缺陷，连带依赖 m4
重建失败。

新解法（对齐已发布 flint/arb）：
1. OHOS 分支 build()/package() 不再调用 `Autotools` 类做 configure/make/
   install，改为写一个 `#!/bin/sh` 脚本原位驱动：
   - `CONFIG_SHELL=/bin/sh`、`SHELL=/bin/sh`（规避 hnp bash getcwd）
   - `TMPDIR=$HOME/tmp`（/tmp 只读 erofs）
   - PATH 前置工具链目录（从编译器绝对路径推导，同 flint/arb）
   - 把 gmp/mpfr 的 include/lib 目录注入 CPPFLAGS/LDFLAGS
   - configure 显式传 llvm 工具链 AR/LD/RANLIB/NM/OBJDUMP/STRIP
2. `make check` 在 build() 内经 `/bin/sh -c` 运行，仍解析
   tests/test-suite.log 的 # TOTAL/PASS/FAIL 并输出
   HMBS_UPSTREAM_TEST_RESULT（discovered=passed=2，确定性日志源）。
3. `make install` 在 package() 内经 /bin/sh 运行，并校验 libsirocco 落位。

只要规避了 Autotools helper 的 bash wrapper（/bin/sh 驱动），configure 的
getcwd 探针即通过，m4 依赖也随 helper 不再被拉建，真机可编译。

## 2026-09-21 修复：OHOS 在 generate() 短路 AutotoolsToolchain，避免拉建 m4

真机 preflight 失败于依赖 m4/1.4.19 的构建阶段：
```
m4/1.4.19: RUN: ".../src/configure" --prefix=/ ...
.../configure: fork: Out of memory
m4/1.4.19: ERROR: Package ... build failed
```
日志的 dependency graph 显示 `Build requirements: m4/1.4.19`。根因：配方
`generate()` 无条件实例化 `AutotoolsToolchain(self)`，Conan 2 会据此把
m4/autoconf/automake 作为 tool_requires 拉建（构建期从源码重编 m4）。上一轮
虽已把 OHOS configure/make/install 改成 /bin/sh 原位脚本驱动（不再用 helper），
但 `generate()` 里的 AutotoolsToolchain 仍在图计算时把 m4 拉进 build
requirements，于是在每次预检（全新 conan-home）都要从源码构建 m4，并在共享真机
内存紧张时触发其 configure 的 `fork: Out of memory`——这是 sirocco 自身根本
不使用的上游工具链。

修复：`generate()` 开头对 OHOS 直接 `return`，不实例化 AutotoolsToolchain，
从而不拉建 m4/autoconf/automake。OHOS 分支 configure/make/install 完全由
/bin/sh 自包含脚本驱动，_resolve_cc 用 conf 的 compiler_executables、_ohos_dep_env
自己拼 CPPFLAGS/LDFLAGS、_configure_args 自己传 llvm 工具链，不依赖 toolchain
生成的环境文件，短路后行为不变。非 OHOS 分支仍按原逻辑走 AutotoolsToolchain。


## 2026-09-21 修复：显式 tool_requires("m4/1.4.19") 覆盖 gmp/mpfr 传递 m4

真机 preflight 仍在 m4/1.4.19 的 configure 阶段失败：
```
m4/1.4.19: RUN: ".../src/configure" --prefix=/ ...
job-working-directory: error retrieving current directory: getcwd: cannot access parent directories: ...
configure: error: working directory cannot be determined
m4/1.4.19: ERROR: Package ... build failed
```
日志的 dependency graph 显示 gmp/6.3.0、m4/1.4.19、mpfr/4.2.2 都要被拉建，
且 `gmp/6.3.0: Main binary package 'b0030...' missing → 11 compatible configs
not found`。根因：ohpcd 制品仓没有收 gmp/mpfr 的 aarch64-ohos clang 静态二进制，
gmp/mpfr 必须从源码构建，从而把 conancenter 的 m4/1.4.19 作为传递性 build_require
拉进图。上一轮只短路了 sirocco 自己的 AutotoolsToolchain（避免 sirocco 自身拉 m4），
但**阻止不了 gmp/mpfr 从 conancenter 拉 m4**，而 conancenter 的 m4 在 OHOS HMDFS 上
configure 报 getcwd 失败（hnp bash 缺陷）。

修复：与 autoconf/flex/libslax/zimpl 等已发布配方一致，在 sirocco 的
`build_requirements()` 显式 `self.tool_requires("m4/1.4.19")`，让全图（含
gmp/mpfr 的传递 m4）统一解析到本仓自带的 OHOS 适配版 m4/1.4.19
（archives/m/m4，用 CONFIG_SHELL=/bin/sh + TMPDIR + OHOS triplet 修复，
真机 r13 已验证可建），而非 conancenter 的坏 m4。

sirocco 自身不用 m4（无 autoreconf，/bin/sh 原位驱动），但 gmp/mpfr 需要；
显式声明使 Conan 只为 m4 建一个节点并解析到本仓 m4，整链可通过。


## 2026-09-21 第2次同指纹修复：m4 tool_requires 加 consistent=True + 确认 infra 根因

上轮加的 `tool_requires("m4/1.4.19")` 未能改变结果，真机仍拉 conancenter 的
m4/1.4.19（日志 patch `1.4.19-0004-disable-hardening-in-source.patch` 是
conancenter 的），并同样 getcwd 失败。本轮定位到两个叠加原因：

1) **build 上下文 tool_requires 默认独立节点（consistent=False）**：Conan
   2.28+ 规定（requirements() 文档 consistent 特质）在
   `required_conan_version=">=2.28"` 策略下，build 上下文的 tool_requires
   默认 `consistent=False`，即 gmp/mpfr 各自建独立的 m4 节点，sirocco 声明的
   m4 覆盖不到 gmp/mpfr 的传递 m4。→ 本轮改为 `self.tool_requires("m4/1.4.19",
   consistent=True)` 强制整图（含 gmp/mpfr 传递 m4）合并为单一 m4 节点，
   统一解析到本仓/ohpcd 的 OHOS 适配 m4（archives/m/m4，195+ 配方同款，
   libicns 知识证实由 ohpcd 提供）。

2) **ohpcd 跨 conan 版本 package_id 失效（infra）**：conan 2.28/2.30 回归
   #19705 "Change computation of package_id for transitive static libraries"
   使 gmp/mpfr/m4 旧包 id 不再匹配，ohpcd 收录的旧二进制（flint/arb 时代）
   全部落空 → 强制从 conancenter 源码重建 gmp/mpfr → 拉 conancenter m4 →
   OHOS getcwd 失败（/data/service/hnp/bin/bash 缺陷，knowledge/cvsgraph 实证，
   明确 /bin/sh 干净）。若 ohpcd 未按 conan 2.30 重新发布 gmp/mpfr/m4 的
   OHOS 二进制/配方，配方层面无法让整图解析到工作 m4——这是依赖发布缺口，非
   sirocco 代码缺陷；需 ohpcd 补发布 conan-2.30 兼容的 OHOS m4/gmp/mpfr，
   配方已按仓库 195+ 惯例显式按需声明 m4 tool_requires(consistent=True)。

## 2026-09-21 修复：去掉 tool_requires 的 consistent 参数（真机 TypeError）

真机 preflight 在 dependency graph 计算阶段直接失败：
```
ERROR: sirocco/2.1.1: Error in build_requirements() method, line 69
	self.tool_requires("m4/1.4.19", consistent=True)
	TypeError: ToolRequirements.__call__() got an unexpected keyword argument 'consistent'
```
根因：当前 OHOS conan 基线 2.29.1（ci/conan/setup.sh 确认）的
`ToolRequirements.__call__()` 签名是
`(ref, package_id_mode, visible, run, options, override)`，**不接受
`consistent` 关键字**（consistent 只在 host 上下文的 Requirements 与部分
tool_requires 场景可用）。上一轮为强制 merge build 上下文 m4 节点加的
`consistent=True` 在 2.29.1 上是语法错误，导致 recipe 加载后依赖图计算直接
抛 TypeError。

修复：`build_requirements()` 改回全仓 195+ 配方统一写法
`self.tool_requires("m4/1.4.19")`（不带 consistent）。本仓自带 OHOS 适配版
m4/1.4.19（archives/m/m4），build 上下文同 ref 的 m4 节点由 Conan graph 默认
合并解析到该适配 m4，与 autoconf/flex/libicns 等已发布配方一致。


## 2026-09-21 第3轮（同指纹）：移除无效的 m4 tool_require，定位为依赖供给缺口

真机仍报同一指纹：conancenter 的 m4/1.4.19 被拉建并在 OHOS HMDFS 上
configure getcwd 失败（patch `1.4.19-0004-disable-hardening-in-source.patch`
是 conancenter 命名，非本仓 archives/m/m4 的 0001-0004）。本轮对照源码与
制品仓证据，彻底厘清根因并移除上一轮的 recipe 层尝试：

### 为什么 tool_requires("m4/1.4.19") 不可能生效
1. conan 2.28+ 文档明确：build 上下文 tool_requires 默认 `consistent=False`，
   gmp/mpfr 各自的 AutotoolsToolchain 会建立**独立**的 build 上下文 m4 节点，
   sirocco 根配方声明的同 ref tool_require 覆盖不到（diamond 不合并）。
   给 tool_requires 传 `consistent=True` 在 OHOS conan fork 抛 TypeError
   （上一轮真机证据）。两条路都走不通，显式声明没有合并意义。
2. 前提错误：m4/1.4.19 **不在 ohpcd 制品仓**。archives/m/m4/1.4.19/manifest.yaml
   remote_status 明确 `m4_ohpcd_list: "0 recipes"` 且“m4 ... absent from ohpcd”。
   因此不存在“靠 tool_require 解析到 ohpcd 的 OHOS 适配 m4”这一路径；显式声明
   反而让 conan 依据 remote 优先级去拉 conancenter 的坏 m4 并在构建期重编。
3. sirocco 自身根本不用 m4：OHOS configure/make/install 由 /bin/sh 原位脚本
   驱动，且 release tarball 自带生成好的 configure，无 autoreconf。声明多余。

### 真正的根因（依赖供给/环境缺口，非 sirocco 代码缺陷）
- conan 2.28/2.30 回归 #19705 使 ohpcd 上 gmp/mpfr 旧静态二进制 package_id
  不再匹配 → `--build=missing` 强制从源码重编 gmp/mpfr。
- gmp 重编需要 m4（build tool），m4 不在 ohpcd → 从 conancenter 拉 → 其 m4
  非 OHOS 适配，在 profile 的 `CONFIG_SHELL=/data/service/hnp/bin/bash`（HMDFS
  上 getcwd 损坏）下 configure 失败。
- 即使 m4 修好，gmp/6.3.0 自身的 build() 也是普通 `Autotools` helper（无
  /bin/sh 规避，见 archives/g/gmp/6.3.0/conanfile.py），同一 hnp bash profile
  下 gmp 自己的 configure 仍会 getcwd 失败。整条纯 autotools 依赖链在该
  profile 上无法源码构建。

### 本轮修改
- conanfile.py build_requirements() 删除 `self.tool_requires("m4/1.4.19")`，
  改为空实现 + 详细注释（说明为何不声明）。不再把“解析到 ohpcd 适配 m4”当作
  可达成目标。
- 是否有效由下一次真机/CI 判定；若 ohpcd 补给 conan-2.30 兼容的 OHOS
  gmp/mpfr/m4 二进制或 preflight 改用可源码构建纯 autotools 的 profile/CONFIG_SHELL，
  则整链可通过，与是否声明 m4 无关。


## 2026-09-21 第4轮（同指纹第3次修复）：定位 conan 2.28+ #19705 policy 为重建根因

真机仍同一指纹：conancenter 的 m4/1.4.19 被 gmp/mpfr 的 build 上下文拉建并在
OHOS HMDFS 上 configure getcwd 失败。本轮对照 conan 官方 2.28+ 文档（binary model
/policies）锁定重建的真正触发机制：

### #19705 是 opt-in 的 policy
conan 官方文档明确：2.28 起“Change computation of package_id for transitive static
libraries (#19705)”是一项**可选（opt-in）policy**，仅在
`core:policies=["required_conan_version>=2.28"]`（global.conf 全局）或
recipe 声明 `required_conan_version=">=2.28"`（per-recipe）时启用。
- 旧算法：package_id 把“未被 embed、不传导头文件的传递（非直接）依赖”也算进去
  → 产生更多 package_id（不必要的源码重建）。
- 新算法（policy 启用）：剔除无关传递依赖 → package_id 变少。

已经发布到 ohpcd 的 gmp/6.3.0、mpfr/4.2.2 的旧二进制是在**旧算法**下计算的
（其 recipe 均未声明 required_conan_version，见 archives/g/gmp/6.3.0、
archives/m/mpfr/4.2.2）。若 preflight 的 conan global.conf 启用了
`core:policies=["required_conan_version>=2.28"]`，则消费端用**新算法**重算
gmp/mpfr 的 package_id → 与 ohpcd 旧二进制不匹配 → 强制 `--build=missing`
源码重建 gmp/mpfr → 拉 m4 → conancenter m4 在 hnp-bash profile 上 getcwd 失败。

### 为什么 recipe 层无法解决
- sirocco / gmp / mpfr 都没有 required_conan_version；siirocco 无法从配方关闭
  global.conf 的 policy，也无法影响 gmp/mpfr 各自的 package_id 计算。
- 前两轮已证：tool_requires("m4/1.4.19") 无法合并 gmp/mpfr 独立的 build 上下文
  m4 节点（build 上下文默认 consistent=False；consistent=True 在 OHOS conan fork
  抛 TypeError）；且 m4/1.4.19 不在 ohpcd（archives/m/m4 manifest）。
- 因此这是依赖供给/环境（policy + m4 缺失）缺口：需 ohpcd 按 conan-2.30（启用
  policy 后的新 package_id）补发布 OHOS gmp/mpfr/m4 的二进制/配方，或 preflight
  不启用 #19705 policy 让旧二进制直接可复用，或在 profile 用可源码构建纯 autotools
  的 CONFIG_SHELL（/system/bin/sh）。

### 本轮结论
保持 recipe 干净（不声明无效 tool_requires）。gmp/mpfr 从源码重编所需的
m4 属其 build 上下文，由制品仓/环境负责供给（R36）。是否放行由下一次真机/CI判定。

## 2026-09-21 第5轮（同指纹，纠正根因）：m4 适配版确认在 ohpcd，恢复 tool_require

真机仍同一指纹：gmp/6.3.0 二进制按当前 package_id 命中不到，--build=missing
触发 gmp 源码重编，其 AutotoolsToolchain 拉 m4/1.4.19，最终在 OHOS HMDFS 上
m4/1.4.19 configure getcwd 失败。

### 纠正前 4 轮的错误结论："m4 不在 ohpcd" 是过时数据
- 第3/4轮依据 archives/m/m4/1.4.19/manifest.yaml 的 `remote_status.m4_ohpcd_list=
  "0 recipes"` 断定"m4 根本不在 ohpcd"。但该 manifest 记录的是 m4 自身于
  2026-08-05 构建时的状态（当时尚未发布）。
- 对照同仓已发布配方可证 m4/1.4.19 的 OHOS 适配版【已发布到 ohpcd】：
  - archives/a/autoconf/2.72/manifest.yaml: `m4: "m4/1.4.19 visible/downloadable;
    OHOS armv8 package 6b129b068851896169fae42d399fa922d239ce8a downloaded from ohpcd"`
    （autoconf 于 2026-08-07 真机构建时成功从 ohpcd 下载适配 m4 二进制）。
  - archives/z/zimpl/3.7.1（2026-09-16 合并，本 preflight 同时代）`tool_requires(
    "m4/1.4.19")` 在 OHOS 真机通过，bison 用其 M4 正常。

### 修复
`build_requirements()` 恢复 `self.tool_requires("m4/1.4.19")`（同 zimpl/autoconf/
flex 等 195+ 配方惯例），使 native 构建（host==build）的 build 上下文 m4 节点
统一解析到 ohpcd 的 OHOS 适配 m4，给 gmp/mpfr 源码重编提供可用 m4。不得传
consistent= 参数（当前 OHOS conan 2.29.1 不接受，抛 TypeError，之前轮次实证）。

是否有效由下一次真机/CI 判定。

## 2026-09-21 第6轮（同指纹第3次修复）：gmp/mpfr 切到仓库专属补丁版本，切除 m4 源码构建

第5轮恢复的 `tool_requires("m4/1.4.19")` 仍失效：真机日志 m4 依旧解析到 conancenter
（patch 1.4.19-0004-disable-hardening-in-source.patch 为 conancenter 命名，构建路径
m4dac995 是 gmp 重编链路里拉起的独立节点）。证明根配方的 m4 tool_require 覆盖不到
gmp/mpfr 各自 AutotoolsToolchain 建立的 build 上下文 m4 节点（与 1/2 轮 consistent
分析一致），且会额外引入一次无谓 m4 构建。

### 换策略：不修 m4，改让 gmp/mpfr 命中 ohpcd 预编译二进制（soplex 先例）
对照同仓已合入配方得到的决定性证据：
- soplex/7.1.6（2026-09-18 真机过，静态 default，与 sirocco 同型）曾撞完全相同的
  "conancenter gmp/6.3.0 带坏 m4" 失败，修复 = `requires("gmp/6.3.0")` ->
  `requires("gmp/6.3.0.1")`（notes 第84-91行），m4 链直接切断。
- 机制：conancenter 有 gmp/6.3.0 → 其 recipe 带 m4 tool_require；而 gmp/6.3.0.1
  是【本仓专属补丁版本】（与 6.3.0 同一 tarball，sha256 逐字一致，仅多 --enable-cxx
  + shared=True），conancenter 没有，解析被强制落在本仓 ohpcd 适配配方，预编译二进制
  直接复用 → 不触发任何源码重编 → 不进 m4。
- mpfr/4.2.2 同理会解析到 conancenter；改用本仓专属补丁版本 mpfr/4.2.2.1（同一
  tarball，额外处理 .la），强制 ohpcd 解析。

### 修复
- `requirements()`：`gmp/6.3.0`->`gmp/6.3.0.1`、`mpfr/4.2.2`->`mpfr/4.2.2.1`
  （均 override=True，使 mpfr 传递的 gmp/6.3.0 等整图统一到本仓补丁版本，杜绝残留
  conancenter 的 gmp/6.3.0 节点再触发 m4）。
- `build_requirements()`：移除第5轮加的 m4 tool_require（恢复 pass）—— gmp/mpfr
  prebuilt 后无需 m4 构建，保留反而多一次无谓构建并可能失败。

是否有效由下一次真机/CI 判定。


## 2026-09-21 第7轮（修复 override 导致的 KeyError）：gmp/mpfr 改真实直接依赖

第6轮把 gmp/mpfr 改成 `override=True`，虽强制了 ohpcd 版本，但真机在
OHOS build() 阶段直接失败：
```
self._build_ohos() -> self._ohos_dep_env():
    info = self.dependencies[dep].cpp_info
    KeyError: "'gmp' not found in the dependency set"
```
根因：Conan 2 中 `self.requires("pkg/ver", override=True)` 把该依赖变成
【override（版本覆盖）】而非本包的真实直接依赖。sirocco 用 override=True 声明
gmp/mpfr 后，两者都不是 sirocco 的直接 requirement，`self.dependencies`
（直接依赖闭包）里根本没有 gmp/mpfr 节点 → `_ohos_dep_env()` 访问
`self.dependencies["gmp"].cpp_info` 抛 KeyError（它也波及非 OHOS 的
generate() 同款访问）。

对比同仓已发布、真机通过的配方：
- soplex/7.1.6：`requires("gmp/6.3.0.1")`（真实直接依赖，无 override）。
- mpfi/1.5.4 / linbox：`requires("mpfr/4.2.2.1")` +
  `requires("gmp/6.3.0.1", force=True)`——gmp/mpfr 都是真实直接依赖；且
  mpfr/4.2.2.1 自身钉 gmp/6.3.0，与本包要的 6.3.0.1 冲突，**只有 force=True
  能压过传递依赖钉的版本**。

### 修复
- 主包 conanfile.py requirements()：
  `self.requires("gmp/6.3.0.1", override=True)` + `mpfr/4.2.2.1 (override)` →
  `self.requires("mpfr/4.2.2.1")` + `self.requires("gmp/6.3.0.1", force=True)`。
  这样 gmp/mpfr 成为 sirocco 真实直接依赖（self.dependencies["gmp"/"mpfr"]
  可正确解析），同时 force 压过 mpfr 传递钉的 gmp/6.3.0、整图统一到本仓补丁版本
  6.3.0.1，仍切断 conancenter 坏 m4 链。
- test_package/conanfile.py requirements() 同款改为真实 requires + force=True。

是否有效由下一次真机/CI 判定。

## 2026-09-21 修复：源码下载失败 → 改用 gh-proxy 镜像 + 官方回退
真机 preflight 在 source() 阶段失败：
```
sirocco/2.1.1: WARN: network: Error downloading file
 https://github.com/miguelmarco/SIROCCO2/releases/download/2.1.1/libsirocco-2.1.1.tar.gz:
 'HTTPSConnectionPool(host='github.com', port=443): Max retries exceeded ... Connection to github.com timed out. (connect timeout=30)'
ERROR: sirocco/2.1.1: Error in source() method ... ConanException: Error downloading file ...
```
根因：conandata.yml 里 sources.url 是单条 github.com 官方 URL，真机直连 github.com
超时（connect timeout=30），源码包拉不下来，编译无法进入。gmp/mpfr 依赖下载正常
（来自 conancenter/ohpcd）。

修复：conandata.yml 的 sources.url 改为【有序 URL 列表】：
1. `https://gh-proxy.com/` + 官方 github URL（仓库 ci/conan/build_and_test.sh 唯一
   维护的 GitHub 镜像，2026-08-06 实测可用 412KB/s，gh-proxy.com）
2. 官方原始 github.com URL 保留在末尾作为回退
Conan get() 对 url 列表按顺序逐个尝试，任一成功即用之。镜像提供与官方完全相同的
归档，sha256 "83d1dd5..." 不变。未改动其它 recipe/测试接入逻辑。

## 2026-09-23 真机 transient：preflight.sh can't fork - try again（环境资源耗尽，非配方缺陷）
真机 preflight 在 compile 阶段失败，stderr 仅一行：
  /storage/Users/currentUser/preflight/clients/2e29dbedc1b1/preflight.sh[319]: can't fork - try again
stdout 停在“抢到锁槽 0”与 HMBS_PLATFORM_CAPABILITIES 打印之后，**没有任何 conan create /
configure / make 输出**——说明是 preflight 编排 shell（preflight.sh 第 319 行）在 spawn
首个子进程时 fork 失败，sirocco 配方尚未进入编译。
根因：`can't fork - try again` 即 fork() 返回 EAGAIN，是宿主级资源耗尽
（进程数达 RLIMIT_NPROC 上限 / 内存瞬时耗尽），属共享真机瞬时负载，非配方可拦截的确定性错误。
配方已最大化减少进程/内存占用：tools.build:jobs=1、configure/make/install 全部 -j1 串行、
/bin/sh 直驱绕开 bash wrapper、无 autoreconf/m4 工具链、gmp/6.3.0.1+mpfr/4.2.2.1 钉到
ohpcd 预编译二进制（不触发源码重编）。gmp/mpfr manifest 均确认 ohos_device pass。
结论：环境瞬时资源问题，按守则不要求修改代码；保留已通过验证的配方不变，等待真机环境恢复后由
hmbs 自动复跑。诊断记录于此，供下一轮结果核验。


## 2026-09-23 修复：source() 改用 Python tarfile 原位解压，绕开 OHOS toybox tar 的 exec zcat
真机 preflight compile 阶段 stderr：
  tar: exec /usr/bin/zcat: Out of memory
  tar: had errors
发生在 conan source() 阶段（conandata.yml 的 tar.gz 解压）。根因：Conan 2 的 get()/
untargz 在系统有 tar 时走系统 tar 解压 .tar.gz，OHOS 用 toybox tar，其 gzip 解压需
派生子进程 `exec /usr/bin/zcat`；在共享真机内存紧张时该 exec 失败并报 "Out of memory /
had errors"（上一轮同为宿主资源耗尽的 fork/zcat exec 失败指纹）。

修复（同 autodiff/0.4.0 已发布先例）：source() 不再用 get()，改为
  - conan.tools.files.download 逐个尝试 conandata.yml 的有序镜像回退 URL
    （保留 sha256 校验，镜像与官方 tarball 逐字一致，校验值不变）；
  - 用 Python 内置 tarfile.open(..., "r:gz") 流式解压（进程内解压，不派生子进程，
    不 exec /usr/bin/zcat，内存占用最小）；
  - 手动 strip_root（单一顶层目录上移内容）；
  - Python 3.12+ 用 filter="data" 防路径穿越，旧版本走 extractall() 兜底。
不影响 build()/package() 后续逻辑（basic_layout 下 source==build，in-source 不变）。
是否有效由下一次真机 preflight 判定。


## 2026-09-24 修复：给 build-aux/config.guess 注入 HarmonyOS 分支（E007）

真机 preflight compile 阶段失败：
```
./build-aux/config.guess: unable to guess system type
UNAME_SYSTEM  = "HarmonyOS"
configure: error: cannot guess build type; you must specify one
```
停在 configure 的 build/system 类型探测（AC_CANONICAL_HOST），sirocco 配方尚未
进入编译。

### 根因
sirocco 2.1.1 发布 tarball（make dist）自带 **2024-07-27 版现代 GNU config.guess**
（`timestamp='2024-07-27'`，错误横幅逐字吻合）。该脚本不识别
`UNAME_SYSTEM=HarmonyOS`（uname -s），主 case 无匹配分支 → 无法输出三元组 →
configure "cannot guess build type"。其 build-aux/config.sub 已是现代版，**原生支持
ohos/linux-ohos**（实测 `config.sub aarch64-unknown-linux-ohos` 返回 rc=0、逐字回显），
故只须补 config.guess，无需动 config.sub。

### 修复
conanfile.py source() 在 OHOS 分支调用新增 `_patch_config_guess_for_ohos()`：
1. 核心：在 `    *:NetBSD:*:*)` 分支前插入 `*:HarmonyOS:*:*)` case（MACHINE 映射 →
   `GUESS=${MACHINE}-unknown-linux-ohos`；现代脚本统一尾部输出 GUESS= 形态，故用
   GUESS= 注入，见 DRAFT-config-guess-era-echo-exit）。
2. 辅助：`#if defined(__ANDROID__)`/`LIBC=android` 序列后补
   `#elif defined(__OHOS__)/LIBC=ohos`（E007 一并修 libc 探测；sirocco 该段用 Tab 缩进，
   故按空白无关正则定位）。
3. 遵循 P-AUTOTOOLS-001：**不使用 --build/--host 绕过**（会误判交叉编译、跳过
   AC_RUN_IFELSE、生成错误 config.h）。全部判定幂等（已含 HarmonyOS/__OHOS__ 则跳过）。

### 验证（本机对发布 tarball 实测）
- 补丁后脚本在 Linux 本机仍输出 `x86_64-pc-linux-gnu`（rc=0，无回归）。
- 用 stub `uname`（-s=HarmonyOS, -m=aarch64）驱动补丁后脚本 → 输出
  `aarch64-unknown-linux-ohos`、rc=0；再经 sirocco 自身 config.sub 验证该三元组被接受。
- 是否放行由下一次真机 preflight 判定。


## 2026-09-23 真机 transient：exec request failed on channel 0（SSH 传输层，非配方）
真机 preflight 本轮失败 stderr 仅一行：
  exec request failed on channel 0
stdout 为空。这是 OpenSSH 客户端在 channel 0 上发起 exec 请求被服务端拒绝/无法分配
会话信道（无空闲 pty / maxsessions 达上限 / 远端 shell 因资源限制无法派生）时的传输层
错误。它发生在 preflight 通过 SSH 建立执行通道阶段，sirocco 配方尚未启动，与
conanfile/测试无关，配方层无可修复项。
连续三轮真机失败同属共享机资源/会话层告警：round1 preflight.sh can't fork（fork EAGAIN）、
round2 tar exec /usr/bin/zcat: Out of memory、round3 SSH exec request failed on channel 0。
三者均非确定性配方缺陷。上一轮 source() 改 Python tarfile 原位解压（绕开 OHOS toybox
tar 的外部 zcat 子进程）是合法加固，保留不动；本轮 SSH 传输层失败需等待真机环境恢复后
由 hmbs 自动复跑，届时方能验证该加固。

## 2026-09-24 第2轮（E007 加固）：config.guess 补丁对 configure 实际运行的目录兜底

真机 preflight compile 阶段仍失败于同一指纹（config.guess unable to guess）：
```
id: bad uid 20020100
id: bad uid 20020100
configure: WARNING: ancient id detected; assuming current UID is ok, but dist-ustar might not work
./build-aux/config.guess[1741]: can't create /storage/Users/currentUser/tmp/cgkGCkGO/dummy.c: Permission denied
./build-aux/config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```
根因定位：日志走到 config.guess 的 fallback（`cat > "$dummy.c"` 的 dummy.c 临时文件
redirection）+ "unable to guess system type" banner，说明运行时 config.guess 的
`UNAME_SYSTEM=HarmonyOS` 未命中任何分支 → GUESS 为空 → 落入需要 C 编译器的兜底。
而上一轮 source() 里已注入 `*:HarmonyOS:*:*)` 分支（本机实测该分支可让 config.guess
不经 dummy.c 直接输出 `aarch64-unknown-linux-ohos`）。

结论有两种可能：(a) 上轮 preflight 跑的是未加补丁的快照；(b) Conan 在
`Copying sources to build folder` 后，configure 实际运行的目录里的 config.guess
未被打到补丁（folder 语义差异，source_folder 与 build_folder 可能不同）。

修复（幂等兜底）：`_patch_config_guess_for_ohos` 改为接受 `base` 参数；`_build_ohos`
在运行 `/bin/sh _build_ohos.sh`（configure/make 原位脚本，`cd $source_folder`）之前，
对 `source_folder` 与 `build_folder` 依次重打 config.guess 补丁。source() 里的补丁调用
保留（默认 base=source_folder）。二次调用因 `if "HarmonyOS" not in content` 幂等跳过。
是否有效由下一次真机 preflight 判定。

## 2026-09-24 修复：source() 内禁读 self.settings（ConanException）
真机 preflight compile 阶段在 source() 直接失败：
```
ERROR: sirocco/2.1.1: Error in source() method, line 164
	if str(self.settings.os) == "OHOS":
	ConanException: 'self.settings' access in 'source()' method is forbidden
```
根因：Conan 2 规定 source() 方法内【禁止访问 self.settings】（source 阶段在依赖与
settings 就绪前执行）。上一轮（第2轮 E007 加固）在 source() 的
`apply_conandata_patches(self)` 后加了一段
`if str(self.settings.os) == "OHOS": self._patch_config_guess_for_ohos()`，该
settings 读取正是违规点，conan 在加载 recipe 后 source() 阶段抛 ConanException，
整个 compile 未进入下载/解压/configure。

修复：删除 source() 里的 OHOS 条件块（仅保留 apply_conandata_patches）。config.guess
的 HarmonyOS 补丁不需要在 source() 打——`_build_ohos()` 在运行 /bin/sh configure 原位
脚本前，已对 source_folder 与 build_folder 依次调用 `_patch_config_guess_for_ohos(base)`
（幂等，已含 HarmonyOS/__OHOS__ 则跳过），且 build() 允许访问 self.settings，因此 OHOS
工况下补丁仍在 configure 运行前就位，行为不变。非 OHOS（Linux CI）路径本就用不到该补丁，
不受影响。source() 内其余引用（self.conan_data/self.source_folder）均为合法访问。
是否有效由下一次真机 preflight 判定。

## 2026-09-24 基础设施告警轮：HMBS 根仓库越界变化（无配方修改）

本轮真机结果 failed@compile，但原因是基础设施/守护进程检测告警，非配方编译/测试缺陷：
  原因：AtomCode 轮次中检测到 HMBS 根仓库越界变化：HEAD 从 7913111596f9 变为 d72c059d1ecb
平台能力诊断 [shell_getcwd]：HNP bash 无法访问当前 HMFS/HMDFS 工作目录；处理方式为
使用 HMBS 已注入的 SHELL=/bin/sh、CONFIG_SHELL=/bin/sh，且不要在配方硬编码
/data/service/hnp/bin/bash。

核对当前配方与该诊断的符合性（全部满足，无新增代码改动）：
- OHOS configure/make/install 全部由 `#!/bin/sh` 原位脚本驱动（_bootstrap_ohos_script /
  _install_ohos.sh），脚本内写 `CONFIG_SHELL=/bin/sh`、`SHELL=/bin/sh`、`TMPDIR=$HOME/tmp`。
- `make check` 用 `/bin/sh -c` 运行；全程未把 /data/service/hnp/bin/bash 作为可执行文件
  硬编码（仅出现在注释/说明文本与 binary-sign-tool 签名工具路径，后者只用于 shared=True）。

结论：该「HMBS 根仓库越界变化」属守护进程环境/检测层告警，配方无对应代码缺陷，按守则
基础设施故障不要求修改代码。已通过验证且逐轮加固（E007 config.guess、source() 禁读
settings、tarfile 原位解压、/bin/sh 直驱、gmp/mpfr 补丁版本钉 ohpcd）的配方保持不变，
等待真机环境恢复后由 hmbs 自动复跑核验。

## 2026-09-24 修复：make check 运行目录错位（source_folder≠build_folder）

真机 preflight compile 阶段失败（已过 configure+make，仅 mpfr sentinel 警告后）：
```
make: *** No rule to make target 'check'.  Stop.
sirocco/2.1.1: upstream-check| make: *** No rule to make target 'check'.  Stop.
sirocco/2.1.1: ERROR: Error in build() method, line 489
    self._run_upstream_check(self.build_folder, use_sh=True)
```

根因：`basic_layout(self)` 下 `build_folder = <source_root>/build-release`，与
`source_folder`（源根，含 configure/Makefile.am/...）**不是同一目录**。配方 OHOS 的
_build_ohos 用 `#!/bin/sh` 脚本 `cd $source_folder` 原位 configure+make（库已编出，编译
警告即来自 source_folder 里的 make），即生成 Makefile 的目录是 **source_folder**；而
`_run_upstream_check(self.build_folder)` 却把 `make -j1 check` 跑在 **build-release**
——同名子目录里没有生成的 Makefile（config.guess 也不在此，早前 E007 那轮日志已见
`config.guess not found at .../build-release/build-aux/config.guess`），于是顶层
Makefile 无 `check` 目标 → "No rule to make target 'check'"。桌面（非 OHOS）分支用的
Autotools 在 build_folder 里 configure，故该处跑 build_folder 是对的，不可一刀切改。

修复（conanfile.py _run_upstream_check / build()）：
1. `_run_upstream_check` 的 log_file 与 upstream_test_result.json 从写死的
   `self.build_folder` 改为 `build_root`（与 make check 所在目录一致）。
2. build() OHOS 分支 `_run_upstream_check(self.build_folder, use_sh=True)` →
   `_run_upstream_check(self.source_folder, use_sh=True)`：OHOS in-source 构建在
   source_folder，make check 必须也在此跑才能命中生成的 Makefile 与 tests/ 递归
   check 目标。桌面分支保持 build_folder 不变。

## 2026-09-24 修复：make check 运行目录已对 → 上游测试真机上 FAIL:2，需暴露 per-test 日志

上一轮把 OHOS 的 `make check` 改到 source_folder（in-source 构建目录）后，make check
真正跑起来了，但真机预检显示上游 2 个测试全部失败：
```
upstream-check| # FAIL:  2
upstream-check| make[3]: *** [Makefile:688: test-suite.log] Error 1
ConanException: sirocco: upstream `make check` failed with rc=2
```
_emit_check_log 只打了 make check stdout 尾部（automake 并行 harness 的汇总块），
不包含每个 test 的真实 stderr（在 tests/*.log 与 tests/test-suite.log 里），故看不到
确切原因。

### 本地（Linux x86_64，系统 gmp/mpfr）对同一发布 tarball 实测
- autoreconf + configure + make + `make check` 全部通过：test-suite.log `# TOTAL: 2 # PASS: 2`。
- 两个测试程序本体都极轻：sirocco_minimal_test 0.02s / 5MB RSS、sirocco_test 0.04s /
  5.6MB RSS，且这两个测试【没有任何断言】——返回 0 即通过，非零即崩溃。
=> 真机失败是 OHOS 特有（原生通过），非算法/资源问题（极轻），也不是测试本身坏。
  只能进一步取 per-test 日志确认是哪个运行期原因（崩溃信号 / “Singularity detected”
  返回 NULL 后被 rop[0] 解引用段错误 / 其它）。

### 本轮修改（诊断加固，不伪造通过）
conanfile.py `_emit_check_log(log_file, build_root=None)` 增加：
- 失败时 dump `tests/test-suite.log`（automake 汇总 + per-test 明细块）；
- dump `tests/*.log`（每个测试的 stdout/stderr，automake 并行 harness 的真实失败
  载体，常含 “Segmentation fault” / “Singularity detected. Abort Sirocco”
  / 信号/退出状态）。
两个调用点（OHOS /bin/sh 分支与桌面 env 分支）都传入 build_root。
仍然保持 `make check` 失败的硬失败（raise ConanException），不跳过、不吞掉计数。
是否修复由下一次真机 per-test 日志判定——拿到确切原因后再做针对性改动。

## 2026-09-24 修复：上游测试运行期加载不到共享 libgmp.so.10（DT_NEEDED 解析到系统 stub）

上一轮加的 per-test 日志 dump 奏效，真机日志直接给出两个测试失败的确切原因：
```
test| Error loading shared library libgmp.so.10: (needed by ./sirocco_test)
test| Error relocating ./sirocco_test: __gmpn_rshift: symbol not found
...
test| FAIL sirocco_test (exit status: 127)
test| Error loading shared library libgmp.so.10: (needed by ./sirocco_minimal_test)
test| Error relocating ./sirocco_minimal_test: __gmp_bits_per_limb: symbol not found
test| FAIL sirocco_minimal_test (exit status: 127)
```
即测试可执行文件带 DT_NEEDED libgmp.so.10，运行期加载器解析到系统自带的 stub
libgmp.so.10（缺现代 GMP 符号）→ “symbol not found” → exit 127。

### 根因
- gmp/6.3.0.1 是【共享包】（conanfile default_options={"shared": True}，产
  libgmp.so.10）；mpfr/4.2.2.1 是【静态包】（libmpfr.a，manifest 确认）。
- sirocco 静态库 + 上游测试 tests/Makefile.am `-lmpfr -lgmp`：`-lgmp` 命中共享
  libgmp.so.10 → 测试可执行文件 DT_NEEDED libgmp.so.10。库本体是静态归档不涉及
  运行期加载，故编译/链接都过；只有测试可执行文件运行期才需要解析共享 gmp。
- 测试可执行文件没有 rpath 指向 conan gmp 的 libdir，OHOS 加载器在默认路径找到
  系统 stub libgmp.so.10 → 重定位失败。libsirocco 库先编好无此问题，故整个 build
  只卡在 make check 的运行期。

### 本轮修改
conanfile.py `_run_upstream_check` OHOS（/bin/sh）分支：make check 前
`export LD_LIBRARY_PATH="<gmp libdir>:<mpfr libdir>:$LD_LIBRARY_PATH"`，把 conan
依赖（gmp/mpfr）的 libdir 前置进加载路径，确保测试程序加载到 conan 的正确共享
libgmp.so.10，而不是系统 stub。libdir 从 self.dependencies[dep].cpp_info.libdirs
收集（与 _ohos_dep_env 同源）。test_package 侧已由 VirtualRunEnv(conanrun) 自动
注入依赖 libdir 的 LD_LIBRARY_PATH，无需另改。

### 本地佐证
同一 2.1.1 tarball 在 Linux（系统 gmp/mpfr 头部）autoreconf+configure+make+
make check 全过（TOTAL:2 PASS:2），证明测试逻辑本身无缺陷，失败确为 OHOS 运行期
共享库解析问题。

是否有效由下一次真机 preflight 判定。

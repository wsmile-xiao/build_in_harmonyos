# qalc 5.11.0 适配笔记

## 编译环境
- 构建系统: autotools（上游自带 configure，无需 autoreconf）
- 编译日期: 2026-09-27
- 编译器: OHOS SDK clang/clang++（--target=aarch64-linux-ohos）
- 目标: ohos-aarch64（本地验证 profile `ohos-local`，与 CI `ohos-aarch64` 同源）
- 状态: built（本地 conan create/verify 通过，未 upload，R29 不伪造 published）
- 任务背景: 积分赛清单 `qalcC++ 5.11.0`；qalc CLI 与 libqalculate 同源（上游唯一 tarball 即 libqalculate-5.11.0.tar.gz，Debian/Ubuntu 的 qalculate 二进制包同样取自该源码包），故以 qalc 为名独立打包（application，含 bin/qalc + libqalculate.so + share/qalculate）

## 依赖（制品仓均已发布，conan requires 管理）
| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| gmp | 6.3.0 | requires | configure AC_CHECK_LIB 硬错误 |
| mpfr | 4.2.2 | requires | configure AC_CHECK_LIB 硬错误 |
| libxml2 | 2.15.3 | requires | configure PKG_CHECK_MODULES 硬检查 |
| readline | 8.3 | requires | qalc CLI 交互模式增强 |

可选依赖 libcurl/ICU 未发布 → configure 传 `--without-libcurl --without-icu`。

构建工具：5.11.0 的 data XML 用 GNU gettext `msgfmt --xml` 生成（intltool 已被上游移除）；msgfmt 优先取 PATH（macOS host 为 Homebrew），CI worker 缺失时从 cmd-pkgs 装 gettext 0.22.5。

## 适配点（3 个补丁，全部 portability、无平台宏）

### 补丁 0001: config.guess（HarmonyOS 检测）
- `Linux|GNU|GNU/*` → `Linux|GNU|GNU/*|HarmonyOS)`，LIBC 直接 gnu
- 添加 `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-gnu`

### 补丁 0002: configure（umask）
- 移除 `umask 077 && mktemp/mkdir`（HMDFS 兼容；5.8.2-r0 同款）
- 5.8.2 补丁里的 intltool XML::Parser 部分已不需要：5.11.0 上游移除了 intltool

### 补丁 0003: util.cc（pthread 守卫）
- `pthread_setcancelstate/setcanceltype/pthread_cancel` 在 OHOS musl 不可用
- 用 HAVE_PTHREAD_* 宏守卫 + `#include "pthread_compat.h"`
- pthread_compat.h 由配方 feature-detection 生成：
  ⚠️ 探测编译必须加 `-Werror=implicit-function-declaration`（OHOS 头文件无
  pthread_cancel 声明但 C 允许隐式声明，仅警告）

## 关键踩坑（继承自 5.8.2-r0 实战，配方同法规避）

### 1. 不用 AutotoolsDeps/VirtualRunEnv
- AutotoolsDeps 把 conan 依赖 -l 全塞进 LIBS → configure 早期 conftest
  （cross-compiling 检查）也链上依赖 → 运行期找不到 conan 缓存 .so → $?=127
- VirtualRunEnv 的 LD_LIBRARY_PATH 顺序会让 lld 命中 conan libxml2.so.16
  而非 SDK 自带版本（SONAME 相同符号集不同）→ "Error relocating lld"
- 依赖 include/lib flag 经 AutotoolsToolchain 环境手动注入

### 2. LD_LIBRARY_PATH 必须在 build() 内显式注入
- 构建期 C++ 工具依赖 libc++_shared.so；顺序：SDK llvm/lib（lld 用 SDK
  libxml2）→ /system/lib64 → conan 依赖 lib

### 3. 依赖 .la 文件路径修复（E236 同族）
- conan 包 .la 的 libdir='//lib' → libtool 读依赖 .la 失败
- 跨包全局映射：mpfr.la 的 dependency_libs 引用 libgmp.la 解析到 gmp 包

### 4. API 签名差异（5.8.2 vs 5.11.0）
- 5.8.2: `MathStructure calculate(std::string, ...)` 按值返回
- 5.11.0: `int calculate(str, MathStructure*)`（回退旧签名）
- 本包为 CLI 应用包，测试以运行 qalc 为主，不受影响

### 5. 线程取消降级说明（R40）
OHOS musl 无 pthread_cancel 家族，Thread::cancel()/enableAsynchronousCancel()
对应调用被守卫编译掉，线程取消在 OHOS 上静默降级为 no-op；qalc 正常计算
流程不依赖线程取消（仅超时中断辅助路径），核心功能不受影响。

### 6. 显式交叉三元组（ohos-local 双 profile 陷阱）
- conan-verify 把同一份 OHOS profile 同时当 -pr:h 与 -pr:b → conan 判定非交叉，
  AutotoolsToolchain 不生成 --host → configure 试图在本机 macOS 上运行 OHOS
  conftest → "cannot run C compiled programs"（wdiff/zeitgeist 同款坑）
- 修复：configure_args 显式 `--build=aarch64-unknown-linux-gnu` +
  `--host=aarch64-unknown-linux-ohos`；上游 5.11.0 的 config.sub 原生已认
  linux-ohos*，无需再打 config.sub 补丁

### 7. libtool 2.6 + OHOS lld 不打 SONAME（E537 同族）
- 现象：libtool 2.6 在 with_gnu_ld=no（clang/lld 探测结果是 /usr/bin/ld 且
  非 GNU ld）时链接库不传 -Wl,-soname → libqalculate.so.23.3.12 无
  DT_SONAME → qalc 的 DT_NEEDED 被记成相对路径
  `../libqalculate/.libs/libqalculate.so`，不可重定位、运行期找不到库
- 修复：build() 从生成 Makefile 读 QALCULATE_CURRENT/REVISION/AGE（26/12/3），
  按 libtool 规则 major=current-age=23，make 命令行覆盖
  `libqalculate_la_LDFLAGS="-version-info 26:12:3 -no-undefined
  -Wl,-soname,libqalculate.so.23"`——只影响库目标，不污染可执行文件
- ⚠️ make 变量值含冒号（26:12:3），必须整体加引号传给 make，否则
  `make: *** No rule to make target '26:12:3'`
- 实测：修后 qalc 的 DT_NEEDED = libqalculate.so.23 + libxml2.so.16 +
  libc++_shared.so + libc.so（A3 断言通过）

## 上游测试与验证

- 上游测试: qalc --test-file 原生执行器，tests/ 17 个 batch 文件共 688 个
  input→expected 用例（stats.batch 依赖 tests/vectordata*.csv 相对路径，
  需以 tests/ 所在目录为 cwd）；src/Makefile.am TESTS=unittest 为同一入口
- test_package: 两层验证——A1-A4 产物/ABI 检查（任意 host，纯 Python 解析
  ELF）；真实鸿蒙 worker 上全量复跑上游 688 用例 + H1-H3 平台行为
  （H1 定义加载/单位换算、H2 表达式退出码、H3 musl libm 三角函数）
- 计数口径: 独立检查项，688（上游）+ 7（鸿蒙特有）= 695

## 远程 CI 复跑

- 2026-09-27 21:27 手动 `/rebuild` 复跑：构建 **#63068**（worker `OpenHarmonyPCDeveloper-CI-008`）再次全绿——Conan test_package 通过、L0/L1 门禁通过、全步骤 ✅（https://ohpcd.atomgit.com/ci?id=63068），与首发构建 #62925 相互印证。
- PC 鸿蒙化 PR 审查（2026-09-28）除 rule6（AI 检视评论缺失）外全部通过；rule6 根因是 atomgit-bot 对本 PR 的检视生成卡在「进行中」（对照：同期大测试集 PR libgee #13268 同样卡死，小 diff PR plumber #13331 检视正常完成）。已按 SKILL §12A 先后执行 `/ai review` 与 `/ai review force` 重触发。

## 2026-09-28 审查跟进（PC 审查 rule6）

- CI 第三次复跑：新提交 e48e6072（test 数据文件按数据渲染 + 哈希溯源）构建 **#63655**（CI-036）全绿，与 #62925/#63068 三次互证。
- atomgit-bot AI 检视共 6 次触发（自动 + /ai review ×2 + /ai review force ×3，含顶层评论）均停留「进行中」；对照同期小 diff PR 检视正常、大测试集 PR（libgee #13268）同样卡死 → 平台侧生成故障，非本 PR 内容问题。已在审查者「test_package 需复核」讨论串回复完整证据链。
- test_package/tests/ 目录新增 .gitattributes（*.batch/*.csv 标记 -diff，数据文件渲染）并在 MANIFEST.yml 声明 19 个文件逐 sha256 溯源（对应 libqalculate-5.11.0.tar.gz 内同名文件），diff 由 2952 行收口至 1420 行，溯源反而更可审计。

## 产物
- bin/qalc
- lib/libqalculate.so（同源构建，随包交付）
- share/qalculate/*.xml（运行时定义数据）
---

**编译结束**: 2026-09-27 17:26
**最终状态**: built

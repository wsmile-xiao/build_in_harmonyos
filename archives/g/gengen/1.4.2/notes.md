# gengen 1.4.2 适配笔记（GLM-15，2026-09-12）

## 任务信息

- 平台任务号：7318，语言 cpp；worktree `~/qzy/GLM-15-gengen-1.4.2`，分支 `feat/gengen-1.4.2`
- 基线：upstream/main `a675263b91fd9cef49cbce7aafb54062ae10df2c`（worktree 新建即此 HEAD）
- 上游：https://ftp.gnu.org/gnu/gengen/gengen-1.4.2.tar.gz（2010-09-07 发布）
- SHA256：`f49bde616c09156cf7a91f40cb37b476fcd20fe899be15ecd194ca8ed40798e9`
  - 双源核验：ftp.gnu.org 与 mirrors.kernel.org 下载件同值（tarball 497066 字节）
- 构建系统：autotools（2010 年代 automake，发布包自带 configure）
- 包类型：**纯工具型**——安装产物仅 `bin/gengen` + `share/doc/gengen/`（libgengen.a 为 noinst 不安装，无公开头文件）；`package_type="application"` + 软件级 `commands.json`（R38/PF8）
- 依赖：零外部依赖（W0 preflight 通过：无依赖声明需检查）

## W0/W0b

- W0：`ci/scripts/preflight_check.sh gengen/1.4.2` → 预检通过（无依赖需要检查），exit 0。
- W0b：upstream/main 归档树无 gengen（`git ls-tree HEAD:archives/g/` 无匹配），无历史 notes.md 可读。
  参照同作者同构建体系的 gengetopt 2.23 已归档配方（`archives/g/gengetopt/2.23`，已合入 upstream/main）。
- R47 lang-preflight：exit 0，milestone=lang_checked（C++ 与任务声明语言匹配）。

## 构建环境

- 鸿蒙设备（SSH 8.154.43.235），clang 15.0.4（/data/service/hnp/bin），GNU Make 4.4.1
- conan 2.29.1（OHOS 适配版），CONAN_HOME `~/tmp/ch/home-GLM15-gengen`（global.conf `tools.build:jobs=2`）
- profile：ci/conan/profiles/ohos-aarch64（os=OHOS, arch=armv8, clang 15, libc++, cppstd=17）
- 设备无 makeinfo/texinfo/help2man；有 flex/bison（本包用不上：tarball 内生成文件时间戳晚于 .ll/.yy/.ggo）

## 实撞坑与处理（对应配方 build() 内四处受控修改）

1. **2010 版 config.guess/config.sub（E007/E160）**：config.guess 在 HMDFS 上
   `can't create $TMPDIR/dummy.c: Permission denied` 直接失败，且不认识
   `uname -s = HarmonyOS`；config.sub 拒绝 `aarch64-unknown-linux-ohos` 与
   `aarch64-unknown-linux-musl`（"Invalid configuration"），只认 `-gnu` 结尾。
   处理：显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`。
   本机构建目标即本机（aarch64 OHOS），native 语义正确，conftest 可直接运行
   （configure exit 0，零 cache 变量注入）。
2. **configure 内嵌 `umask 077`（E011/E129）**：2 处，HMDFS 上 config.status
   建临时目录会 Permission denied。处理：替换为 022（知识库受控方案）。
3. **2010 年代 C++ vs profile cppstd=17（E293）**：
   - src/scanner.cc（flex 生成）含 15 处 `register`；构建级复现（pristine 源码 +
     同参数 configure + `make CXXFLAGS=-std=c++17`）报
     `scanner.cc:836:2: error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]`（clang-15 硬错误）。
   - src/skelstruct.cc 使用 `std::bind2nd/std::mem_fun`（81-82 行）与
     `std::bind1st/std::mem_fun`（212 行）；首轮 conan create（-std=c++17）报
     `error: no member named 'bind2nd' in namespace 'std'` 等——这些绑定器
     是 C++17 **移除**的库组件，任何 -Wno-error 都救不回。
   - 处理：`configure()` 中 `self.settings.rm_safe("compiler.cppstd")`（仓库
     先例：boost-ext-ut 2.3.1 / c-client 2007f / cunit 2.1.3 / cif-api 0.4.2）
     ——工具链不再注入 -std=c++17，clang 15 默认 gnu++14，该代际特性全部可用。
     设备探索构建正是在默认标准下全量通过（含上游 52 项测试），条件一致。
     E130 提示的"SDK libc++ 头文件需要 C++17+"风险经实证排除：探索构建
     无 -std 标志、走 SDK 默认 libc++ 头文件，编译零错。
   - scanner.cc 的 register 仍顺带 sed 清理（gnu++14 下仅 -Wdeprecated-register
     告警，清掉保零告警）。
4. **doc/ 需要 texinfo**：顶层 `SUBDIRS = lib src doc tests`，doc/ 的
   info_TEXINFOS 需要 makeinfo（设备/CI 均无）。处理：configure 后改写顶层
   Makefile 的 SUBDIRS 行为 `lib src`。不可用命令行 SUBDIRS（递归传播给子
   make）也不可用 `make -C src`（HMDFS 上 libtool getcwd 坑）——gengetopt
   2.23 配方注释中的实撞结论，本包直接沿用。

## 上游测试四维账本（R51，§10.1 口径）

上游测试体系（1.4.2 tarball，静态清点）：

| 层 | 内容 | 数量 | 来源 |
|---|---|---|---|
| tests/ 金标 diff | 生成文件与 `.test` 金标逐字节 diff | 35 | tests/Makefile.am `BUILT_SOURCES`/`GENERATED_TESTS`/check-diff |
| tests/ 金标 diff | 错误用例 stderr 与 `.err` 金标 diff | 8 | tests/Makefile.am `ERRFILES`/check-diff |
| tests/ 金标 diff | verbose 输出 diff | 1 | tests/Makefile.am `VERBOSEOUTPUT` |
| tests/otherdir | `--output-dir` 行为 diff | 4 | tests/otherdir/Makefile.am check-am |
| src/tests | 单元测试程序（automake TESTS） | 4 | src/tests/Makefile.am：test_replace、test_exp_checker、test_exp_generator、test_type_env |

四维数字：

- **N_static = 52**（上表合计 35+8+1+4+4；按 tests/Makefile.am、src/tests/Makefile.am、tests/otherdir/Makefile.am 的真实注册入口逐项清点）
- **N_registered = 52**（全部注册于 `make check`，无条件编译/资源缺失排除项）
- **N_executed = 52，通过 52**（`make check -j1` exit 0；日志 check2.log 共 21497 字节，sha256 `4060f39a049194588a559b35ce6e7df6119d82ee915cce4cd35fc8abc9e07808`：`PASS:` 4 条、`diff` 行 48 条=35+8+1+4、无 FAIL/ERROR）
- **未执行/跳过 = 0**（`check-valgrind`/`check-gengen-valgrind` 不在默认 check 注册链内，不计入 N_static）
- **N_consumer = 1**（test_package/test.py，7 项断言，见下）

### 上游测试修改说明（4 条，全部是构建规则、测试用例零修改）

首轮 `make check` 在 tests/ 的 test_if 链接步骤中断（exit 2）：
tests/Makefile.am 的 4 条规则把**已生成的头文件**追加进编译命令行
（`test_if$(EXEEXT): $(test_if_BUILT_SRC) test_if.h` 等 4 条，Makefile
1004/1007/1010/1013 行），2010 年 GCC 容忍该写法，clang-15 报
`clang-15: error: cannot specify -o when generating multiple output files`。
处理：从这 4 条规则删去命令行上的 .h（头文件依赖已由 check-am 先建
BUILT_SOURCES 保证，删去不改变测试语义），重跑 `make check` 全过。
文件：tests/Makefile.am →（configure 生成）tests/Makefile；测试源文件
（*.cc/*.cc_skel/*.test/*.err）一字未动。

## test_package 消费者闭环（N_consumer = 1，7 项断言）

test.py 以库使用者身份走完整闭环（工具型包：只跑 --help / 只打印 / 只查文件存在不合格）：

1. 写最小骨架 demo.cc_skel（@value@ 替换 + @IF@/@ELSE@ 分支）
2. 运行 `gengen --no-gen-version -i demo.cc_skel --file-name demo.h --gen-name demo`
3. 断言 demo.h 含 `class demo_gen_class` / `void set_value` / `void set_flag` / `generate_demo`
4. 用 C++ 编译器把生成的 demo.h 与消费者 main.cc 编译为可执行文件
5. 运行消费者，断言 stdout 与期望逐字一致：
   `demo begin\n  value=42\n  flag=yes\ndemo end\n`（设备 clang15/aarch64 实测值）

设备探针实测（与 test.py 同构的先行验证）：COMPILE_OK、RUN_EXIT=0、输出逐字一致。
test_package/conanfile.py 用 `self.tested_reference_str` 依赖被测包，`cross_building` 时如实跳过。

## 冒烟

`src/gengen --version` → `GNU gengen 1.4.2`（exit 0，未签名 ELF 在设备可直接运行）。

## 安装产物（staging 实测）

`bin/gengen` + `share/doc/gengen/{COPYING,ChangeLog,INSTALL,NEWS,README,THANKS}`。
无 .la、无头文件、无库——package_info 声明 bindirs=["bin"]、libs=[]。

## 配方验证轮次记录

- 第 1 轮 conan-verify：G1 FAIL——缺 `export_sources()` 方法。补
  `export_conandata_patches` 钩子（patches 为空时为 no-op）。
- 第 2 轮 conan-verify：G0 PASS（知识命中 E490 提示可执行位风险，配方已加
  防御性 chmod）；G1 PASS；G2 FAIL——conan create 在 -std=c++17 下报
  skelstruct.cc `no member named 'bind2nd'/'mem_fun'/'bind1st'`（C++17 移除，
  见"实撞坑 3"）。按仓库先例 rm_safe("compiler.cppstd") 处理。
- 第 3 轮 conan-verify：见最终汇报（执行中）。

## 路径 B 判断：不走 B（纯路径 A）

候选知识增量逐项查重结论：

1. `register`/`throw()` vs C++17 → **查重命中 E293**（关键词 register storage
   class/C++17/cppstd=17 精确覆盖，rec=toolchain-flag，已在其他包真实使用过
   used=1）。本包只是又一次命中，无新知识。
2. 老版 config.sub 拒绝 ohos/musl triplet、gnu-gnu native 方案 → E007 已覆盖
   config.guess/build-type 大类；同型方案已沉淀在 gengetopt 2.23 归档配方与
   其软件级 manifest。参数级微调（更老的 sub 连 aarch64-musl 都不认）不构成
   跨仓库复用的新知识。
3. umask 077 → E011/E129 既有受控方案。
4. texinfo/SUBDIRS/HMDFS libtool → gengetopt 2.23 配方注释与 manifest 已沉淀
   （同作者同构建体系，先例完备）。

结论：所有适配知识均有既有知识条目或已合入的同型先例，无可申报的跨仓库
复用增量 → 纯路径 A。

## 发现与知识积累

- ✅ 2010 版 config.guess 在 HMDFS 无法建临时文件且不识 HarmonyOS、config.sub 拒绝 ohos/musl triplet → 显式 gnu-gnu 双 triplet 跳过猜测（E007/E160，落在配方 generate()）
- ✅ configure 内嵌 umask 077 ×2 → 替换 022（E011/E129 受控方案，落在配方 build()）
- ✅ C++17 移除特性（register/bind1st/bind2nd/mem_fun）撞 profile cppstd=17 → configure() rm_safe(compiler.cppstd) 回默认标准 + scanner.cc register 清理（E293，构建级错误签名已复现入档）
- ✅ autotools 助手脚本可执行位在 HMDFS 适配路径可能丢失 → build() 防御性 chmod（E490）
- ✅ 设备/CI 无 texinfo → MAKEINFO=true + 顶层 Makefile SUBDIRS 收窄 lib src（gengetopt 2.23 同型先例，落在配方 generate()/build()）
- ✅ 2010 年代测试规则把已生成头文件放进编译命令行（GCC 容忍、clang 拒绝）→ 删命令行 .h，测试语义不变（本包 L3 笔记，详见上方"上游测试修改说明"）
---

**编译结束**: 2026-09-12 05:06
**最终状态**: built

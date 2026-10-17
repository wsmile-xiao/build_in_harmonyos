# DRAFT-ctemplate-2.4-no-pregen-configure-manual-autotools

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-09
> Source: ctemplate 2.4 HarmonyOS PC 适配（无预生成 configure → conanfile 内重建 configure 三件事）

## 现象

ctemplate 2.4 只发 git tag：GitHub release 无资产，Debian orig tarball 与
tag 内容 sha256 完全相同——**哪里都没有预生成 configure**。autogen.sh 依赖
autoconf/automake/libtool，构建沙箱不具备。直接编译也不行：每个 .cc 都
`#include <config.h>`，公开头全是 `.h.in` 模板，htmlparser 还需要
generate_fsm.py 生成的 BUILT_SOURCES 头。

## 根因

上游假定用户要么跑 autotools 全链，要么用 dist tarball（从没发布过）。
configure 实际只做三件产物：config.h、.h.in→.h、（构建期）fsm 头生成。

## 解决方案

conanfile build() 内手工完成这三件事：

1. **config.h 合成**：先 `grep -rhoE 'HAVE_[A-Z_0-9]+' src/ | sort -u` 枚举
   全部用量，已核实的 OHOS/musl/clang 特性定义为 1，不确定的（RWLOCK/
   SYS_ENDIAN_H 等）一律不定义走代码 fallback；
2. **.h.in 替换**：7 个 @var@。注意 `@ac_cv_cxx_hash_map@` 的值**带尖括号**
   （`<unordered_map>`，源码是 `#include @var@` 直接拼接），namespace=std；
   `@ac_google_attribute@` 用在 `#if` 里取 1；dllexport 两变量置空；
3. **codegen**：`sys.executable` 跑上游 generate_fsm.py 生成 3 个 fsm 头
   （沙箱必有 python3——conan 自己就跑在 python 上）。

之后按 Makefile.am 的 4 套库变体（threads/nothreads × NDEBUG/debug）直编，
**23/23 上游测试目标全量实跑**（自带 mini harness 无需 gtest；模板测试需
`TEMPLATE_ROOTDIR=<源码根>` 环境变量；statemachine_test 要把
statemachine.cc 复制为 .c 以 C 模式编译；3 个 shell 脚本自带 tmpdir 参数）。

## 禁止策略

- config.h 不得给未核实特性定义为 1——编译期才暴露，排查成本高。
- `@ac_cv_cxx_hash_map@` 替换值不得缺尖括号——`#include @var@` 语法错误。
- 不得只跑 threads 变体——nothreads 是上游一半测试量（9/20 二进制）。

## 适用范围

只发 git tag（无 dist tarball）且构建依赖 configure 产物的 autotools 库：
枚举宏用量 → 合成 config.h → 替换 .h.in → sys.executable 跑 codegen，
测试按 Makefile.am 的变体矩阵直编。

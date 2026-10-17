# kbd 2.9.0 适配笔记

## 编译环境

- 构建系统: autotools（kernel.org 发布 tarball 含生成 configure；设备 autoconf 2.73 / automake 1.18.1 / pkg-config 0.29.2）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（/data/service/hnp/bin）
- 状态: published（conan-verify G0-G4 + L2/L4/L5 全过）

## 编译步骤

conan create（ohos-aarch64 profile）：

1. generate(): AutotoolsToolchain `--host=aarch64-unknown-linux-musl --build=aarch64-unknown-linux-gnu`
   （显式三元组跳过 config.guess 并进入交叉模式）；`--disable-vlock`（规避 PAM）、
   `--disable-nls`（规避 gettext）、`--disable-werror`；AutotoolsDeps 聚合依赖；
   PKG_CHECK_MODULES 显式变量（ZLIB/BZIP2/LZMA/ZSTD CFLAGS+LIBS）；
   `-include shim/progname_shim.h` 强制注入 musl 兼容头
2. build(): configure（CONFIG_SHELL 命令级路由 /bin/sh）+ make -j1 +
   `make -C tests check`（上游 testsuite 真实执行）
3. test_package: 消费者测试 3 项断言真机执行（运行包内 loadkeys/setfont --version）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 working directory cannot be determined | profile buildenv 的 CONFIG_SHELL 指向 hnp bash，HMDFS 下 getcwd 必挂（E386/经验汇总 12.38①） | build() 内包装 self.run，configure 命令级路由 /bin/sh |
| 2 | config.status 报 can't create confXXXXXX/subs1.awk: Permission denied | configure 内 (umask 077 && mktemp/mkdir) 在 HMDFS 产出不可写目录（E011/§5.3） | 补丁 0001-configure-umask-hmdfs.patch 移除 2 处 umask 077 前缀 |
| 3 | error.c/version.c 编译报 use of undeclared identifier 'program_invocation_short_name' | glibc 专属全局量，musl 无 | 配方 exports shim/progname_shim.h，经 -include 强制注入：以 musl __progname 等价替换（覆盖 src/ 全部 10 处使用） |
| 4 | 大量 int→pointer 隐式转换错误（analyze.l 等） | 交叉模式下 AC_FUNC_MALLOC 假设 malloc 非标准，config.h 定义 malloc=rpl_malloc | autoconf 缓存变量 ac_cv_func_malloc_0_nonnull/realloc_0_nonnull=yes |
| 5 | 测试套件 43 用例全失败：Error loading shared library libzstd.so.1 | 测试二进制动态链接 zstd；testsuite 环境无压缩库路径 | 执行套件时注入 LD_LIBRARY_PATH（zstd 制品包 lib 绝对路径，12.38③） |

## 源码修改

无源码修改。补丁 1 个（配置脚本层）：

- patches/0001-configure-umask-hmdfs.patch：configure 内 2 处 `(umask 077 && mktemp/mkdir)`
  移除 umask 077 前缀（E011 受控方案）

## 依赖版本

- zlib/1.3.1、bzip2/1.0.8、xz/5.6.2（liblzma）、zstd/1.5.7（均为制品仓已发布包；压缩后端为 configure 可选项，全部启用）

## 上游测试清点（R51）

- 上游测试框架：GNU AutoTest（tests/*.at），N_static = 105（AT_SETUP 计数：
  libcommon 3 + libkbdfile 15 + libkeymap 29 + utils 8 + e2e 50）
- 配方内 `make check`（上游默认 unittest 范围）真实执行：43 例，42 通过、
  1 失败（libkbdfile test15：运行时 dlopen libbz2 解压 .bz2 keymap——bzip2 制品包
  仅含静态库，OHOS 无共享 libbz2，属制品形态限制）、12 例上游 AT_SKIP_IF 自跳过
- 补充全量运行（sh ./testsuite）：44 执行（42 通过 + 2 失败，另 1 例失败为
  psfxtable e2e 需 strace，OHOS 环境无 strace）、61 例 AT_SKIP_IF 自跳过
  （VT console 守卫与 memcheck/valgrind 守卫）

## 验证结果

- conan create + conan-verify：PASS（G0/G1/G2/G3/G4 + L2/L4/L5）
- 上游 testsuite（配方内执行）：42/43 通过（97.7%），12 例上游自跳过
- 消费者测试（真机）：test_kbd 3 项断言 3/3 通过——loadkeys --version 退出码 0、
  版本横幅输出、setfont --version 退出码 0（checks=3 failures=0）

## 路径 B 判断（GLM-58，2026-09-19）

判断：不走路径 B，按纯路径 A 交付。依据：①五个坑的修复均为既有经验条目
（E386/12.38①、E011/§5.3、E007 变体、12.38③）在单库内的直接应用；
②program_invocation_short_name 与 rpl_malloc 属通用 musl 移植问题，知识库已有
同族条目覆盖，无新增跨仓库知识增量；③消费者测试刻画的是工具行为语义。
---

**编译结束**: 2026-09-19 05:28
**最终状态**: built

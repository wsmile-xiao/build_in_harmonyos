# bglibs 2.04 适配笔记（GLM-15，2026-09-12）

平台任务号 7324，语言 C。worktree `~/qzy/GLM-15-bglibs-2.04`，分支 `feat/bglibs-2.04`。

## 1. 上游与构建系统

- 源码：https://untroubled.org/bglibs/bglibs-2.04.tar.gz
  SHA256 `e4ae34a4c43f72ff0c5f100b3ac432460e7d736a7f0708d5e429c97dd5c52474`
- 构建系统：**djb/spac 风格**（非 autoconf）。tarball 自带 Makefile（spac 生成），
  配置经 `conf-cc`/`conf-ld`/`conf-bin`/`conf-include`/`conf-lib`/`conf-man`
  文件，各 wrapper（`compile`/`ltcompile`/`load`/`makeshlib`）由 make 在构建时
  生成并**把 conf-* 首行原文嵌入脚本**。特性探测用 `choose`（编译/链接/运行
  `sys/try*.c`），生成 `sysdeps.h`；`systime.h`/`uint*.h` 等头亦为构建生成
  （AUTOFILES 机制）。
- 硬构建工具：**libtool**（ltcompile/ltload/makeshlib）。CI worker 无系统
  libtool → `tool_requires("libtool/2.5.4")`（制品仓已有，preflight 实证；
  cliquer 同款方案）。
- W0：preflight_check.sh PASS（无 conan 库依赖，bglibs 自包含）。
- W0b：归档树无 bglibs 历史 notes（全库 find 仅 libglibutil 模糊命中）。
  recipe-search 无相似配方（语料 4433 条）→ 首稿按模板手写。

## 2. 关键适配决策

### 2.1 conf-* 注入编译器（R33）
conf-cc 首行写为 `<profile CC> -W -Wall -Wshadow -Wno-unused-result -Os -g`，
CC 取 profile `tools.build:compiler_executables` 的 `c` 绝对路径；conf-ld 首行
`<CC> -g`。未使用裸 shell 变量。

### 2.2 两阶段构建（构建期生成器 + 交叉编译）
上游 `libraries` 目标依赖 6 个 `crc/*_table.c`，而 tarball **不含**这些表文件，
Makefile 规则要求运行构建期程序 `crc-gentab` 生成（6 条生成命令与上游 Makefile
逐字一致，见配方 `CRC_TABLES`）。CI worker（x86）无法运行 aarch64 OHOS 的
crc-gentab → 两阶段：
1. **Phase 1（native）**：探测构建机常驻编译器（`gcc`→`clang`→`cc` 顺序；
   设备命中 clang，CI 命中 x86 gcc），native 构建 crc-gentab 并运行生成 6 表；
2. **清理** native 中间产物（.o/.lo/.libs/wrapper/生成头），保留 crc-gentab 与表；
3. **touch 6 个表文件**（新于 crc-gentab，防止 Phase 2 make 重建表并运行交叉
   crc-gentab）；
4. **Phase 2（target）**：写 profile 工具链 conf-cc，`make sysdeps.h libraries -j2`。
   sysdeps.h/dl.lib/rt.lib 被删后按目标工具链重新 choose 探测。

### 2.3 choose 运行型探测的交叉退化
sysdeps.h 的 `choose ... clr` 探测含运行时判定。设备构建（本机 aarch64）探测
真值；CI 交叉构建时 r 模式探测失败按设计回退到 h0（portable fallback），特性集
保守退化但可编译。各环境独立生成 sysdeps.h，产物均可编译链接（G2 实证）。

### 2.4 库包语义裁剪
仅构建 `sysdeps.h libraries`（上游 `all` 目标会级联 `selftests` 与 programs）。
programs（bg-installer/cli-generate）与 man 页需要 perl 版 `cli-generate` 生成器，
且非库 API 表面 → 不构建不打包，`commands.json` 不适用（纯库包）。打包内容=
INSTHIER 的 include（平铺头 + pwcmp/ + vmailmgr/ + 生成的 sysdeps.h/systime.h/
uint*.h——str.h 等公共头依赖 sysdeps.h 的宏）+ lib 下 5 个静态库
（libbg.a/.libs 与 libbg-cli/libpwcmp/libpwcmp-module/libvmailmgr 同在 .libs/，
与上游 INSTHIER 安装清单一致）。**不打包 .la**（烤死 libdir 绝对路径）。

## 3. 上游测试四维账本（真机 selftests.sh）

| 维度 | 值 | 来源 |
|---|---|---|
| N_static（上游源码静态声明） | **118** | tarball 内 `grep -l '#ifdef SELFTEST_MAIN' */*.c` 逐文件计数（djb selftest 的注册入口即该标记；无 runner 层） |
| N_registered（构建系统可执行） | **118** | selftests.sh 无独立注册层，`fgrep -l` 运行时列表与静态清单一致 |
| N_executed（真机实际执行） | **118** | 设备第二轮全量运行，`Testing ` 计数 118（第一轮 69"失败"系 selftest-cmp 未生成的假失败，重建比较器后作废） |
| 通过 | **117** | 输出与 SELFTEST_EXP 逐行比对一致 |
| 未通过分类 | **1（环境失败）** | `net/connect4.c`：期望 loopback TCP connect 成功，设备实际 `connect(127.0.0.1)=EPERM`（SELinux/未签名进程网络策略限制），4 个 bind/listen 断言全过、仅 connect 行差异；非代码/适配缺陷 |
| 跳过 | 0 | — |
| N_consumer（新增消费者测试） | **1** 程序（19 项断言） | test_package/test.c：str_init/copy/append/prefix/free + fmt_ulldec + crc32_block==0xCBF43926 |

通过率口径：执行项 117/118；静态全量 117/118（1 项环境失败逐项说明如上）。
消费者测试另列：1/1 通过（conan create 设备运行）。

## 4. 消费者测试（test_package）

以使用者身份 `#include <bglibs/str.h> <bglibs/fmt.h> <bglibs/crc32.h>`，链接
CMakeDeps 生成的 `bglibs::bglibs`，断言真实行为（19 项 CHECK，任一失败退出码
非 0）：str 动态串全生命周期、fmt_ulldec 十进制格式化、crc32_block 对标准向量
"123456789" 的 IEEE CRC-32（0xCBF43926）。交叉构建时编译不运行（conanfile
test() 显式分支），设备本机构建真实运行。
迭代记录：首版误用 `str_catf(" %u")`（bglibs 格式串是自有语言，非 printf 语义，
上游 str/catf.c 自测即证），G2 运行消费者测试当场暴露 2 项断言失败——恰证明
测试真实消费库行为；改用无歧义组合（str_catc + fmt_ulldec + str_cats）后复验。

## 5. 探索构建证据（~/tmp/uc2/bglibs-2.04/）

- `explore-build.log`：设备探索构建（conf-cc=clang）`make sysdeps.h libraries
  programs man -j2` 全过：5 个静态库（libbg/libbg-cli/libpwcmp/libpwcmp-module/
  libvmailmgr）+ bg-installer 链接成功；HMDFS 硬链接警告被 libtool 复制 fallback
  吸收（产物完整）。
- `selftests.log`：第一轮 69 假失败（selftest-cmp 缺失，expected==actual 完全
  相同仍判失败）→ 根因为我探索构建未触发 selftest-cmp 生成目标；`make
  selftest-cmp` 后作废重跑。
- `selftests2.log`：**118 执行 / 117 通过 / 1 环境失败**（净结果，见 §3）。

## 6. 路径 B 判断

**倾向走 B（由主理收口）**。候选知识主题："djb/spac 构建系统包的交叉编译
两阶段模式"。判断依据：
- 可复现症状：Makefile 规则要求运行构建期生成器（crc-gentab），CI 交叉环境
  无法执行目标架构 ELF → make 失败（证据：探索构建 + conan create 日志）。
- 跨仓库复用价值：untroubled.org/djb 系（cvm 0.97=平台任务 6951、ucspi 系列、
  djbdns 等）与一切"构建期生成器"包（gperf/bison 生成器类同构）复用同一模式
  （native bootstrap 生成器 → 清理 → touch 生成物 → 目标工具链全量）。
- 查重：knowledge/graph/index.tsv 未见 spac/djb 两阶段构建条目（待 conan-verify
  后以 engine/draft-review 复核并落 .kv/.md 草稿）。
- 真实验证：本包 conan create（G2）即触发实例与验证。

## 7. 遗留与风险

- CI 侧 sysdeps 特性集与设备不同（保守退化），若某特性 h0 分支编译失败会在
  CI 暴露——choose 机制本身保证两分支可编译，风险低。
- `net/connect4.c` 环境失败若评审要求，可用设备自签工具复测（EPERM 大概率与
  未签名进程网络权限有关），不影响库功能与消费者测试。
---

**编译结束**: 2026-09-14 02:52
**最终状态**: built

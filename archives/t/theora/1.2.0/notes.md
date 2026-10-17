# theora 1.2.0 适配记录

## 任务背景（2026-09-19）

- 平台任务 #13475（taskBranch=feat/theora-1.2.0），theora 全新包线（制品仓 conan list "*theora*" 为 0）。
- **Xiph 三件链收官**：ogg/1.1.1（PR #10038）→ vorbis/1.3.7（PR #10592）→ theora/1.2.0（本件）。
  开工前 conan download 双前置确认均已发布到制品仓。
- 上游 xiph/theora tag v1.2.0（2025-03-29 正式发布，downloads.xiph.org 官方 tarball）。

## 上游形态

- 纯 C，三库：libtheoradec（解码）/ libtheoraenc（编码）/ libtheora（pre-1.0 legacy 合并 API）。
- **纯 autotools**（configure.ac + 预生成 configure），无 CMake——与 vorbis（双构建系统选 CMake）不同，
  theora 只有 autotools 一条路，打法直接复用 ogg 1.1.1 的 autotools 先例。
- tarball 自带 2022-01-09 版 config.guess/config.sub（新式 GUESS=）+ 完整 configure，**无需 autoreconf**。
- configure.ac 里 PKG_CHECK_MODULES(OGG, ogg >= 1.3.4) 版本闸与 ogg/1.1.1 包名线版本号冲突——
  走 XIPH_PATH_OGG fallback（--with-ogg + --disable-oggtest，仅编译链接探测、无版本检查）。
  theora 实际使用的 ogg API 面（oggpackB_write/reset/bytes/get_buffer/writeinit/writeclear 系 +
  oggpack_write/writeclear）在 ogg 1.1.1 头文件与符号表里**全部存在**（曾逐符号核对）。
- 库本体只依赖 ogg；SDL/PNG/TIFF/cairo/vorbis 全是 examples 专用（encoder_example/player_example/
  png2theora/tiff2theora）→ `--disable-examples` 一刀关闭，无需任何额外依赖。
- aarch64 不匹配 configure.ac asm 分派的 arm* case → 纯 C 路径（无 ARM 汇编、无 perl 依赖）。

## 三处关键适配（踩坑记录）

1. **0001-ogg-uint64-portability.patch**（静态补丁）：lib/state.c 的 border-mask 计算用了
   `ogg_uint64_t`——这是 libogg >= 1.3.x 才有的类型（ogg 1.1.1 的 Linux config_types.h 只有
   ogg_int64_t；os_types.h 的 MinGW 分支才有 ogg_uint64_t）。**这也是上游 ogg >= 1.3.4 版本闸的
   真实根因之一**。补丁：局部变量改 uint64_t（含 (uint64_t)1<< 移位转换，避免有符号溢出 UB）+
   显式 #include <stdint.h>。全库仅 state.c 两行使用。
2. **config.sub kernel-OS 白名单**（配方内运行时补丁）：2022 版 config.sub 有
   `case $kernel-$os` 组合校验白名单（linux-gnu* | linux-dietlibc* | linux-android* | ...）。
   官方 perl 补丁 patch-autotools-ohos.pl 的 2.3 步（linux-uclibc* 模式注入 linux-ohos）被其
   "already present" 守卫误跳——2.1 步刚加的 ohos-linux triplet 里已含字面 "linux-ohos"（basic_os=linux-ohos）。
   症状：config.guess 正确输出 aarch64-unknown-linux-ohos，但 configure 报
   "Kernel `linux' not known to work with OS `ohos'"。配方 `_patch_config_sub_kernel_whitelist`
   在 linux-gnu* 行追加 `| linux-ohos*`。
3. **make check 运行期 LD_LIBRARY_PATH**：9 个测试程序经 libtool --mode=execute wrapper 执行，
   加载 in-tree libtheora*.so（DT_NEED libogg.so.0 指向 conan ogg 包目录）。profile 的
   LD_LIBRARY_PATH 只覆盖工具链不含依赖包 → generate() 里
   `env.prepend_path("LD_LIBRARY_PATH", ogg_libdir)` 进 conanbuild.sh。

## 测试（N 实测口径）

- 上游 tests/Makefile.am：TESTS_DEC（noop_theora/comment/comment_theoradec/comment_theora）+
  TESTS_ENC（noop/noop_theoraenc/granulepos/granulepos_theoraenc/granulepos_theora）= **N=9 个
  check 程序**，check_PROGRAMS=$(TESTS) 由 make check 驱动（libtool wrapper + LOG_COMPILER）。
- 本地实测：conan create 的 build() 内 autotools.make(target="check") → **PASS 9 / FAIL 0**
  （证据：reports/upstream-test-suite.log）。
- test_package 消费者往返（安装后包）：th_version_string 断言 + th_encode_alloc(64x48 4:2:0) +
  th_encode_flushheader 产 3 头部包 + legacy theora_info API 符号 + th_decode_headerin/alloc
  完整解码链 → "theora consumer smoke passed: Xiph.Org libtheora 1.2.0 20250329 (Ptalarbvorm)"。

## Conan 配方结构

- requirements：ogg/1.1.1（transitive_headers=True + transitive_libs=True——theora 公共头
  include <ogg/ogg.h>，公共 API 用 ogg_packet/ogg_int64_t 类型）。
- 组件：theoradec / theoraenc / theora（三组件，cmake_file_name=Theora，
  Theora::theoradec / Theora::theoraenc / Theora::theora + pkg_config_name theoradec/theoraenc/theora）。
  theoradec 的 ogg 需求是 transitive 类型层；theoraenc/theora 链接期真依赖 ogg（oggpackB 系符号）。
- 无 commands.json（纯库，无可执行产物——examples 已禁）。

## 依赖发布状态

- ogg/1.1.1 ✅ 已发布（rev 5185cdae，2026-09-17）；vorbis/1.3.7 ✅ 已发布（rev 2560813f，
  2026-09-18）——本件只 requires ogg，vorbis 无需引用（examples 禁用后无 vorbis 依赖）。

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-09-19
- 编译器: clang/clang++（ohos-aarch64 profile，本机 HarmonyOS PC 直接跑上游测试）
- 状态: built（本地 conan create exit 0 + make check 9/9 + 消费者 smoke 通过）
---

**编译结束**: 2026-09-19 01:12
**最终状态**: built

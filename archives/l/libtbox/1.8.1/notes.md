# libtbox 1.8.1 适配笔记

## 软件概述

**tbox** 是 TBOOX 团队的类 glib 跨平台 C 库（stream、coroutine、container、
algorithm、charset、hash、xml、regex、object、database 等模块），xmake 构建
工具的上游基础库。入口 API：`tb_init()` / `tb_exit()`，头文件 `tbox/tbox.h`。

- **上游版本**：1.8.1（tag v1.8.1，2026-07-05）
- **上游仓库**：https://github.com/tboox/tbox
- **官方源**：https://github.com/tboox/tbox/archive/refs/tags/v1.8.1.tar.gz
- **许可证**：Apache-2.0
- **构建系统**：custom（xmake.sh script-only `configure` 生成纯 Makefile，
  无需 xmake 二进制；`--toolchain=envs` + `CC/CXX` 环境变量指定编译器）

## 构建系统分析

- 顶层 `xmake.lua`：`set_project("tbox")`，`set_version("1.8.1", soname)`，
  语言 c99；库 target 名 `tbox`，kind 取 `--kind`（static/shared）。
- `src/xmake.lua` 定义选项：`demo`（默认 y）、`small`（默认 y，开启时关闭
  全部模块）、`micro`、`float`、`info` 等，以及模块选项（xml/zip/hash/
  regex/object/charset/database/coroutine）与可选三方包（zlib/mysql/
  sqlite3/openssl/polarssl/mbedtls/pcre2/pcre，均为 optional）。
- 根目录 `configure` 即 xmake.sh 引擎（约 173KB 纯 sh）：`./configure`
  按 `--plat/--arch/--mode/--kind/--toolchain/--prefix` 与项目选项
  （Nixpkgs 同样用 `--hash=y --charset=y --float=y --demo=n` 传参）生成
  `Makefile`（或 `--generator=ninja` 生成 build.ninja）。
- 生成的 gmake Makefile 支持 `DESTDIR` + `PREFIX` 变量安装
  （`_gmake_add_switches`），`--prefix=/` + `DESTDIR=<包根>` 时文件直落
  `<包根>/lib`、`<包根>/include`。
- 库安装形态：`lib/libtbox.a(.so)` + `include/tbox/**.h`（不含 impl 内头）
  + 自动生成的 `tbox.config.h` + pkgconfig/cmake import 文件。

## 依赖链与发布状态（W0/R36）

| 依赖 | 关系 | 处理 |
|------|------|------|
| pthread / dl / m / c | 系统库 | `cpp_info.system_libs`，`os in ("Linux", "OHOS")`（R32） |
| zlib/sqlite3/mysql/openssl/polarssl/pcre2/pcre | 上游 optional | 全部 `--xxx=n` 关闭，regex 走 posix 后端，zip 用内置编码 |

- 归档内无前置依赖包需求；本配方 `requirements` 为空。
- 参考 knowledge：xmake 3.0.5 notes 记录 xmake.sh 在 HMDFS 上曾生成损坏
  构建文件（并发写交错）——本配方保持 `make -j1`（R9）并走默认 gmake
  生成器以降低风险；若真机预检暴露 HMDFS 问题再切 ninja 或加串行化。

## 配方关键决策

1. **不用 `tool_requires xmake`**：script-only configure 不需要 xmake 二进制，
   且归档中 xmake/3.0.5 状态为 built（未发布），require 会触发 R36 门禁。
2. **`--toolchain=envs`**：xmake.sh 内置 `envs` toolchain 从 `$CC/$CXX/$AR`
   取工具链；配方从 `tools.build:compiler_executables` 取值后格式化进命令
   行（R33 合规，L0h 只拦 `${CC}` 裸引用，本配方无此写法）。
3. **`CONFIG_SHELL` 与显式解释器**：OHOS 无 `/bin/sh`（R5），沿用 zlib 范式
   `CONFIG_SHELL=<bash> CC=<cc> CXX=<cxx> <bash> ./configure …`。
4. **`--plat=linux --arch=arm64`**：xmake.sh 无 ohos plat；OHOS 用户态对纯 C
   库走 linux 分支（posix + epoll poller，pthread/dl/m/c 直链）。
5. **`--demo=n --small=n`**：demo 仅为示例非测试且不进安装；small=n 打开
   全模块（hash/charset/xml/regex/coroutine…）得到完整 libtbox。
6. **默认静态**（`shared=false`，参考 libdvdnav 先例）：首轮求稳，避开
   .so 版本链接与 RPATH 不确定性；非系统同名库，R26 不强制。
7. **无 `make check`**：上游无测试套件（见下节审计），build() 只构建；
   验证全部由 test_package 承担（L1c 仅在 MANIFEST 声明时才查 check 痕迹）。

## 上游测试套件审计（W3/TEST_QUALITY_SPEC/R51）

审计对象：`v1.8.1.tar.gz`（1227 个条目，sha256 见 conandata.yml）。

| 审计项 | 结果 |
|--------|------|
| `TEST(` / `TEST_F`（gtest） | 0 处 |
| `def test_`（pytest） | 0 处 |
| `tests/` / `test/` 目录 | 不存在 |
| ctest / meson test / `make check` 注册 | 无；生成 Makefile 目标仅 all/clean/install/run 系 |
| `src/demo/other/test.c` | 空 stub（`tb_demo_other_test_main` 直接 `return 0`），属示例程序入口，非测试 |
| `src/demo/*`（约数十个 `*.c` 示例） | 均为功能演示（container/hash/stream/network…），无断言 harness、无退出码语义 |
| `.github/workflows/*` | 仅各平台构建（`xmake`/configure + 编译），无测试步骤 |

**结论**：tbox 1.8.1 上游**不存在**任何测试用例（单元/集成/其他均为 0）。
test_package 自建真实调用 libtbox API 的消费者验证程序（见 test_package/）：
`tb_init`、CRC32 tbox 变体已知答案（"123456789"/seed0→0x7F89A189）、空输入、
确定性/区分性、vector 插入/长度/内容，全失败路径均非零退出。

## 本轮修复（2026-09-14 真机 test_package 链接失败）

- 现象：`clang … -ltbox` 报 `undefined symbol: tb_crc32_make / tb_crc32_make_from_cstr`（另有截断的后续未定义符号），即归档找到但 hash 模块符号缺失。
- 根因判断：`--small=n` 理论上应重新启用模块（`src/xmake.lua` 的 `after_check` 仅在 small/micro 启用时关闭模块），但为防 xmake.sh 选项默认值漂移导致模块被裁，显式追加 `--micro=n --float=y --info=y --exception=n --deprecated=n --xml=y --zip=y --hash=y --regex=y --object=y --charset=y --database=y --coroutine=y` 保全模块全开。
- 加固：`build()` 打印 `tbox.config.h` 的 `TB_CONFIG_MODULE_HAVE_*` 与归档清单；`package()` 在可写 TMPDIR 下执行 `make install`（readonly_tmp），并以 `llvm-nm/nm` 严格校验已安装 `libtbox.a` 导出 `tb_init/tb_crc32_make/tb_crc32_make_from_cstr/tb_vector_init`，缺失即 fail-fast；`test_package` 的 `HMBS_TEST_PACKAGE_RESULT` 按 8 条 CHECK 断言如实上报 `discovered/passedCount=8`。
- 待下轮真机预检验证。

## 本轮修复(2026-09-14 真机 test_package 1 例 FAIL + readonly_tmp 诊断)
- 现象:conan create 到 test_package 阶段,vector 3 条 PASS 后 `1 TEST(S) FAILED`,exit 1;平台诊断同时报 `[readonly_tmp] /tmp 只读`.
- 根因:`test_libtbox.c` KAT 误用标准 IEEE 向量 0xCBF43926;但 src/tbox/hash/crc32.c 的 tb_crc32_make_impl 直接以 seed 为迭代初值、无终异或,seed=0 时 "123456789"(9B)实际为 0x7F89A189(以 g_crc32_table 本地复算验证).
- 修改:test_libtbox.c KAT 更为 0x7F89A189 并加注释,KAT/确定性块增加 printf 打印实际 crc,CHECK 数保持 8;未删除断言;test() 以 _with_tmpdir 包裹二进制调用.
- 待下轮真机预检验证 8/8.

## 验证结果（待真机预检回填）

- 编译状态：待真机预检（本轮仅完成未提交工作树，未跑 conan）
- 上游测试用例通过率：0/0（上游无测试套件，见上节审计）
- 新增测试用例通过率：待真机 evidence 轮填写（test_libtbox.c 共 8 条 CHECK 断言，
  不得猜测，以预检日志 `HMBS_TEST_PACKAGE_RESULT` 为准）

## 已知限制 / TODO

- `--plat=linux` 是基于“OHOS 用户态 Linux ABI 兼容 + 纯 C 无 bionic 特有调用”
  的判断；若真机出现平台相关编译失败（如 poller/epoll、coroutine 上下文汇编），
  下轮按日志收敛（备选：切 small 模式裁剪模块）。
- `envs` toolchain 对 `CC` 的 honored 行为以真机 configure 日志为准；
  若被忽略，备选 `--toolchain=clang`（OHOS 工具链即 clang 15）。
- 真机预检在 HarmonyOS aarch64 环境实测；CI 侧由官方 Buildbot worker 复核。

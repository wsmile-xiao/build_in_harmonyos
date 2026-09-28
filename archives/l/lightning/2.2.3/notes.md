# GNU lightning 2.2.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-24
- 编译器: clang / clang++
- 状态: built

## 编译步骤

```bash
# 源码包（官方 GNU 源）
#   https://ftp.gnu.org/gnu/lightning/lightning-2.2.3.tar.gz
#   sha256 = c045c7a33a00affbfeb11066fa502c03992e474a62ba95977aad06dbc14c6829

# Conan 配方内步骤（AutotoolsToolchain 注入环境）
./configure --disable-disassembler --disable-devel-disassembler MAKEINFO=true
make -j1
make -j1 check        # 上游测试 → check/test-suite.log（automake 汇总）
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 host 三元组无法识别 | 自带 config.guess(2023)/config.sub(2023) 无 HarmonyOS 支持 | 0001-config.guess.patch 识别 UNAME_SYSTEM=HarmonyOS 输出 aarch64-unknown-linux-ohos；0002-config.sub.patch 增加 ohos OS 与 linux-ohos 内核-OS 组合 |
| 2 | configure 创建临时目录失败 | configure 用 umask 077 创建 ./confXXXXXX，HMDFS 权限受限 | 0003-configure-umask-022.patch 将 umask 077 改为 022（两处） |
| 3 | 可选 disassembler 依赖 binutils | OHOS 无 libbfd/libopcodes/libiberty/zlib | 显式 --disable-disassembler 只构建核心 JIT 库 |
| 4 | configure 报 `working directory cannot be determined`（getcwd 失败） | HMDFS 限制父目录 getcwd/readdir，configure 的 `ac_pwd=\`pwd\`` 失败 | conanfile.py 新增 `_fs_env`（PWD/TMPDIR/SHELL/CONFIG_SHELL）与 `_patch_configure_for_ohos`：把 `ac_pwd=\`pwd\`` 改为 `ac_pwd=\`pwd 2>/dev/null \|\| echo $PWD\``，umask 022 + `${TMPDIR:-.}/confXXXXXX`，并在 build() 中先后对 source/build/config.status 打补丁；generate() 把可写 TMPDIR 写入 buildenv |
| 5 | `make all` 递归进入 doc/ 重建 lightning.info 时 `makeinfo: command not found`（Error 127） | OHOS 无 Texinfo/makeinfo；doc/Makefile.am 经 `missing` 包装调用 makeinfo，`missing` 无法生成 info 目标而中止 | `generate()` 的 configure_args 追加 `MAKEINFO=true`：覆盖 Makefile 变量为 no-op true（returns 0），info 节点视为已更新，`make all`/`make check`/`make install` 均不再触发 makeinfo；tarball 内置 doc/lightning.info 保持不变，核心 JIT 库与测试不受影响 |

## 源码修改

- `patches/0001-config.guess.patch` — config.guess 增加 `*:HarmonyOS:*:*)` 分支，
  把 UNAME_MACHINE 映射后输出 `${MACHINE}-unknown-linux-ohos`。
- `patches/0002-config.sub.patch` — config.sub 的 OS 识别列表加入 `ohos*`，
  内核-OS 组合校验列表加入 `linux-ohos*`。
- `patches/0003-configure-umask-022.patch` — configure 临时目录创建由 umask 077
  改为 022（两处）。
- `conanfile.py` — 运行时 HMFS 加固：`generate()` 注入可写 TMPDIR 到 buildenv；
  `build()` 里 `_fs_env()` 设置 PWD/TMPDIR/SHELL/CONFIG_SHELL，`_patch_configure_for_ohos()`
  在 configure 运行前把 `ac_pwd=\`pwd\`` 降级为 `ac_pwd=\`pwd 2>/dev/null || echo $PWD\``，
  并把临时目录改用 `${TMPDIR:-.}` + umask 022；configure 生成 config.status 后再补打一次。
  对应真机错误 `configure: error: working directory cannot be determined`（HMDFS getcwd）。

## 依赖版本

- 无第三方构建依赖（核心 JIT 库仅需 libc / libm / libdl）。

## 验证结果

```bash
# make check（automake TESTS，aarch64）
#   aarch64 下 x87/arm/nodata 条件分支均不生效：
#     base_TESTS = 67 个 .tst 转写用例（check.sh 驱动）
#     + ccall self setcode nodata ctramp carg cva_list catomic protect riprel cbit callee = 12 个 C 测试程序
#     合计 79 个注册 TESTS
#   汇总写于 check/test-suite.log：含 # TOTAL/# PASS/# FAIL/# SKIP/# XFAIL/# XPASS/# ERROR
#   conanfile.py build() 解析该汇总并输出 HMBS_UPSTREAM_TEST_RESULT 标记。
```

## 注意事项

- 上游测试计数口径为 automake `autotools_tests`（check/Makefile.am 的 TESTS 变量）。
- JIT 依赖 mmap/mprotect（jit_memory.c），OHOS 内核提供，无需特殊处理。
- `check_PROGRAMS` 中的 `cldstxba` 编译但不加入 TESTS，不计入上游注册总数。
- HMBS 真机预检最终以真实 test-suite.log 为准，若出现个别平台差异用例将据实
  上报 gaps 并定位根因。

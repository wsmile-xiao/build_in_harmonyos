# sharutils 4.15.2 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang (aarch64-unknown-linux-ohos)
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built
- 软件类型: 命令行工具集 (package_type=application, 无需链接的库)

## 编译步骤

conan 配方 (`conanfile.py`, AutotoolsToolchain + Autotools helper) 内完成,
关键命令与配置:

`CONFIG_SHELL=<bash> SHELL=<bash> configure gl_cv_have_weak=no CFLAGS="-Wno-error=implicit-function-declaration -Wno-error=implicit-int -Wno-error=int-conversion"` → `make -j1` → `make check -j1`

- `SHELL`/`CONFIG_SHELL` 取可用 bash (回退 `/data/service/hnp/bin/bash`), OHOS 无 `/bin/sh`。
- 构建与测试共用 HMBS 注入的可写 `TMPDIR`/`TMP`/`TEMP`, 不回退到只读 `/tmp`。
- `makeinfo` 缺失时追加 `MAKEINFO=true`, 仅跳过 `doc/sharutils.info` 重建,
  6 个上游 TESTS 照常全部执行。
- 上游测试在 `build()` 内真实执行, 解析 `tests/test-suite.log` 的
  `# TOTAL/# PASS/# FAIL/# SKIP` 汇总行 (兼顾 XFAIL/XPASS/ERROR) 产生
  `HMBS_UPSTREAM_TEST_RESULT` 标记; 执行数为 0 直接失败, 不计为通过。
- 参照夹具非空校验: `tests/shar-1.ok` (3727 字节)、`tests/testdata` (381 字节);
  为空则直接失败, 杜绝空文件比空文件的虚假通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 无法识别 HarmonyOS, configure 报 `unable to guess system type` | 旧 config.guess 无 OHOS 分支 | patches/0001 按 `*:HarmonyOS:*` 映射到 `aarch64-unknown-linux-ohos` |
| 2 | `config.sub` 拒绝 `aarch64-linux-ohos` 三元组 | 旧 config.sub 无 ohos-linux 允许项 | patches/0002 接受 ohos-linux 三元组 |
| 3 | configure 自身 `umask 077 && mktemp/mkdir` 在 HMDFS 上失败 | HMDFS 对 0700 临时目录与部分 mktemp 语义不支持 | patches/0003 把 configure 内该处放宽为 022, 并增加 CONFIG_SHELL 回退到 bash |
| 4 | 链接报 `program_name` 重复符号 | `src/*-opts.h` 的暂定定义被工具 `.c` 与 `*-opts.c` 同时发射, clang 15 / GCC 10+ 默认 `-fno-common` | patches/0004 四处声明加 `extern` (与 BLFS 同款修复) |
| 5 | clang 把隐式函数声明、隐式 int、int 转换当 error | 2015 年旧代码写法 | `extra_cflags` 追加三个 `-Wno-error=` 降级为警告 |
| 6 | `intl/lock.h` 报 `use of undeclared identifier 'pthread_cancel'` | gnulib 弱符号探测在 OHOS musl 上误判 (`USE_POSIX_THREADS_WEAK=1`), 而 musl 无 `pthread_cancel` | configure 参数预设 `gl_cv_have_weak=no`, configure 后再清理生成 `config.h` 残留定义 (双保险) |
| 7 | `make check` 在 doc/ 目录以 Error 127 终止, 0 个 TEST 执行 | CI/真机缺 texinfo/makeinfo, `missing makeinfo` 包装重建 info 失败 | 缺 makeinfo 时传 `MAKEINFO=true` (automake 官方 no-op), 只跳过文档重建 |
| 8 | uutest-1 与 shar-1 在不同全局 umask 下互斥失败 | HMDFS 上 chmod 为静默 no-op, 创建模式即最终模式; uutest-1 需 test.bin 为 0664 (umask 002), shar-1 需 shar-1.in 为 0644 (umask 022) | 各脚本内作用域 umask (uutest-1 置 002, shar-1 置 022), 断言原文不动 |
| 9 | shar-3 在 HMDFS 临时目录下 `mkdir subdir`/解包失败 | 运行期 TMPDIR 的 0700 子目录不可用, 且归档内含自身 (`archive cannot contain itself`) | 严格 0700 探测, 不通过则把 TMPDIR 重定向到构建目录之外的同文件系统可写目录; shar-3 的 `(umask 077` 放宽为 `(umask 022`, 空 ctypes 回退到 `none` |
| 10 | shar-1 后半段 `uudecode` 解析到系统 `/usr/bin/uudecode` (非 GNU 实现) | 测试脚本用 PATH 裸调 `uudecode`, 而归档载荷是 GNU uuencode 编码 | `make check` 前把刚构建的 `src/` 前置到 PATH, 用 GNU uudecode 解码 |
| 11 | shar 在 HMDFS 构建目录下 `xgetcwd()` 失败导致归档缺 `Source directory was` 头行 | HMDFS 下 getcwd 对 conan 构建目录家长链解析失败 | 构建前 `chdir` 到 build 文件夹并导出逻辑 `$PWD`; 源码级 `$PWD`/`$USER`→`$LOGNAME`→`unknown` 回退 (行号无关的字符串替换, 幂等) |

## 源码修改

- `patches/0001-config.guess.patch`: 识别 HarmonyOS/OHOS, 映射 OHOS libc 到 linux-ohos 三元组。
- `patches/0002-config.sub.patch`: 接受 `aarch64-linux-ohos` / ohos-linux 三元组。
- `patches/0003-configure.patch`: HMDFS 兼容 (umask 077→022) 与 CONFIG_SHELL bash 回退。
- `patches/0004-fno-common-program-name.patch`: `src/shar-opts.h`、`src/unshar-opts.h`、`src/uuencode-opts.h`、`src/uudecode-opts.h` 的 `program_name` 加 `extern`。
- `conanfile.py` 内行号无关的字符串替换 (替代易漂移的 shar.c unified-diff 补丁):
  `src/shar.c` 增加 `<stdlib.h>`、`getcwd` 失败时回退 `$PWD` 输出头行、
  `set_submitter` 空指针安全回退 (`$USER`/`$LOGNAME`/`unknown`);
  执行中的 `tests/shar-3`、`tests/uutest-1`、`tests/shar-1` 拷贝做作用域 umask、
  ctypes 回退与模式记号规范化。所有上游断言原文未动, 无跳过、无删除。

## 依赖版本

- 无 conan 依赖, 零第三方运行时依赖 (gettext/gnulib 为源码内 `intl/`、`lib/` 自带)。
- 构建工具: 真机/CI 的 autoconf、make、clang 工具链 (配方内不写死路径, 取环境与 HMBS 注入)。

## 验证结果

- 上游官方测试 (`make check -j1`, `tests/Makefile.am` 的 TESTS:
  uutest-1、uudecode-2、shar-1、shar-2、shar-3、shar-4, 共 6 个):
  在 HarmonyOS aarch64 环境实测 total=6 executed=6 passed=6 failed=0 skipped=0, 通过率 6/6 (100%)。
- 新增消费者测试 (`test_package/test_sharutils.sh`:
  uuencode/uudecode 往返逐字节比对、shar/unshar 往返逐字节比对, 非空负载 + 内容 grep, 共 2 个断言):
  通过率 2/2 (100%)。
- 交付二进制: `shar`、`unshar`、`uuencode`、`uudecode` (随包 `bin/` 目录)。
- 软件级 `commands.json` (type=tool) 已存在, 本次新增版本级 `manifest.yaml` 与本笔记。

## 注意事项

- `make -j1` 为硬性要求 (并行 make 触及 HMDFS jobserver fifo 限制)。
- 任何配方/补丁/测试改动后, 旧的真机验证结果即失效, 需重新完整预检。
- 上游为纯 C 工具集, 本次适配未改动上游功能逻辑与测试断言, 仅做平台可移植修复。

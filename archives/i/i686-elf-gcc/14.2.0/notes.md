# i686-elf-gcc 14.2.0 适配笔记

## 概述

GNU GCC 配置为**交叉编译器**，目标 `i686-elf`（裸机 / freestanding ABI）。
产出的 `i686-elf-gcc` / `i686-elf-g++` 及 freestanding `libgcc` 运行于
HarmonyOS PC (aarch64) 宿主，生成 i686 ELF 目标代码；不在宿主执行 i686 代码。

- build/host = `aarch64-linux-ohos`（HarmonyOS PC）
- target = `i686-elf`（freestanding，`--without-headers`）

与仓库已有的 `gcc/9.5.0`（**原生**编译器，target=aarch64-linux-ohos）不同，本包：
- 是交叉编译器（`--target=i686-elf`）；
- 不需要 OHOS sysroot / `ohos.h` / `gcc/config.gcc` 的 ohos 分支（那些是 target=ohos 才需要的）。

与 `i686-elf-binutils/2.46.1`（同 target 的交叉汇编器/链接器）配套，本包
`requires("i686-elf-binutils/2.46.1")` 以取得 `i686-elf-as/ld/ar/nm/ranlib`。

## 构建系统 / 编译器

- autotools（GCC 定制 `configure && make all-gcc && make all-target-libgcc`）
- 编译器：clang / clang++（来自 ohos-aarch64 profile，`/data/service/hnp/bin/clang`）
- 依赖：i686-elf-binutils/2.46.1（Conan requires）+ bundled gmp/mpfr/mpc（in-tree）

## 依赖版本（bundled in-tree）

GCC 14.2.0 上游 `contrib/download_prerequisites` 精确选择：

| 依赖 | 版本 | 说明 |
|------|------|------|
| gmp | 6.2.1 | in-tree，`<src>/gmp/` |
| mpfr | 4.1.0 | in-tree，`<src>/mpfr/` |
| mpc | 1.2.1 | in-tree，`<src>/mpc/` |
| isl | 0.24 | **不下载**，`--without-isl` 禁用 Graphite |

> 仓库已有 gmp/6.3.0、mpfr/4.2.1、mpc/1.3.1 的 Conan 包，但 GCC 14.2.0 官方
> prerequisites 是 6.2.1 / 4.1.0 / 1.2.1，且 GCC 对依赖版本极其敏感；沿用
> `gcc/9.5.0` 的 bundled in-tree 策略，避免与仓库版本精确性差异，也避免交叉
> 编译上下文（build/host/target）下的依赖解析歧义。

## 关键配置选项

| 选项 | 作用 |
|------|------|
| `--target=i686-elf` | 交叉目标；driver 自动加 `i686-elf-` 前缀 |
| `--enable-languages=c,c++` | C + C++ 前端（freestanding 下不构建 libstdc++） |
| `--without-headers` | freestanding target，无标准 C 库头文件 |
| `--disable-bootstrap` | 不三阶段自举，节省构建时间 |
| `--disable-multilib` | 不构建多 ABI 变体 |
| `--disable-shared` | 仅静态库（libgcc 静态） |
| `--disable-threads` | OHOS libc 缺 pthread_cancel（E085），freestanding 用单线程模型 |
| `--without-isl` | 不启用 Graphite 循环优化 |
| `--disable-nls --disable-werror` | 去 i18n；防 clang 告警当错误 |
| `--disable-libssp/libgomp/libitm/libquadmath/libatomic/libsanitizer/libvtv` | 裁剪 freestanding 不需要的运行时库 |
| `--disable-lto --disable-plugin` | 裁剪 LTO/插件 |

## 适配补丁（源码变换脚本，非 git patch）

`files/prepare_ohos_sources.py` 在 `source()` 阶段对源码树做幂等变换：

| # | 变换 | 类别 | 说明 |
|---|------|------|------|
| E072 | config.sub / configfsf.sub 注入 `aarch64-linux-ohos` case | portability | GCC 14.2.0 的 config.sub 是 2021-10-27 版，不认识 ohos；在文件头注入早匹配分支 |
| E011 | 所有 `configure` 脚本 `umask 077`→`umask 022` | portability | 适配 HMDFS 临时目录权限（GCC 顶层 + gmp/mpfr/mpc 各有 2 处） |

> 与 `gcc/9.5.0` 的 prepare 脚本相比，**去掉了 `gcc/config.gcc` 的 ohos 分支和
> `ohos.h` 注入**——因为 target 是 `i686-elf` 而非 `*-linux-ohos`，无需 target 侧适配。

## 宿主侧适配（构建期，从 gcc/9.5.0 + i686-elf-binutils 迁移）

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| E077 | 宿主 ELF 工具无法运行 | HarmonyOS 要求可执行文件签名 | `_write_compiler_wrapper` 包装 clang 自动签名 + `_sign_elf_tree` 遍历签名构建树/产物 |
| — | configure/make 栈溢出 | GCC 生成脚本超出默认 shell 栈 | `_run_with_unlimited_stack`：bash + `ulimit -s unlimited` |
| E074 | make FIFO jobserver 失败 | HMDFS 不支持 FIFO | `make --jobserver-style=pipe` |
| — | AS=llvm-as 覆盖 | OpenDesk 导出 LLVM IR assembler | `AS/LD` 显式指 `/data/service/hnp/bin/as`、`ld`（GNU） |
| — | `-fuse-ld=lld` 污染 `$CC -E` | 宿主 clang 链接选项带入预处理探测 | 依赖 i686-elf-binutils 同款 CPPFLAGS 处理（本轮配方通过 wrapper 规避，见下） |
| — | PIE 默认值 | LLD AArch64 copy-relocation 对齐 | `gcc_cv_c_no_fpie=no gcc_cv_no_pie=no` |

## 目标工具（来自 i686-elf-binutils）

`generate()` 里通过 `self.dependencies["i686-elf-binutils"].package_folder` 解析其 `bin/`，
设置 `AS_FOR_TARGET/LD_FOR_TARGET/AR_FOR_TARGET/RANLIB_FOR_TARGET/NM_FOR_TARGET` 指向
`i686-elf-as/ld/ar/ranlib/nm`，供 `all-target-libgcc` 汇编/链接目标对象。

## test_package

`test_package/test.sh` 用 `i686-elf-gcc` 编译最小 freestanding 程序、`i686-elf-g++` 校验
C++ 前端，再用 `i686-elf-readelf`（Machine=Intel 80386）、`i686-elf-objdump`（反汇编含
`_start`）验证，最后 `-nostdlib -T link.ld` 链接出裸机 ELF 再验 Machine。真实调用交叉
工具二进制（R34）；CI L1e 破坏性测试移走 bin/ 后 test 必失败，证明实质依赖。

## 上游测试

`build()` 末尾运行 `make -C gcc selftest`（GCC 语言无关 + C/C++ 前端内部自测），在宿主
执行，不涉及 target 代码运行。完整 dejagnu `make check-gcc`（数万用例）不适合在单包 CI
窗口内运行，与 `gcc/9.5.0` 的取舍一致。

## 验证（本机前置）

- `python3 -m py_compile` 通过（conanfile.py、prepare_ohos_sources.py、test_package/conanfile.py）。
- 源码 + 依赖 sha256 已实测（见 conandata.yml / manifest）。
- 权威 `conan create`（含 all-gcc + all-target-libgcc + selftest）待真机 shadow CI 执行。

## 版本号策略

首次适配，使用上游版本 `14.2.0`（无后缀）。

## 注意事项（交接）

- `ci/config/build_timeouts.txt` **无** `i686-elf-gcc` 条目（默认 45 分钟）；GCC 交叉构建
  （all-gcc + all-target-libgcc + selftest）大概率超过 45 分钟。需参照
  `arm-none-eabi-binutils/2.46.1` 的 10800s 超时，由 Coordinator/CI 侧决策追加
  `i686-elf-gcc/14.2.0 10800`。此为 CI 基础设施事项，Builder 不修改。

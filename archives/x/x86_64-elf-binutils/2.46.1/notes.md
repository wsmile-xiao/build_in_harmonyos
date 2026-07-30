# x86_64-elf-binutils 2.46.1 适配笔记

## 概述

GNU binutils 配置为**交叉开发工具链**，目标 `x86_64-elf`（裸机 ABI）。产出的
`x86_64-elf-as / x86_64-elf-ld / x86_64-elf-objdump / x86_64-elf-ar / x86_64-elf-nm …`
运行于 HarmonyOS PC (aarch64) 宿主，操作 x86_64 ELF 目标对象；不在宿主执行 x86_64 代码。

与仓库已有的 `binutils/2.46.0`（原生工具链，无 conan 配方）不同，本包：
- 是交叉工具链（`--target=x86_64-elf`）；
- 提供完整 Conan 配方（conanfile.py + conandata.yml + test_package + commands.json）。

## 构建系统 / 编译器

- autotools（`./configure && make`）
- 编译器：clang / clang++（来自 ohos-aarch64 profile，`/data/service/hnp/bin/clang`）
- 无外部依赖（binutils 自包含，内嵌 zlib）

## 关键配置选项

| 选项 | 作用 |
|------|------|
| `--target=x86_64-elf` | 交叉目标；工具自动加 `x86_64-elf-` 前缀 |
| `--enable-static --disable-shared` | 仅静态库，避免 .so 污染、保持自包含 |
| `--disable-gprofng` | gprofng 依赖 Linux `SIGEV_THREAD_ID`，HarmonyOS 不可用 |
| `--disable-gdb --disable-gdbserver --disable-sim` | 裁剪不需要的重型组件 |
| `--disable-nls --disable-werror` | 去 i18n；防止 clang 告警当错误 |

## 适配补丁（15 个）

| # | 补丁 | 类别 | 说明 |
|---|------|------|------|
| E007 | 0001-config.guess.patch | portability | 添加 `__OHOS__`→LIBC=ohos 与 `*:HarmonyOS:*:*`→`<arch>-unknown-linux-ohos` 分支 |
| E011 | 0002~0015-*-configure.patch（14 个） | portability | 各 configure 脚本 `umask 077`→`umask 022`，适配 HMDFS 权限 |

> config.sub：2.46.1 顶层共享的 config.sub 已原生支持 `ohos*` / `linux-ohos*`，故**无需** config.sub 补丁
> （与 2.46.0 不同，2.46.0 需手改 config.sub）。
> 2.46.1 同样只共享 1 个 config.guess / config.sub（顶层），故 E007 仅 1 个补丁。

umask 补丁直接复用 `binutils/2.46.0` 的同名补丁（已验证 14 个全部干净 apply 到 2.46.1）。
`umask 077` 出现在 configure 内显式子壳 `( umask 077 && mktemp -d "./confXXXXXX" )`，无法通过
设父进程 umask 规避，故需改源；这是 HMDFS 真实 worker 才会触发的 E011，本地容器不复现。

## 遇到的问题与对策

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| E007 | config.guess 无法识别 HarmonyOS | GNU config.guess 无 OHOS 分支 | 0001 补丁加 __OHOS__/HarmonyOS 识别 |
| E011 | configure 临时目录权限不足 | HMDFS 下 `umask 077` 建目录权限受限 | 14 个 configure 补丁改 umask 022 |
| gprofng | 编译失败 SIGEV_THREAD_ID 未定义 | Linux 特定信号机制 | `--disable-gprofng` |
| limits.h 等 | libiberty 编译报 LONG_MIN / O_RDONLY / posix_spawn 未定义 | 宿主 clang 把 `-fuse-ld=lld` 带进 `$CC -E` 预处理，stderr 有 "argument unused" 告警，autoconf 旧式预处理模式 header 探测把 stderr 当失败，HAVE_LIMITS_H/FCNTL_H/SPAWN_H 全被误判为 no | build() 内向 CPPFLAGS 追加 `-Wno-unused-command-line-argument`，给探测干净 stderr，header 正确识别 |
| mallinfo | ld/ldmain.c 报 `struct mallinfo2` incomplete type | musl 把 mallinfo/mallinfo2 作为可链接兼容桩提供，但不定义对应 struct；autoconf 仅链接探测误判 HAVE_MALLINFO(_2)=yes | build() 内设 `ac_cv_func_mallinfo=no ac_cv_func_mallinfo2=no`（env 传播到所有子 configure），ld 跳过可选 malloc 统计 |

> 后两项均为 musl/autoconf 兼容问题，对功能无影响：libiberty/ld 仅丢失可选的内存统计。容器内（Alpine musl clang）与真实 OHOS（musl）均适用。


## test_package

`test_package/test.sh` 用 `x86_64-elf-as` 汇编一段最小 x86_64 程序（sys_exit 42），
再用 `x86_64-elf-readelf`（确认 Machine=x86-64）、`x86_64-elf-objdump`（反汇编含 syscall）、
`x86_64-elf-ar`（归档）、`x86_64-elf-nm`（符号）验证。真实调用交叉工具二进制（R34）；
CI L1e 破坏性测试移走 bin/ 后 test 必失败，证明实质依赖。

## 验证

容器 `hmbs-builder` 内 `conan create` + test_package 通过（W3 本地验证）。
产物 `bin/x86_64-elf-{as,ld,ld.gold,objdump,readelf,ar,nm,...}`，均为 aarch64 ELF。

## 版本号策略

首次适配，使用上游版本 `2.46.1`（无后缀）。

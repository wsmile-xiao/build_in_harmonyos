# i686-elf-binutils 2.46.1 适配笔记

## 概述

GNU binutils 配置为**交叉开发工具链**，目标 `i686-elf`（裸机 ABI）。产出的
`i686-elf-as / i686-elf-ld / i686-elf-objdump / i686-elf-ar / i686-elf-nm …`
运行于 HarmonyOS PC (aarch64) 宿主，操作 i686 ELF 目标对象；不在宿主执行 i686 代码。

与仓库已有的 `binutils/2.46.0`（原生工具链，无 conan 配方）不同，本包：
- 是交叉工具链（`--target=i686-elf`）；
- 提供完整 Conan 配方（conanfile.py + conandata.yml + test_package + commands.json）。

## 构建系统 / 编译器

- autotools（`./configure && make`）
- 编译器：clang / clang++（来自 ohos-aarch64 profile，`/data/service/hnp/bin/clang`）
- 无外部依赖（binutils 自包含，内嵌 zlib）

## 关键配置选项

| 选项 | 作用 |
|------|------|
| `--target=i686-elf` | 交叉目标；工具自动加 `i686-elf-` 前缀 |
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

`test_package/test.sh` 用 `i686-elf-as` 汇编一段最小 i686 程序（sys_exit 42），
再用 `i686-elf-readelf`（确认 Machine=Intel 80386）、`i686-elf-objdump`（反汇编含 int 0x80）、
`i686-elf-ar`（归档）、`i686-elf-nm`（符号）验证。真实调用交叉工具二进制（R34）；
CI L1e 破坏性测试移走 bin/ 后 test 必失败，证明实质依赖。

## 验证

容器 `hmbs-builder` 内 `conan create` + test_package 通过（W3 本地验证）。
产物 `bin/i686-elf-{as,ld,ld.gold,objdump,readelf,ar,nm,...}`，均为 aarch64 ELF。

## 版本号策略

首次适配，使用上游版本 `2.46.1`（无后缀）。

## Round-2：接线上游完整测试链（DejaGNU make check）

### 决策
用户选择方案 C（progress.json `ud-i686-elf-binutils-20260823-005519`）：
dejagnu/1.6.3 已合入官方基线，继续走完整上游测试路线（379 .exp 全量运行）。

### 变更（均在候选目录内）
1. `conanfile.py`
   - 新增 `build_requirements()`：`tool_requires("dejagnu/1.6.3")`、
     `tool_requires("expect/5.45.4")`、`tool_requires("tcl/8.6.14")`。
     expect/tcl 按 Conan 惯例直连声明，便于在 `generate()` 解析 package_folder
     （Conan 不暴露传递依赖的 package_folder），用于设置 TCL_LIBRARY / LD_LIBRARY_PATH
     （官方 dejagnu 配方同款模式）。
   - `generate()`：生成 build 作用域 `i686_elf_check_env.sh`，向 PATH 前置
     expect/bin，设 `LD_LIBRARY_PATH=<tcl>/lib`、`TCL_LIBRARY=<tcl>/lib/tcl8.6`。
   - `export_sources()`：额外导出 `site-stty-fix.exp` 与 `tmpfile-shim.c`。
   - `build()` 末尾集成上游 `make check`：
     `DEJAGNU=<build>/site-stty-fix.exp LD_PRELOAD=<build>/tmpfile-shim.so make -k -j1 check`，
     在 `self.build_folder`（out-of-tree）运行，env 用 `conanbuild + i686_elf_check_env`。
   - tmpfile-shim.so 用 profile 的 `tools.build:compiler_executables`（clang）编译：
     `clang -shared -fPIC tmpfile-shim.c -o tmpfile-shim.so`。
2. 新增 `site-stty-fix.exp`、`tmpfile-shim.c`：与 arm-none-eabi-binutils 2.46.1
   逐字节一致（sha256 已核验），属测试环境兼容文件，非新增上游测试用例。
3. `test_package/MANIFEST.yml`：`upstream_test_in_build: true`，声明完整测试命令与
   5 个 runner（gas 145 / ld 187 / binutils 37 / libctf 6 / libsframe 4 = 379 .exp）。
4. `manifest.yaml`：build.dependencies 列出三个 tool_requires（官方基线），notes 更新。

### 预检证据（本协议 round-2，见 reports/builder/round-2.md）
- `python3 -m py_compile`（conanfile.py、test_package/conanfile.py）通过。
- `conan graph info`：dejagnu/1.6.3、expect/5.45.4、tcl/8.6.14 全部 Cache 命中
  （含 OHOS armv8 二进制），不触发任何新构建；zlib/1.3.1（expect 传递依赖）Cache 命中。
- 运行环境 smoke：`runtest --version` → DejaGnu 1.6.3 / Expect 5.45.4 / Tcl 8.6；
  `expect -c "source site-stty-fix.exp; puts OK"` → SITE-FIX 注入成功。
- tmpfile-shim 设备探针：无 shim 时 `tmpfile: Permission denied`（复现 OHOS libc EACCES）；
  `LD_PRELOAD=tmpfile-shim.so` 后 `TMPFILE_OK`（恢复 POSIX 语义）。

### 未在本轮执行（权威 CI 专属，交 authoritative-ci 轮）
- 完整 `conan create`（含 379 .exp make check）未运行；提交前预检结果不得视为权威 PASS。
- 注意：`ci/config/build_timeouts.txt` 无 i686-elf-binutils 条目（默认 45 分钟）。
  arm-none-eabi-binutils/2.46.1 使用 10800s 超时；若 make check 使构建接近/超过
  45 分钟，权威 CI 可能超时。此为 CI 基础设施事项，需 Coordinator 决策，Builder 不修改。

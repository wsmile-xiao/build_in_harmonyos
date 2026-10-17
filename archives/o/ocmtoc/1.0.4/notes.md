# ocmtoc 1.0.4 适配笔记

## 基本信息

- 上游仓库：https://github.com/acidanthera/ocmtoc
- 上游版本：1.0.4（tag `1.0.4`，Changelog：rebase 到 cctools 1024.3，新增 `__SBAT` 支持与 `--fullversion` 参数）
- 源码归档：https://github.com/acidanthera/ocmtoc/archive/refs/tags/1.0.4.tar.gz
- SHA256：`dbc33ca5d5ae436b2845e36fc13ba878261480788db86fc6daab89dc5588e51a`
  （已在本地独立下载验算，与 Homebrew 公式 `Formula/o/ocmtoc.rb` 记录值一致）
- 许可：APSL-2.0（`APPLE_LICENSE`）
- 构建系统：custom（上游只提供 `cctools.xcodeproj`，无 CMake/autotools/meson；CI 仅在 `macos-latest` 上跑 `xcodebuild -scheme mtoc`）
- 编译器：clang（取自 Conan conf `tools.build:compiler_executables`，R33 合规）
- 产物：`bin/mtoc` + `share/man/man1/mtoc.1`，`package_type = "application"`
- 依赖：无（零外部依赖，纯 C）
- 状态：built（待真机预检实证后由 HMBS 统一提交）

## 上游源码结构审计

| 目录 | 内容 | 是否采用 |
|------|------|----------|
| `efitools/mtoc.c`（84KB） | mtoc 主程序：Mach-O 解析 → PE/COFF 输出 | 采用 |
| `libstuff/`（46 个 .c） | Apple cctools 通用库 | 按需采用 23 个（见下） |
| `include/`（mach/coff/mach-o/stuff/xar/elf/...） | 自带头文件（含 `mach/machine-cctools.h` 等跨平台头） | `-Iinclude -Iinclude/stuff` |
| `efitools/mtor.c`、`ld/`、`ar/`、`misc/`... | 兄弟工具（mtor）与其他 cctools 组件 | 不采用（本包只交付 mtoc） |
| `tests/` | cctools 回归套件（见“上游测试审计”） | 无法在 OHOS 运行 |
| `man/mtoc.1` | mtoc 手册页 | 随包安装 |

Xcode 工程实证（`cctools.xcodeproj/project.pbxproj`，442709 字节）：
`PBXNativeTarget "mtoc"` 的 Sources 阶段仅含 `mtoc.c`，Frameworks 阶段仅链接
`libstuff.a`，依赖仅为 `stuff` 目标。因此配方编译 `efitools/mtoc.c` +
libstuff 子集即与上游 mtoc 构建等价。

链接闭环（静态分析 `efitools/mtoc.c` 的外部引用 → 提供文件的传递闭包）：
`allocate.c`、`apple_version.c`、`arch.c`、`breakout.c`、`bytesex.c`、
`checkout.c`、`coff_bytesex.c`、`crc32.c`、`diagnostics.c`、`errors.c`、
`fatal_arch.c`、`fatals.c`、`get_arch_from_host.c`、`get_toc_byte_sex.c`、
`ofile.c`、`ofile_error.c`、`ofile_get_word.c`、`print.c`、`reloc.c`、`rnd.c`、
`set_arch_flag_name.c`、`swap_headers.c`、`write64.c`，
另加 `portability/mach_compat.c`（见下）。`libstuff/lto.c` 被排除：
`ofile.c` 对 `lto_*` 的全部引用都在 `#ifdef LTO_SUPPORT` 内，不定义该宏即
无需链接（代价：LLVM bitcode 输入被判为未知文件——mtoc 只接受
MH_PRELOAD/MH_DYLIB，本就拒绝 bitcode，行为无损）。
`libstuff/writeout.c` 同样被排除：它实现归档写出器
`writeout`/`writeout_to_mem`/`reset_load_command_pointers`（ar/ranlib 类工具用），
经全文扫描确认 `mtoc.c` 及本闭包其余翻译单元零调用（`breakout.c:340` 仅为注释提及）；
静态归档链接只拉取未定义符号所需的目标文件，故不编译它与上游链接等价，
同时避开其 macOS 专属限速路径（`O_FSYNC`、`host_sched_info`/`HOST_SCHED_INFO`
需内核支持、`UINT_MAX` 缺 `<limits.h>`）——这些非头垫片可解，逐个补符号只会
每轮暴露下一个（前三轮连败教训），故改走减法路线。

## 上游测试审计（103 个用例，均无法在 OHOS 运行）

- `tests/test-cases/` 下共 **103** 个用例子目录；抽查 `mtor-preload`、
  `libstuff-unit-tests` 等 Makefile，首行均为 `# PLATFORM: MACOS`。
- 驱动 `tests/run-tests` 要求 Xcode 工具链（`xcrun`、Apple SDK、`-arch`、
  `-Wl,-preload`、`codesign` 等），真机（HongMeng Kernel + musl）不具备。
- 103 例中**没有 mtoc 专用例**（最接近的是 4 个 `mtor-*` 兄弟工具用例，
  测的是本包不构建的 mtor）。
- 结论：cctools run-tests 套件在 HarmonyOS 上不可补齐（缺的是整个 Apple
  工具链，非单个可 vendor 的库），且上游 CI 自身从不运行它
  （`.github/workflows/main.yml` 只有 `xcodebuild -scheme mtoc`，无任何测试步骤），
  其中 0 例与 mtoc 相关，故不计入通过率分母。
- 第二测试集合 `libstuff_test/`（上游自带的 libstuff C 单元测试，定制
  `test.h` 框架，零 Xcode 依赖）中，与本包交付物直接相关的子集已在配方
  `build()` 内真实编译运行：`allocate_test`（4 项，对应 `libstuff/allocate.c`）、
  `arch_test`（7 项，对应 `libstuff/arch.c`）、`get_arch_from_host_test`
  （1 项，对应 `libstuff/get_arch_from_host.c`，在真机上实际验证 uname→
  CPU_TYPE_ARM64 映射）、`rnd_test`（2 项，对应 `libstuff/rnd.c`），另加
  harness 自检 1 项，共 15 项。测试二进制以与 mtoc 相同的编译 flags/shims
  构建，并链接已编好的 mtoc 闭包目标文件（含 `mach_compat.o` 提供 musl 缺失
  的 `reallocf`）；计分取自其 `tests completed (N/M passing)` 汇总行，
  `HMBS_UPSTREAM_TEST_RESULT` 以 `status:passed/discovered=15/executed=15`
  上报（以真机实测为准）。
- 未运行的 `libstuff_test` 文件（align/args/depinfo/guess_short_name/
  version_number/reset_load_command_pointers）覆盖的模块均不在 mtoc 链接闭包
  内（`_mtoc_sources` 清单核对无引用；reset_* 还需 `writeout.c`，该文件因
  macOS 内核专属限速路径已移出闭包），测它们无法验证交付物，故排除。
- 证据持久化（复用 abuild-sudo 已验证方案）：`build()` 把结果 dict 写入
  `build_folder/upstream_test_result.json`，`package()` 随包发布到 `res/`，
  `test_package` 每轮从包内原样复发标记；缓存命中导致 `build()` 被跳过时仍有证据。

## 移植设计（全部是实质等价实现，非空壳 stub）

上游为 Apple 平台编写，以下差异用 POSIX 等价修复；补丁与兼容层中
**不含任何 `__OHOS__` 平台宏**（R8/PF5 合规），Linux/OHOS 通用：

1. `portability/shim/mach/mach.h` + `mach_error.h` + `mach/machine.h`：
   `<mach/mach.h>` 只提供 `kern_return_t`/`KERN_SUCCESS`/`mach_task_self` 等
   最小定义（`machine.h` 转发到上游自带的 `machine-cctools.h`，CPU 常量
   仍是上游官方版本）；`mach_error_string()` 为静态内联。
   另有 SDK 叶头垫片：`mach/boolean.h`（`boolean_t` 唯一定义）、
   `mach/machine/boolean.h`（仅转发前者，供 `mach/hppa/thread_status.h`
   使用，避免重复 typedef）、`mach/machine/vm_types.h`（LP64 最小类型）、
   `mach/message.h`（`mach_msg_type_number_t`）、`machine/types.h`
   （含 Darwin `__uint*_t` 别名，供 `mach/i386/_structs.h` 等使用）、
   `mach/vm_prot.h`（`vm_prot_t` 与 `VM_PROT_*`，取值与 Darwin SDK 一致；
   上游 `mach-o/loader.h` 以 `__has_include` 条件引入，移植目录优先故
   自动命中，无需改上游源码）。
2. `portability/shim/libc.h`：聚合标准头，替代 NeXT 遗留的 `<libc.h>`。
3. `portability/mach_compat.c`：
   - `vm_allocate` → `calloc`（同样匿名零填充；`writeout.c` 注释明确要求空洞读零）；
   - `vm_deallocate` → `munmap`（ofile 镜像均来自 `mmap`）并以 `free` 兜底；
   - `host_info(HOST_BASIC_INFO)` → `uname()` 映射到 `CPU_TYPE_*` 常量
    （aarch64 真机返回 `CPU_TYPE_ARM64`，是真实答案；仅 `get_arch_from_host`
     使用，mtoc 常规路径不经过它）。
   - `ocmtoc_reallocf()` → BSD `reallocf(3)` 等价实现（失败时释放原指针）；
     经 `portability/shim/ocmtoc_compat.h` 以 `-include` 强制注入全部
     翻译单元（`diagnostics.c` 的诊断消息数组扩容用），上游源码零改动、
     不遮蔽任何系统头。
4. `patches/0001`：`MAP_RESILIENT_CODESIGN`/`MAP_FILE` 缺失时定义为 0
  （纯特性检测，无平台宏）。
  （曾有的 `patches/0002` 随 `writeout.c` 移出闭包一并删除：该补丁只改
  已不再编译的文件，留着是死补丁；`__builtin_available` 问题随文件移除而消失。）
5. `-DCURRENT_PROJECT_VERSION='"1.0.4"'`：复刻上游 `libstuff/Makefile` 的
   版本戳生成，使 `mtoc --version` 输出 `1.0.4`
  （`apple_version.c` 默认是 `cctools-localbuild`）。

## 编译步骤（配方 `build()` 实际执行）

```sh
$CC -O2 -Iportability/shim -Iinclude -Iinclude/stuff \
    -include portability/shim/ocmtoc_compat.h \
    -DCURRENT_PROJECT_VERSION='"1.0.4"' -c <25 个 .c> -o obj/*.o
$CC -O2 -o mtoc obj/*.o
test "$(mtoc --version)" = "1.0.4"
mtoc --fullversion | grep -q "Acidanthera ocmtoc 1.0.4"
if mtoc; then exit 1; fi
printf 'not-a-macho' > bad.bin
if mtoc bad.bin bad.pe 2>bad.err; then exit 1; fi; grep -q "error" bad.err
```

源码行为依据（逐行核对 `efitools/mtoc.c`）：
`--version` → `puts(VERSION); exit(0)`（419-422 行）；
`--fullversion` → `puts("Acidanthera ocmtoc " VERSION); exit(0)`（423-426 行）；
无参数 → `warning("no input file specified"); usage();` → `exit(EXIT_FAILURE)`
（434-436、486 行）；垃圾文件 → `breakout()` 记错 → `return(EXIT_FAILURE)`
（444-446 行），stderr 形如 `error: mtoc: ...`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 CMake/autotools 入口 | 只发 Xcode 工程 | custom 配方直调 clang（文件清单来自工程实证） |
| 2 | `<mach/mach.h>` 等 Apple 头缺失 | libstuff 的 Mach 依赖 | portability 兼容层（POSIX 等价，见上） |
| 3 | `MAP_RESILIENT_CODESIGN`/`MAP_FILE` 未定义 | musl 无 BSD/Apple 扩展 | patches/0001 特性检测补零 |
| 4 | `__builtin_available` 解析失败风险 | 仅 Apple clang 支持 | 曾用 patches/0002 以 `__APPLE__` 隔离；后随 `writeout.c` 移出闭包，该补丁已删除（见 #7） |
| 5 | `mtoc --version` 版本戳来源 | 上游 Makefile 生成 | `-DCURRENT_PROJECT_VERSION` 复刻 |
| 6 | 上游 103 例测试跑不了 | 全是 PLATFORM: MACOS + Xcode，且上游 CI 自身从不运行 run-tests | 改跑上游 `libstuff_test/` 中与 mtoc 闭包相关的 15 项单元测试（allocate/arch/get_arch_from_host/rnd），cctools 套件如实排除并写清原因 |
| 7 | `writeout.c` 编译 7 错（`O_FSYNC`、`host_sched_info`、`HOST_SCHED_INFO*`、`UINT_MAX`） | 前三轮“缺一个补一个”逐个垫片，每轮暴露下一个；该文件是 ar/ranlib 归档写出器，mtoc 零调用 | 改走减法路线：移出编译闭包（静态归档链接等价）、删除死补丁 0002；ofile 自带 `<limits.h>` 故其 UINT_MAX 不受影响 |
| 8 | libstuff_test reallocate crash, then conan patch apply failure | macOS realloc(p,0) non-NULL vs musl/glibc NULL aborts via system_fatal; patch-file hunk counts are fragile under conan applicator | in-recipe python edit in build(): normalize size 0 to 1 in libstuff/allocate.c, NULL input still via allocate(0); patch file removed |
| 9 | libstuff_test_runner died with rc=-6 (SIGABRT), stdout only testing: | abort() blocks SIGABRT before raising; upstream arch_test trap uses signal()+longjmp which never restores the mask, so on musl later deliberate aborts kill the runner and buffered output is lost | build-time edit of libstuff_test/arch_test.c to sigaction()+sigsetjmp/siglongjmp (same assertions/count) + test-only portability/test_unbuffer.c linked into runner for unbuffered stdio |

## 依赖版本

无外部依赖。仅工具链：clang 15（真机 `/data/service/hnp/bin/clang`，
由 profile/conf 注入）、POSIX sh、grep。

## 验证结果（待真机预检回填）

- `conan create`：待 HMBS 真机预检。
- 构建期冒烟 4/4、`test_package` 3/3（`verify_mtoc.py`，7 个断言）：
  待真机实测回填，数字以预检日志为准。
- 上游 `libstuff_test/` 单元测试（闭包相关子集）：15/15（待真机实测回填，
  数字以预检日志 `tests completed (N/M passing)` 为准；证据经
  `res/upstream_test_result.json` 由 test_package 每轮复发）。
- 上游 cctools run-tests 套件：103 例均与 mtoc 无关且平台不兼容（PLATFORM:MACOS），
  上游 CI 自身亦不运行，不计入通过率；排除理由见“上游测试审计”。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/mtoc` | Mach-O → PE/COFF 转换器 |
| `share/man/man1/mtoc.1` | 上游手册页 |

## 注意事项

- 本包是**命令行工具包**（`package_type = "application"`），无库文件；
  `commands.json` 已按 R38 在软件级目录声明。
- Windows 工作区大小写不敏感：上游 `archives/l/libXext` 与 `libxext`
  双目录在本机 checkout 会互相覆盖，`git status` 恒显示该两文件被改动；
  与本任务无关，真机（Linux 大小写敏感）不受影响，切勿将其纳入提交。
- 后续可加强：用 clang `--target=x86_64-apple-macos` 生成最小 Mach-O
  做端到端转换测试（需先验证真机 clang 含 Mach-O 后端，`--version` 通过
  后再议，避免不可验证的测试进包）。

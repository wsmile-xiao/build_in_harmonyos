# gcc-snapshot 20260705 HarmonyOS 前置适配草稿

- **草稿 ID**: DRAFT-gcc-snapshot-20260705-ohos-source-tree-and-fresh-build
- **来源**: gcc-snapshot/20260705 真机前置适配与 fresh build 验证
- **分类**: toolchain / autotools / source-extract / ohos-platform / bundled-prerequisites
- **状态**: 本地草稿（未创建 Issue/PR，未生成知识编号，无远端链接，无审核结论）
- **源码 URL**: `https://gcc.gnu.org/pub/gcc/snapshots/17-20260705/gcc-17-20260705.tar.xz`
- **源码语言**: C / C++

## 范围

GCC snapshot 不是普通第三方库，而是一个自举型工具链包。它同时包含：

- 主体源码：`gcc-17-20260705.tar.xz`
- 内建前置：`gmp-6.3.0`、`mpfr-4.2.2`、`mpc-1.3.1`
- 构建期生成器：`flex/2.6.4`

在 HarmonyOS PC 上，它的前置适配重点不是“能否编译一个库”，而是“能否把生成器、源码树、shell、sysroot、HMDFS 这些约束一起跑通”。

## 关键现象

1. 直接下载 GCC snapshot 源码到设备上太慢，真机阶段会把时间耗在大 tarball 传输上。
2. Conan `source()` 不能依赖 `self.settings`，因此不能在 source 阶段按 OHOS 分支做 settings 访问。
3. GCC snapshot 没有预生成的 `gcc/gengtype-lex.cc`，所以 `flex` 必须作为 `tool_requires` 前置进来。
4. 真机上 HMDFS、只读 `/tmp`、脚本直接 exec、工作目录恢复等问题会同时出现，必须把环境和入口统一收口。
5. 这一版 `gcc/Makefile.in` 的 `FLEX` 变量已经是 `@FLEX@`，不需要再强行替换成固定 `flex`。
6. `generate()` 里的编译器探测不能依赖裸 `clang`；真机设备上的默认值要直接落到 `/data/service/hnp/bin/clang` 和 `/data/service/hnp/bin/clang++`。
7. Conan 的 `tool_requires("flex/2.6.4")` 只说明依赖被安装，不代表它一定出现在 GCC 子构建的 `PATH` 里；这轮补了显式 `FLEX` 和 `PATH` 注入。
8. 即使配置了 `--disable-lto`，GCC snapshot 的生成选项表和 LTO 相关源文件仍可能保留 LTO-only option code；需要同步清理 `LangEnabledBy ... LTO` 语言启用关系，并在 LTO/GCC option consumers 中做禁用分支保护。
9. 目标端 option-completion selftest 的选项集合不是所有目标平台都适用；本次 AArch64 OHOS 构建中，`-Wno-underflow`、`-Wtarget-lifetime`、`-Warray-temporaries` 会把平台差异错误地升级为编译器 selftest 失败，因此在源码变换阶段删除这些明确不适用的条目。
10. OHOS 上构建树里的 `gcc/as` 可能是 shell 脚本而非可直接 `posix_spawn` 的 ELF；目标编译器 wrapper 必须先添加 `-B/data/service/hnp/bin/`，再添加构建树 `-B`，这样 xgcc 会使用设备 GNU Binutils 2.45 的 `as`/`ld`。
11. AArch64 OHOS 目标编译至少需要显式 `-isystem <ohos-sdk>/native/sysroot/usr/include/aarch64-linux-ohos`，并通过 shell wrapper 传递 `-D__availability__(...)=`，以跳过 GCC 无法解析的 Clang dotted availability annotation。
12. `libgcc/Makefile.in` 的 `mkheader.sh` 即使文件权限正常，也可能因 HMDFS direct exec 策略失败；将命令改为 `$(SHELL) $(srcdir)/mkheader.sh` 后，目标运行库配置和头文件生成可以继续进行。
13. 安装 wrapper 不能假设 Conan snapshot 日期就是 GCC 的内部安装版本；应从 `gcc.real -dumpversion` 取得 `17.0.0`，否则 `-B<package>/lib/gcc/...` 会指向不存在的目录。
14. `collect2` 的调试输出显示它可能直接选择 `gcc/collect-ld`，而不是 `-B` 路径中的 `ld`；HMDFS 下对受保护 HNP linker 的 direct `posix_spawnp` 会返回 `Permission denied`。因此需要构建一个 signed ELF launcher，通过 `/system/bin/sh` 转调 `/data/service/hnp/bin/ld`，并同时提供 `ld`、`collect-ld`、`real-ld` 三个别名。
15. CI 源码下载不能只验证官方 URL 在开发机可用：99.6 MB 长连接可能在 worker 上断流，且预下载工具可能缺少 `curl`。Conan `download()`/`get()` 支持有序 URL 列表，应保留官方源和经过同一 SHA256 校验的 Sourceware 镜像，先走 worker 可达镜像、官方源作兜底。
16. 仅有 URL 回退仍不能处理“连接保持建立但持续低速”的情况：Conan 会继续等待首个 URL，直到 CI 固定的 3600 秒窗口耗尽。对于确认支持 HTTP Range 的公开源，应将大包拆成有限大小的分块并行获取，每块有限重试，按序合并后再做一次完整 SHA256 校验。
17. Conan 的 `build_jobs()` 在 OHOS profile 未配置处理器检测时会返回 1，表面上设置“最多两路”仍会退化成串行编译；已在 OHOS 上明确启用 `make --jobserver-style=pipe` 并设置并发下界，避免 GCC 自举退化为串行。
18. 固定总超时要按阶段边界诊断：#44912 已完成 `all-gcc` 和 7,676,387 项 selftest，并在 `all-target-libgcc` 收尾处耗尽 3600 秒，说明 `-j2` 仍不足以覆盖受限 profile 的整条构建链。此时可以在已确认的 AArch64 资源范围内把 OHOS 上限提高到 `-j4`，保留 pipe jobserver、内存余量和非 OHOS 较低上限；不能把 generic timeout 诊断误写成交互式测试失败。
19. #44956 已重复验证 `-j4` 仍在 `all-target-libgcc` 收尾处触发同一固定超时，说明继续提升 make 并发不是唯一方向。对于明确限定为 C frontend + static libgcc 的 OHOS 产品，可以关闭 decimal-float runtime，并在 target libgcc 命令行使用 `-O2 -fPIC` 去掉继承的调试标志；这是缩小已声明产品边界和编译输入，不是跳过 libgcc 或伪造测试通过。
20. #44992 的耗时较 #44956 缩短 193 秒，且 decimal/BID 对象已退出，但日志仍显示 `-g`；GCC `libgcc/Makefile.in` 的 `LIBGCC2_DEBUG_CFLAGS` 会覆盖普通 target flags，因此必须显式传 `LIBGCC2_DEBUG_CFLAGS=-g0`，仅设置 `CFLAGS_FOR_TARGET` 不足以移除 libgcc 调试 I/O。随后 PR CI #45033 验证该覆盖可以越过 `all-target-libgcc` 超时边界并完成 `test_package`。

## 根因

- GCC snapshot 的 `download_prerequisites` 体系天然依赖 bundled GMP/MPFR/MPC，不能简单改成外部 Conan requires，否则会改变工具链边界。
- `source()` 里如果读取 `self.settings`，Conan 会直接报错；OHOS 专用转换必须放到 settings 无关的路径里。
- GCC 的生成器链条依赖 `flex`，而不是只靠上游源码树本身；没有 `flex` 时 generator 阶段会卡在 lexer 生成。
- HarmonyOS 上的 shell/执行权限和 HMDFS 约束会让 `configure`、`move-if-change`、`get_patches.sh` 这类脚本调用出现“看起来有权限、实际不能直 exec”的问题。
- `collect2` 不是只看最终用户传入的 `ld`；它会按 GCC 构建目录优先级解析 `collect-ld`。只添加 shell wrapper 或只添加 `ld` 别名都不足以覆盖该路径，launcher 必须是真正可被 `posix_spawnp` 的签名 ELF。
- 大源包的网络失败可能不是立即断流，而是单个 HTTP 连接长期低速；这时有序镜像列表不会及时切换，外层 3600 秒 timeout 会把网络问题归类成构建超时。需要在包自身的 `source()` 阶段做分块、并行、重试和最终校验。
- OHOS profile 没有 `tools.build:jobs` 时，Conan `build_jobs()` 安全返回 1；如果 recipe 只做上限限制，GCC 会串行构建，在源码下载和真机 HMDFS 操作占用时间后容易耗尽 3600 秒窗口。

## 已采用方案

- `config_options()` 里移除 `os.version`。
- `source()` 支持 `GCC_SNAPSHOT_SOURCE_TARBALL` 本地源包回退，优先复用已经落到设备上的 tarball。
- 源码解包后仅保留必要主干和 bundled prerequisite，避免把完整 testsuite 复制到后续环节。
- `prepare_ohos_sources.py` 作为短生命周期进程执行，避免 Conan 进程残留状态影响后续 configure。
- `flex/2.6.4` 作为 `tool_requires` 单独适配，不混入 gcc-snapshot 主库 PR。
- `gcc/Makefile.in` 不再强改 `FLEX` 行，只保留 shell 兼容和 checksum / move-if-change 修复。
- `generate()` 的编译器默认值显式使用 `/data/service/hnp/bin/clang` 与 `/data/service/hnp/bin/clang++`，避免 Conan 环境 PATH 差异。
- `generate()` 里显式从 Conan build dependency 取出 `flex` 可执行文件，并把 `FLEX` / `LEX` 与 `PATH` 一起注入给 GCC 构建。
- 真机前置命令要显式设置 `TMPDIR`、`CONFIG_SHELL`、`SHELL`，并对必要脚本入口用 shell 包一层。
- 对禁用 LTO 的生成选项、LTO wrapper/driver/option source 做兼容保护，并过滤目标端 option-completion selftest 中明确不适用的三项。
- 目标端使用 `/data/service/hnp/bin/` 优先的 `-B` 顺序、OHOS AArch64 sysroot 和 shell wrapper，避免构建树脚本被当成 assembler 直接执行。
- 安装后的 relocatable `bin/gcc` wrapper 也要把 `/data/service/hnp/bin/` 放在其余 `-B` 路径之前，否则包消费阶段仍会复现 `as: posix_spawnp: Permission denied`。
- 在构建期生成一个最小 signed ELF linker launcher，并把相同 launcher 复制为 `ld`、`collect-ld`、`real-ld`；安装包内也保留这些别名，同时将 package `bin` 放进 wrapper 的最高优先级 `-B` 搜索路径。
- GCC 主 tarball 不再依赖单个长 HTTP 连接：先读取 `Content-Length`，按 4 MiB 分块最多 8 路并行下载，每块重试 3 次，合并时校验完整 SHA256；URL 按顺序回退，未改变官方校验值。
- OHOS 构建在 `build_jobs()` 返回 1 的默认 profile 下显式采用 `make --jobserver-style=pipe`，并将已确认资源范围内的并发上限设为 4；不修改 CI 全局 timeout，也不把并发扩大到设备核数，同时避免源码下载、配置和串行自举共同耗尽 CI 时间窗。
- OHOS 产品边界显式使用 `--disable-decimal-float`；`all-target-libgcc` 通过命令行 `CFLAGS_FOR_TARGET=-O2 -fPIC`、`CXXFLAGS_FOR_TARGET=-O2 -fPIC` 和 `LIBGCC2_DEBUG_CFLAGS=-g0` 构建，避免把 profile 与 libgcc Makefile 的 debug flags 复制到大量 target runtime 对象。

## 验证状态

- 设备侧源码树已经成功展开，`gcc`、`gmp`、`mpfr`、`mpc`、`libiberty`、`fixincludes` 目录均可见。
- `flex/2.6.4` 已在独立库中完成前置适配并通过 test_package。
- `gcc-snapshot` 的真机 fresh build 已完成 `all-gcc`、C frontend selftest 和 `all-target-libgcc`；C frontend selftest 通过 `7,676,387` 项，安装后的包 wrapper 已完成最小 AArch64 consumer 验证，torture 子集 `100/100` 通过。
- 2026-09-11 官方 runner R4 在 `10.62.229.155:2222` 完成完整 `conan create`、安装包 `test_package` 和 shadow CI 分层检查；L0/L1/L2/L4/L5 全部通过，100/100 torture 通过，`test_package` 输出 `gcc17-ohos-ok`，runner 退出码为 `0`。
- PR CI `#44812` 在 L0 通过后因 GCC 99.6 MB 源包单连接下载在 3600 秒内未完成而超时，未进入编译或 `test_package`；并行 Range 下载器已在本机临时 HTTP Range 服务上验证分块、URL 回退和 SHA256 合并逻辑，待真机 CI 复跑。
- PR CI `#44864` 通过了前置步骤并进入 GCC 自举，日志已打印 `7,676,387 pass(es)`，但因 OHOS profile 的 `build_jobs()` 退化为串行，`conan create` 在 3600 秒窗口内未完成 `all-gcc` 后续阶段；未产生新的编译错误或测试断言失败。
- PR CI `#44912` 已验证上一轮 `-j2` 和源码缓存兼容路径可以继续推进，日志完成 `all-gcc` selftest，并在 `all-target-libgcc` 的收尾处触发 `conan create TIMED OUT after 3600s`；package、安装包签名、test_package、L1/L2/L4/L5 均未执行。这仍是构建时间窗不足，不是上游测试断言失败；当前配方已把 OHOS pipe 并发上限提升为 `-j4`。
- PR CI `#44956` 已确认 `-j4` 仍在同一个 `all-target-libgcc` 收尾边界超时；#44992 应用 decimal-float 和 target `-O2 -fPIC` 后缩短 193 秒但仍超时，说明 libgcc Makefile 的 debug flags 还在生效。随后通过 `LIBGCC2_DEBUG_CFLAGS=-g0` 完成修复。
- PR CI `#45033` 已通过：`conan-build-test` 用时 3562 秒、总耗时 3647 秒，Conan `test_package`、L0、L1 和全部构建步骤成功；这只确认当前声明的 C frontend + static libgcc 交付边界，不代表未执行测试矩阵全部通过。

## 可复用结论

- 适合所有“自带 prerequisite + 需要生成器 + 真机 HMDFS 约束”的大工具链包。
- 适合在 Conan `source()` / `build()` 之间严格分层的项目。
- 适合需要把下载风险从真机链路上移除的超大源包。
- 适合记录“禁用一个可选子系统仍需同步修补生成代码/源文件”的大型 autotools 工具链。
- 适合记录目标平台工具搜索路径、脚本执行策略、sysroot 头文件和 ELF 签名同时影响编译器自举的场景。
- 适合记录 snapshot 包版本与上游内部安装版本不同、需要 relocatable driver 运行时解析的场景。
- 适合记录 GCC `collect2` 选择 `collect-ld`、而目标平台对直接 spawn 受保护 linker 有额外限制的场景。
- 适合记录大源包在固定 CI 时间窗内的低速长连接问题，以及不修改 CI 基础设施时的 Range 并行下载方案。
- 适合记录 Conan 默认 jobs 探测在受限 OHOS profile 下退化为串行、需要按阶段耗时选择有上限的 pipe 并发以满足固定 CI 时间窗的场景。
- 适合记录工具链 recipe 在保持 C compiler 和普通 static libgcc 交付的前提下，通过显式关闭 decimal-float 和 target-only 优化参数控制构建成本的场景。
- 适合记录 GCC 子 Makefile 的专用调试变量覆盖普通 `CFLAGS_FOR_TARGET`、导致大型 target runtime 仍保留 `-g` 的场景。

## 可迁移知识条目

下面的条目按“触发条件、根因、处理方式、验证方式、不要这样做”的口径整理，适用于其他需要在 HarmonyOS PC / HMDFS 上构建的大型 autotools、编译器和自举工具链项目。

### 1. source 阶段不要读取 settings

- **触发条件**：Conan recipe 的 `source()` 需要根据平台选择补丁、源包或解包路径。
- **根因**：Conan 的 `source()` 生命周期早于完整 settings 注入，在该阶段读取 `self.settings` 会直接报 `self.settings access in source() method is forbidden`。
- **处理方式**：把源码下载、SHA256 校验、tarball 解包和与平台无关的源码清理放在 `source()`；需要 OHOS 的变换改为 settings-independent 的幂等操作，或延迟到 `generate()` / `build()`。
- **验证方式**：用普通 profile、OHOS host profile 和本地源包三种入口分别执行 source，确认不会因为 settings 缺项提前失败。
- **不要这样做**：不要在 `source()` 里写 `if str(self.settings.os) == "OHOS"`，也不要把同一组变换重复放进 source 和 build，避免二次替换破坏上游文本。

### 2. 大源包使用本地 tarball 回退和 no-copy-source

- **触发条件**：GCC、LLVM 或大型 SDK 源包在真机上下载慢，或者 Conan 把源码树复制到 build folder 的成本过高。
- **处理方式**：保留官方 URL 和固定 SHA256 作为默认来源，同时提供 `GCC_SNAPSHOT_SOURCE_TARBALL` 这类显式环境变量回退；使用 `no_copy_source = True`，并在 source 阶段只保留构建需要的目录。
- **裁剪边界**：本次保留 `gcc` 主树、bundled GMP/MPFR/MPC、`libiberty`、`fixincludes`、`gcc.c-torture/execute` 和 `selftests`，没有把完整 testsuite 复制进后续构建路径。
- **验证方式**：记录官方 tarball 哈希；确认源码树中生成器输入、上游 selftest 和目标 torture 输入仍存在，再开始 configure。
- **不要这样做**：不要为了加速而删除生成器输入或把下载失败静默替换成任意版本的缓存文件。

### 3. bundled prerequisite 与独立工具依赖要分层

- **触发条件**：上游 `download_prerequisites` 会下载并解包 GMP、MPFR、MPC 等固定版本，同时构建阶段还需要 flex、m4 等工具。
- **处理方式**：保持上游 bundled GMP/MPFR/MPC 的版本边界，避免把它们无条件改成外部 Conan requires；把 `flex/2.6.4` 作为独立 `tool_requires` 复用。
- **设备差异**：制品仓的 `flex/2.6.4` 可能只有 `libfl.a` 和头文件，没有 `bin/flex`。此时仍保留 Conan 依赖关系，只允许回退到设备提供的同版本 `/data/service/hnp/flex.org/flex_2.6.4/bin/flex`，不能静默找其他版本。
- **环境注入**：显式设置 `FLEX`、`LEX`、`M4`，并把实际 executable 所在目录前置到 `PATH`；不能假设 `tool_requires` 自动影响所有 GCC 子构建。
- **验证方式**：在生成 `gengtype-lex.cc` 前检查 `FLEX` 是可执行文件，并在日志中记录最终解析到的路径。

### 4. HMDFS 上脚本必须通过 shell 入口调用

- **触发条件**：文件权限显示可执行，但 `configure`、`move-if-change`、`get_patches.sh`、`mkheader.sh` 或 Conan 生成的 wrapper 直接执行返回 `Permission denied`。
- **根因**：HMDFS 的 direct-exec 策略和普通 Linux 文件权限语义不完全一致，`chmod +x` 不能保证脚本可被 `posix_spawn` 直接启动。
- **处理方式**：将 Makefile 中的脚本命令改为 `$(SHELL) script`，将 Conan 生成的 wrapper 入口统一改为 `sh wrapper`；每个构建命令前显式设置可写 `TMPDIR`、`SHELL` 和 `CONFIG_SHELL`。
- **栈空间**：GCC 顶层 configure 和生成脚本可能需要更大 shell stack，外层命令使用 `ulimit -s unlimited` 后再 `exec` configure/make。
- **验证方式**：分别测试 `sh wrapper --version`、`$(SHELL) move-if-change` 和带临时目录的 configure probe；不要只测试 `ls -l`。

### 5. 先解析真实 executable，再生成 Conan 环境

- **触发条件**：设备环境导出了裸 `clang`、`AS=llvm-as` 或其他与 GCC 语义不一致的工具名。
- **处理方式**：优先从 `tools.build:compiler_executables` 取得命令，解析并校验 executable；OHOS worker 上默认使用 `/data/service/hnp/bin/clang` 与 `/data/service/hnp/bin/clang++`。GCC 目标汇编使用 GNU `as`，不能让 OpenDesk 的 `AS=llvm-as` 继承进来。
- **SDK 内部 clang 的 sysroot 定位**：worker 的 `compiler_executables` 可能由 PATH 解析为
  `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang`，
  此时 sysroot 是同一 SDK 版本下的 `ohos/native/sysroot`，不是
  `native/llvm/ohos-sdk.org`。通用做法是沿解析后的 clang 路径向上识别 `native` 或
  `llvm` 目录，再检查其兄弟 `sysroot`；对 `/data/service/hnp/bin/clang` 这类 HNP 入口，
  再扫描 `/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot`。候选路径必须检查
  `usr/include`，随后再检查目标三元组目录中的 `bits/alltypes.h`，避免把 SDK 容器目录误当作
  可用 sysroot。
- **构建/目标分离**：host compiler wrapper 负责签名 host ELF；target `xgcc` wrapper 负责 sysroot、availability 宏和 `-B` 顺序；不要用一个未经区分的全局 `CC` 覆盖所有阶段。
- **验证方式**：在 Conan generate 日志中确认 CC、CXX、AS、LD、M4、FLEX 的最终绝对路径，并用 `--version` 检查它们属于预期工具链。

### 6. 从 Clang 路径推导 OHOS sysroot

- **触发条件**：设备不存在 `/usr/include`，或者固定写死的 `/data/service/sysroot` 不存在。
- **处理方式**：从已解析的 OHOS Clang 真实路径向上定位 `ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot`，选择包含 `usr/include` 的版本目录；目标头文件额外确认 `usr/include/aarch64-linux-ohos/bits/alltypes.h` 存在。
- **配置方式**：同时传入 `--with-sysroot=<resolved-sysroot>`、目标 include 路径和 `--with-native-system-header-dir=/usr/include`，让 GCC 的 configure、fixincludes 和最终 driver 使用同一套头文件根。
- **验证方式**：用新建 `xgcc` 编译一个包含 `stdint.h`、`stdio.h` 的 AArch64 程序，检查 `__OHOS__` 和指针宽度。

### 7. PIE、签名与 host generator 是一个整体

- **触发条件**：`cc1`、`gen*`、`xgcc` 等 host 工具已生成但不能运行，或 AArch64 LLD 报非 PIE 重定位/对齐错误。
- **处理方式**：OHOS configure 使用 `--enable-host-pie`，并将 host probe 的 `gcc_cv_c_no_fpie`、`gcc_cv_no_pie` 设为 `no`；host 工具完成链接后统一扫描并签名，再进入依赖它们的下一构建阶段。
- **签名要求**：签名后的 ELF 必须仍是 `EXEC` 或 `DYN`，并含 `.codesign`；临时签名目录使用 0775 兼容 HMDFS。
- **验证方式**：在每个阶段前检查生成工具的 ELF 类型、`.codesign` section 和可执行性，不能把“文件存在”当成“工具可运行”。

### 8. `collect2` 的 linker 解析必须用 debug 输出确认

- **触发条件**：普通 `ld` smoke test 通过，但 GCC 链接阶段出现 `collect2: fatal error: posix_spawnp: Permission denied`。
- **诊断方式**：运行 `collect2 -debug`，查看它最终解析的是 `gcc/collect-ld`、`real-ld` 还是 `ld`。本次失败的关键是 `collect2` 选择了构建目录中的 `gcc/collect-ld`，只提供 `ld` 不会覆盖该路径。
- **处理方式**：用 OHOS `clang-sign` 把一个最小 C launcher 编译为真实 signed ELF；launcher 通过 `/system/bin/sh -c 'exec "$0" "$@"'` 转调 `/data/service/hnp/bin/ld`，并复制成 `ld`、`collect-ld`、`real-ld`。
- **安装边界**：构建树和安装包都要放入三个别名；安装后的 GCC wrapper 还要把 package `bin` 放在最高优先级 `-B` 路径。
- **验证方式**：单独执行 `collect-ld --version`、`ld --version`、`real-ld --version`，再用包含 CRT 搜索路径的最小 AArch64 程序做一次真实链接。

### 9. `-B` 顺序决定 GCC 最终使用哪套工具

- **触发条件**：`gcc/as` 是 shell wrapper 或构建树脚本，GCC 却优先调用它，导致 assembler 或 linker 的 direct exec 失败。
- **处理方式**：构建期 target wrapper 的顺序为 signed linker launcher、`/data/service/hnp/bin/`、构建树 GCC 目录和 OHOS sysroot；安装期 wrapper 的顺序为 package `bin`、`/data/service/hnp/bin/`、GCC 内部版本目录和 sysroot。
- **版本解析**：安装 wrapper 从 `gcc.real -dumpversion` 获取内部版本 `17.0.0`，不能用 Conan snapshot 日期 `20260705` 直接拼接 GCC libdir。
- **验证方式**：对构建期 `xgcc` 和安装后 `gcc` 分别执行 `-v` 或 `-print-prog-name=as`，核对搜索顺序；不要只验证 `gcc --version`。

### 10. 禁用可选子系统要覆盖生成代码和自测

- **触发条件**：配置使用 `--disable-lto`，但选项生成、LTO source 或 option-completion selftest 仍引用 LTO-only 常量；或目标平台不支持的警告选项使 selftest 失败。
- **处理方式**：同步处理 `c.opt` 的语言启用关系、LTO option consumers、`gcc.cc`、`opts.cc`、`toplev.cc` 等引用点；对明确不属于 AArch64 OHOS 的选项，只在源码变换阶段过滤 `-Wno-underflow`、`-Wtarget-lifetime`、`-Warray-temporaries`。
- **边界原则**：只删除由 configure 明确禁用的子系统引用，或删除经过目标平台证据确认不适用的自测项，不要大面积屏蔽整个 selftest。
- **验证方式**：记录 selftest 的 pass count 和失败选项名称；本次 C frontend selftest 通过 `7,676,387` 项。

### 11. 上游测试和 consumer test 要互补

- **上游测试**：保留 `make -C gcc selftest`；对 `gcc.c-torture/execute` 选择确定性的 50 个源文件，在 `-O0` 与 `-O2 -fno-strict-aliasing` 下各编译、签名、执行一次，共 100 次。
- **测试入口**：解析 torture 源文件中的 `dg-additional-options`，否则测试可能因遗漏上游针对性编译参数而出现假失败。
- **consumer test**：test_package 使用安装后的 relocatable `bin/gcc` 编译 `test_gcc.c`，检查 `__OHOS__`、AArch64 64-bit ABI、端序和运行时输出，并在 OHOS 上对生成的 ELF 执行签名后再运行。
- **负向验证**：在 shadow CI 中临时移走包的 `bin/` 和 `lib/`，确认 test_package 确实依赖被测包而不是环境中恰好存在的系统 GCC。
- **结果口径**：分别记录 selftest pass count、torture 编译/运行次数、consumer test 结果和 CI L0/L1/L2/L4/L5，不把不同口径混成一个“测试数量”。

### 12. 未执行测试必须逐项写出边界和原因

- **完整 testsuite**：GCC 官方源码清单有约 137,532 个 `*/testsuite/` 文件，但文件数不等于 DejaGNU testcase 数；完整 `make check-gcc` 还需要 board 配置、site.exp、目标运行环境和未裁剪的 testsuite。没有这些条件时，应明确写“未全量执行”，不能用 selftest 数量替代。
- **裁剪后的上游测试**：本次只保留 `selftests` 和 `gcc.c-torture/execute`，后者从 1,685 个源文件中选择 50 个做 `-O0`/`-O2` 双配置，共 100 次。未选源文件没有通过结论。
- **配置关闭项**：`--enable-languages=c`、`--disable-bootstrap`、`--disable-lto`、`--disable-multilib`、`--disable-shared`、`--disable-plugin` 以及可选 runtime 库关闭后，对应语言、bootstrap、LTO、ABI、共享库、插件和 runtime 测试都应逐项列为未执行，并说明这是 recipe 边界，不是上游测试失败。
- **平台矩阵**：只验证 OHOS AArch64 时，不应把 Linux、Windows、x86_64、其他 target 或 ABI 的结果并入“上游测试通过率”；需要记录已验证 profile 和未覆盖矩阵。
- **替代证据**：每项未执行测试都要给出实际替代验证，例如 C selftest、选定 torture、安装包 consumer、signed ELF 检查和 shadow CI 分层结果。

### 13. 失败诊断对照表

| 现象 | 优先检查 | 可迁移修复 |
|------|----------|------------|
| `source()` 报 settings forbidden | 是否在 `source()` 访问 `self.settings` | 把平台变换延迟到 generate/build，source 只做 settings-independent 操作 |
| `missing flex` 或找不到 `gengtype-lex.cc` | `FLEX`、`LEX` 和 PATH 的最终值 | 保留独立 `tool_requires`，显式注入可执行 flex，必要时回退同版本 HNP flex |
| `m4: not found` | `M4` 是否被设备工具路径覆盖 | 解析绝对路径并导出 `M4` |
| 脚本 `Permission denied` | 是否通过 shell 调用 | Makefile 使用 `$(SHELL) script`，Conan 入口使用 `sh wrapper` |
| `/tmp` 创建临时文件失败 | `TMPDIR` 是否位于可写 build 目录 | 每条 configure/make 命令显式导出 build-local `TMPDIR` |
| AArch64 非 PIE relocation 错误 | configure 是否选中 `-fno-PIE/-no-pie` | `--enable-host-pie` 并设置 host PIE configure cache |
| `collect2 posix_spawnp` 失败 | `collect2 -debug` 的 `ld_file_name` | 为真实 signed ELF 同时提供 `ld`、`collect-ld`、`real-ld` |
| 包内 GCC 找不到内部 libdir | `gcc.real -dumpversion` 和 wrapper 拼接路径 | 用内部版本 `17.0.0`，不要使用 snapshot 日期 |
| L2 裸 `gcc` direct exec 警告 | runner 是否直接 spawn 脚本 wrapper | 通过 `sh bin/gcc` 验证；若实际 consumer 通过则记录为 HMDFS 非阻断差异 |

### 14. 可复用的交接检查清单

1. 记录官方源码 URL、版本、SHA256、源码语言和 bundled prerequisite 版本。
2. 确认 source 阶段不读取 settings，并能用本地 tarball 回退复现。
3. 明确每个依赖属于 bundled prerequisite、独立 Conan require 还是设备工具，不跨库混改。
4. 记录所有生成器工具的绝对路径以及它们是否真的进入 PATH。
5. 检查所有脚本入口是否通过 shell，临时目录是否可写，栈空间是否足够。
6. 检查 host generator 是否为 PIE、是否已签名、是否可以在下一阶段直接运行。
7. 用 `collect2 -debug` 确认真实 linker 名称和 `-B` 搜索顺序。
8. 分别验证构建树 compiler、安装包 compiler、版本化 driver、linker aliases 和 consumer executable。
9. 记录上游 selftest、torture、consumer test、负向测试和 shadow CI 分层结果。
10. 把已解决的失败日志保留在 notes 和知识草稿中，并标明当前是否仍是 blocker。

### 15. 大源包下载要限制单连接风险

- **触发条件**：源码包在开发机和 HEAD 探测上都可访问，但 CI 日志长时间停在下载进度，最终出现 `conan create TIMED OUT after 3600s`；有序 URL 列表没有及时切换。
- **根因**：普通 URL 回退只在请求抛错后才进入下一个地址；连接如果保持建立但吞吐很低，Conan 会继续等待，外层 CI timeout 会把网络问题归类成构建超时。
- **处理方式**：仅针对大型公开 tarball，在 recipe `source()` 中先用 HEAD 获取 `Content-Length`，通过 `Range: bytes=start-end` 将文件拆成 4 MiB 分块，最多 8 路并行、每块最多重试 3 次；所有分块按序合并，检查总大小和唯一 SHA256 后再替换目标文件，并对 URL 列表逐个回退。
- **验证方式**：临时 Range HTTP 服务验证 404 首地址回退、分块响应边界、缺块重试、合并字节一致性和 SHA256；真机 CI 需要在 3600 秒门限内至少打印完整源码下载完成并继续进入解包。
- **不要这样做**：不要删除 SHA256、把半截文件当缓存使用、无限增加全局 CI timeout，或只增加镜像 URL 却不处理低速连接。

### 16. OHOS profile 要显式限制并发下界

- **触发条件**：recipe 代码写成“最多 `N` 个 jobs”，但 CI profile 没有 `tools.build:jobs`；Conan 的 `build_jobs()` 为兼容性会返回 1，GCC 自举在下载和 HMDFS 操作之后超过固定 3600 秒窗口。
- **根因**：上限限制不是并发启用；`min(build_jobs(self), 2)` 在默认 profile 上仍等于 1。串行编译会让 `all-gcc`、`all-target-libgcc`、签名和 consumer 前置步骤叠加耗尽时间。
- **处理方式**：只在已经验证支持 GNU Make pipe jobserver 的 OHOS 路径设置明确并发下界和上限；本次先用 `-j2` 复跑定位瓶颈，再根据 #44912 的阶段边界提升到 `-j4`，其他平台继续尊重 Conan 的 jobs 探测。
- **验证方式**：同时检查日志中的实际 `make --jobserver-style=pipe -jN`、`all-gcc`/`all-target-libgcc` 边界和剩余内存；确认 selftest、安装和 test_package 仍按顺序执行。并发调整只接受有阶段耗时证据的增量，不按设备核数盲目放大。
- **不要这样做**：不要修改 CI 全局 timeout、直接改基础设施配置，或在没有 HMDFS 证据时把 jobs 提高到设备核数。

### 17. 总超时要看最后一个完成的构建目标

- **触发条件**：CI 只返回“可能有交互式测试卡住”，而完整日志很长、失败点在固定总时限附近。
- **根因**：CI 的通用超时诊断无法区分源码下载、GCC 自举、目标运行库、安装包或 consumer；只看摘要容易把构建超时错判为测试失败。
- **处理方式**：优先截取日志尾部并寻找最后一个 `make[...] Leaving directory`、selftest 计数、torture 汇总和 `test_package` 标记。若最后停在 `all-target-libgcc`，应先优化该构建阶段的并发或输入边界；若没有进入 package/test_package，就不能宣称这些测试失败。
- **验证方式**：在 notes、manifest 和 PR 正文中分别记录“已完成阶段”和“未进入阶段”，并为下一轮配方增加可识别的阶段日志或明确命令。
- **不要这样做**：不要根据 bot 的 generic hint 直接跳过真实测试，也不要把“未执行”写成“失败”或“通过”。

### 18. 关闭未声明的 runtime 功能要同步记录产品边界

- **触发条件**：C-only 工具链在固定 CI 窗口内持续卡在 `all-target-libgcc`，日志显示大量 decimal/BID 或其他未被 consumer 使用的 runtime 对象。
- **根因**：GCC 的 target libgcc 会按目标默认能力拉入额外 runtime，即使当前 recipe 只交付 C frontend 和普通静态 libgcc；并发只能减少等待，不能消除这些不在产品范围内的对象。
- **处理方式**：使用上游已支持的 `--disable-decimal-float`，并把该能力明确写进 configure 边界、未执行测试表和知识草稿；target libgcc 可单独用 `CFLAGS_FOR_TARGET=-O2 -fPIC`、`CXXFLAGS_FOR_TARGET=-O2 -fPIC`，保留 host 工具的正常编译 flags。
- **验证方式**：确认普通 C consumer、selftest、torture、libgcc 链接和安装布局仍覆盖；检查日志不再出现 decimal/BID 对象集，并在交接中明确 decimal float 未适配。
- **不要这样做**：不要只删除某几个 BID 源文件、静默改成不完整的 `libgcc.a`，或继续声称 decimal-float ABI 已通过。

### 19. GCC 子 Makefile 的专用 debug 变量要单独覆盖

- **触发条件**：已经把 `CFLAGS_FOR_TARGET` 限定为 `-O2 -fPIC`，但 `all-target-libgcc` 的编译命令仍出现 `-g`，总构建时间只小幅下降。
- **根因**：libgcc 的 Makefile 会通过专用 `LIBGCC2_DEBUG_CFLAGS` 追加调试选项；它不是普通 `CFLAGS_FOR_TARGET` 的简单别名。
- **处理方式**：只对 target libgcc 的 make 命令传 `LIBGCC2_DEBUG_CFLAGS=-g0`，同时保留 `CFLAGS_FOR_TARGET=-O2 -fPIC`、`CXXFLAGS_FOR_TARGET=-O2 -fPIC`；host GCC 生成器继续使用原 profile flags。
- **验证方式**：在日志中确认 target libgcc 编译行不再包含由 `LIBGCC2_DEBUG_CFLAGS` 注入的 `-g`，并继续检查普通 C consumer、libgcc 链接、安装和 selftest。
- **不要这样做**：不要全局删除 host debug flags、修改 GCC 上游 Makefile 文件，或把“编译更快”当成 runtime ABI 测试通过。

## C 类候选依据

按“命中一条或两条复杂度条件即可”的口径，本库可作为 C 类候选提交。证据集中在两项：

1. **复杂工具链和目标汇编架构**：GCC 源码包含目标相关 assembler/backend 集成和大量生成的 host tool。OHOS 真机构建必须同时处理 GNU `as`/`ld`、AArch64 PIE 链接、生成 ELF 签名、OHOS sysroot、`-B` 搜索优先级以及 shell 包装执行，不能只按普通 C/C++ autotools 库处理。
2. **依赖、构建和验证成本**：snapshot 自带 GMP/MPFR/MPC，并依赖独立的 `flex/2.6.4` generator 工具和 `m4`；真机 `conan create` 在默认 3600 秒窗口内无法完成，执行验证需要临时 10800 秒窗口。当前已完成约 767 万项 GCC selftest、100 次 torture 编译运行和 consumer smoke，完整 GCC testsuite 的成本仍然很高。

边界说明：C 类候选不依赖“闭源二进制”或“私有编译工具链”表述，这两个特征在本库中并不存在。当前配方明确限定为 C frontend、非 bootstrap、非 LTO、非 multilib 目标，因此应申报为 `C-candidate`，最终等级交由维护者和评审确认。

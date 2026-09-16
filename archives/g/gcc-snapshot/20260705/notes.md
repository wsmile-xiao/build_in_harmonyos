# gcc-snapshot 20260705 前置适配笔记

## 当前状态

- 已完成版本目录骨架落地：`archives/g/gcc-snapshot/20260705/`
- 已改为独立 Conan 包：`gcc-snapshot/20260705`
- 已整理出上游来源与 bundled prerequisite 版本
- 已完成真机 shadow CI 回归：完整 `conan create`、安装包消费测试和 L0/L1/L2/L4/L5 均通过
- 2026-09-11 在 `10.62.229.155:2222` 上完成 100/100 `gcc.c-torture/execute` 子集验证，包内 `test_package` 输出 `gcc17-ohos-ok`
- 最新 PR CI #44703 未进入构建或测试阶段：worker 访问官方 GCC 源时在 99.6 MB 长连接中断流，且预下载步骤发现 worker 没有 `curl`。这属于源码下载环境阻塞，不是编译器或测试断言失败；本次加入 Sourceware Mirror Service 镜像优先、官方源兜底，并对四个下载项统一保留 SHA256 校验。
- PR CI #44737 已确认镜像回退生效，四个源码包均下载成功；随后在 `generate()` 创建签名 linker launcher 前因 sysroot 解析失败停止，错误路径为
  `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/ohos-sdk.org`。
  该失败属于配方路径推导错误，不是源码下载、编译或 test_package 断言失败；本轮已修复并等待重跑。
- PR CI #44804（2026-09-12）已通过：`conan-build-test` 运行 3549 秒，完成源码获取、Conan 构建、安装包消费测试、L0/L1 门禁和 cleanup；`Conan test_package`、`worker_preparation`、`worker-prep`、`git-clone`、`checkout-pr`、`conan-setup`、`conan-build-test`、`cleanup` 全部成功。
- PR CI #44812（2026-09-12）在 3600 秒门限超时，日志停在 GCC 99.6 MB 源包约 88.7 MB 的单连接下载处；这不是源码编译或测试断言失败。为避免依赖一次长连接，`source()` 现对 GCC 主包使用 4 MiB HTTP Range 分块、最多 8 路并行、每块 3 次重试、合并后 SHA256 校验，并按 URL 列表顺序回退。
- PR CI #44864（2026-09-12）已越过源码获取和前置阶段，GCC `all-gcc` 日志打印 `7,676,387 pass(es)`，但 `conan create` 在 3600 秒窗口内仍未完成；根因是 OHOS profile 未配置 `tools.build:jobs`，`build_jobs()` 返回 1，现有上限逻辑实际执行串行 make。本轮将 OHOS 构建固定为已验证的 `make --jobserver-style=pipe -j2`，并保留 CI `file://` 源缓存直用路径。
- PR CI #44912（2026-09-12）已验证上一轮 `-j2` 和源码缓存兼容路径可以继续推进：日志完成 `all-gcc` 与 `7,676,387 pass(es)`，并在 `all-target-libgcc` 收尾处触发 `conan create TIMED OUT after 3600s`；没有进入 package、安装包签名、test_package 或 L1/L2/L4/L5。CI bot 给出的“可能交互式测试卡住”是通用超时提示，实际阻塞点仍是构建时间窗，不是上游测试断言失败。现已改为 OHOS `make --jobserver-style=pipe -j4`，非 OHOS 仍保留较低上限，等待下一轮验证。
- PR CI #44956（2026-09-12）已实际使用上一轮 `-j4`，仍在 `all-target-libgcc` 收尾处于 3600 秒窗口超时；`package`、安装包签名、`test_package` 和 L1/L2/L4/L5 仍未启动。两轮失败边界一致，说明继续单纯提高 make 并发不能解决固定窗口；下一轮将保持 bounded pipe 并发，同时在 OHOS C/static-libgcc 产品边界关闭 decimal-float runtime，并用 `CFLAGS_FOR_TARGET=-O2 -fPIC`、`CXXFLAGS_FOR_TARGET=-O2 -fPIC` 去除 target libgcc 继承的调试编译标志。
- PR CI #44992（2026-09-12）实际应用了 `--disable-decimal-float` 和 target `-O2 -fPIC`，构建耗时降至 3722 秒，较 #44956 缩短 193 秒；日志中 decimal/BID 对象已不再出现，但 libgcc 收尾仍越过 3600 秒，未进入 package、安装包签名、`test_package` 和 L1/L2/L4/L5。复盘发现 GCC `libgcc/Makefile.in` 还会通过 `LIBGCC2_DEBUG_CFLAGS=-g` 强制注入调试信息，下一轮将显式覆写为 `-g0`，不改变普通 libgcc 功能边界。
- PR CI #45033（2026-09-12）已通过：第五轮修复显式传入 `LIBGCC2_DEBUG_CFLAGS=-g0` 后，`conan-build-test` 用时 3562 秒、构建总耗时 3647 秒；Conan `test_package`、L0、L1 以及 `worker_preparation`、`worker-prep`、`git-clone`、`checkout-pr`、`conan-setup`、`conan-build-test`、`cleanup` 全部成功。该结果确认此前 `all-target-libgcc` 固定时间窗阻塞已解除，未把未覆盖的 GCC 测试矩阵写成通过。

## 审查整改

- 规则审查曾指出 PR 模板两张测试统计表的合计字段必须是数字，不能填写“分层统计”文本；当前 PR 正文已分别填写 `7676490`（上游执行统计）和 `7676491`（适配后统计），并在说明列保留不同计数口径。
- `test_package` 复核确认不是空跑：先执行被测 GCC `--version`，再用安装后的 relocatable driver 编译 `test_gcc.c`，检查 `__OHOS__`、64 位指针和 little-endian，OHOS 上完成 ELF 头、签名后 `.codesign` 段、真机执行和 `gcc17-ohos-ok` 输出；所有非零退出均会使 Conan test_package 失败。
- 修正 `test_package` 的签名工具探测：`binary-sign-tool`、`objcopy` 和 `readelf` 的 PATH/设备候选现在逐个确认文件存在，避免把不存在的备用字符串误当成可执行路径。

## 这轮改动

- `conanfile.py`
- `conandata.yml`
- `manifest.yaml`
- `files/prepare_ohos_sources.py`
- `test_package/conanfile.py`
- `test_package/MANIFEST.yml`
- `test_package/test_gcc.c`
- `commands.json`

## 源与校验

- GCC snapshot: `https://gcc.gnu.org/pub/gcc/snapshots/17-20260705/gcc-17-20260705.tar.xz`
- gmp 6.3.0: `https://gcc.gnu.org/pub/gcc/infrastructure/gmp-6.3.0.tar.bz2`
- mpfr 4.2.2: `https://gcc.gnu.org/pub/gcc/infrastructure/mpfr-4.2.2.tar.bz2`
- mpc 1.3.1: `https://gcc.gnu.org/pub/gcc/infrastructure/mpc-1.3.1.tar.gz`

## 依赖检查

- W0 结果：recipe 仍然走 GCC bundled prerequisites，不引入额外 Conan requires
- 构建工具前置依赖：`flex/2.6.4`。GCC snapshot 未携带预生成的 `gcc/gengtype-lex.cc`，真机构建 generator 阶段需要 `flex` 生成该文件。
- 设备工具链前置工具：`m4`。flex 生成 scanner 时会调用 m4，配方已显式固定 `M4`，避免 GCC configure 退回 `missing m4`。
- `flex/2.6.4` 已单独适配并作为 `tool_requires` 复用；gcc-snapshot 这里不再内联混入 flex 适配。
- 真机 build env 不能只靠 `tool_requires` 自动进 PATH；这轮已补成 `env.define("FLEX", <绝对路径>)` + `env.prepend_path("PATH", <flex/bin>)`，避免 GCC 继续回退到 `missing flex`。
- shadow CI 暴露出制品仓现有 `flex/2.6.4` 二进制只含 `libfl.a` 与头文件、未含 `bin/flex`；配方仍声明独立 `tool_requires("flex/2.6.4")`，并仅回退到 worker 自带的同版本 `/data/service/hnp/flex.org/flex_2.6.4/bin/flex`，禁止静默选择其他版本。
- OHOS HMDFS 上 `collect2` 会直接 spawn `gcc/collect-ld`，而 HNP 的 `ld` 不能被当作普通脚本或受保护路径直接 spawn；配方在构建期生成签名 ELF launcher，并以 `ld`、`collect-ld`、`real-ld` 三个别名同时放入构建树和安装包。
- 现成代码来源：`D:/harmonyos/worktrees/flex/archives/f/flex/2.6.4/`，对应知识草稿见 `D:/harmonyos/worktrees/flex/knowledge/drafts/DRAFT-flex-ohos-generator-toolchain.md`。
- GCC 主库知识草稿：`D:/harmonyos/worktrees/gcc-snapshot/knowledge/drafts/DRAFT-gcc-snapshot-20260705-ohos-source-tree-and-fresh-build.md`。
- 知识草稿已扩展为 20 条可迁移条目，覆盖 source/cache、依赖分层、HMDFS shell、SDK 内部 clang/sysroot 路径、PIE/signing、`collect2` linker、`-B` 顺序、禁用 LTO、测试设计、失败诊断、低速长连接下载、受限 profile 并发、固定总超时阶段定位、C/static-libgcc 边界、libgcc 专用 debug 变量和交接清单。
- 目前源码内嵌下载项：gmp/mpfr/mpc
- 2026-09-08 复跑确认：这版 snapshot 的 `gcc/Makefile.in` 已是 `FLEX = @FLEX@`，无需再强改成固定 `flex`；真机 `generate()` 里编译器默认值必须用 `/data/service/hnp/bin/clang` 和 `/data/service/hnp/bin/clang++`，裸 `clang` 在 Conan 环境里找不到。

## B/C 类候选说明

- 当前标记为 `C-candidate`，同时保留 B 类知识扩展证据；最终难度等级以仓库维护者和评审结论为准。
- 候选依据不是“源码体量大”本身，而是可复用的 HarmonyOS 适配知识：自举型 C/C++ 工具链、bundled GMP/MPFR/MPC、generator 依赖 flex、HMDFS 脚本执行限制、只读 `/tmp`、OHOS sysroot 探测、host generator ELF 签名、PIE 链接约束，以及独立 consumer test。
- 适配边界保持原子化：`flex/2.6.4` 作为独立工具依赖，不把 flex 的适配改动混入 gcc-snapshot；GCC 草稿只记录 gcc-snapshot 自身可复用的依赖和构建结论。
- 按“满足一条或两条即可”的 C 类口径，本库可提交 C 类候选：一是目标汇编/`as`/`ld`/PIE/ELF 签名组成的复杂工具链架构，二是 bundled 依赖、generator/runtime 组件和高成本 selftest/torture 验证带来的真机资源与时间成本。
- C 类证据边界：本库不是闭源二进制，也不是私有编译工具链；当前 recipe 仅支持 C frontend、`--disable-bootstrap`、`--disable-lto`、`--disable-multilib` 配置，不把裁剪后的范围冒充完整 GCC 发行版矩阵。
- 当前证据状态为“本机静态检查通过、真机完整 shadow CI 通过、默认 3600 秒窗口不足而使用 10800 秒执行窗口”；C 类仍是候选标记，最终等级以仓库维护者和评审结论为准。

## 未执行测试边界

本轮不把“没有执行”写成“通过”。以下项目明确未执行，原因和替代证据如下：

| 未执行项目 | 不执行原因 | 已有替代验证与影响 |
|---|---|---|
| 完整 GCC DejaGNU testsuite（`make check-gcc` / `make -k check`） | 官方源码包包含约 137,532 个 `*/testsuite/` 文件，完整运行还需要 DejaGNU `site.exp`、OHOS board 配置和大量 target/runtime 前置；本包为单包真机构建，源码解包阶段只保留构建必需目录，未保留完整测试树。 | 已执行 `make -C gcc selftest`，输出 7,676,387 pass(es)，并执行 100 次确定性 torture；因此只证明当前 C frontend 和选定目标执行链，不代表完整 GCC testsuite 全量通过。 |
| 全量 `gcc.c-torture/execute` | 上游目录有 1,685 个源文件，完整编译、签名和真机运行会显著扩大单包重任务窗口；当前没有把完整 DejaGNU torture driver 移植成 OHOS runner。 | 选取 50 个源文件，在 `-O0`、`-O2 -fno-strict-aliasing` 下各执行一次，共 100/100；未执行的源文件不宣称通过。 |
| C++、Fortran、Ada、Go、D、Rust、Objective-C/Objective-C++、Modula-2、COBOL 等 frontend tests | 配方明确使用 `--enable-languages=c`；其他 frontends 的生成器、运行库、目标选项和测试依赖没有纳入本包边界。 | C frontend selftest、C torture 和安装包 C consumer；其他语言需要单独扩大 recipe 配置后再测。 |
| bootstrap / rebootstrap / 三阶段编译器一致性测试 | 配方明确使用 `--disable-bootstrap`；三阶段构建会重复构建和比较编译器，超出本轮单包真机交付范围和时间预算。 | 已完成单阶段 `all-gcc`、`all-target-libgcc`、selftest、package 和 consumer；不等价于 bootstrap 结果。 |
| LTO、WPA/LTRANS、`lto-plugin` 测试 | 配方明确使用 `--disable-lto`；本轮还对 LTO-only option consumers 做了禁用态兼容保护，未声明 LTO 功能支持。 | 通过禁用 LTO 的 C frontend selftest、目标编译和安装包 consumer；不覆盖 `-flto`、WPA、LTRANS 或插件链。 |
| multilib、32-bit/ILP32 或其他 ABI 矩阵 | 配方明确使用 `--disable-multilib`，Conan profile 只支持 OHOS `armv8`，设备 sysroot 也只验证 AArch64 OHOS ABI。 | consumer 检查 64 位指针、little-endian、OHOS 宏并在真机运行；不代表其他 ABI 可用。 |
| shared GCC libraries、plugin load、动态插件测试 | 配方明确使用 `--disable-shared`、`--disable-plugin`，交付目标是可重定位 C driver 和静态 libgcc 的最小工具链。 | 已验证安装布局、driver wrapper、signed ELF、链接和执行；不覆盖共享库或 GCC plugin ABI。 |
| decimal-float/BID runtime and decimal-float tests | 本 PR 的 OHOS 产品边界是 C frontend + static libgcc；decimal-float 会拉入大批 soft-fp/BID 对象并在固定 CI 窗口内显著增加构建成本，当前没有为 OHOS decimal ABI 准备独立 consumer 和完整测试矩阵。 | `--disable-decimal-float` 下验证 C frontend、普通 libgcc、selftest、torture 和 consumer；不把 decimal floating-point 支持宣称为已适配。 |
| threads、libatomic、libitm、sanitizer、libgomp、libquadmath、libssp、libvtv 等可选 runtime tests | 这些目标库在配置中明确禁用；其中 OHOS libc 缺少 GCC POSIX gthread 构建所需的 `pthread_cancel`，本轮选择单线程 C/libgcc 边界。 | `all-target-libgcc`、C selftest、torture 和 consumer 通过；不把未启用 runtime 宣称为已适配。 |
| Graphite/ISL、NLS/locale/message catalog tests | 配方明确使用 `--without-isl`、`--disable-nls`，相应第三方依赖和国际化运行时没有进入本包。 | 核心 C compiler、libgcc、安装和目标程序验证；不覆盖 Graphite 或 NLS。 |
| 非 OHOS host、非 AArch64 target、交叉 host/target 组合 | 本 PR 的 settings 与真机 profile 只针对 OHOS AArch64；没有为 Linux、Windows、x86_64 或其他 target 准备并验证对应 sysroot、签名和 linker 规则。 | 真机 OHOS profile 的完整 Conan、shadow CI 和 consumer；不代表跨平台发行版矩阵。 |
| 长时间压力、性能基准、并发 jobserver 矩阵 | 本轮没有建立 benchmark 基线，也没有执行跨设备、长时间压力或完整并发矩阵；`-j4` 只作为 OHOS 固定窗口内的 bounded CI 构建策略验证。 | PR CI #45033 已验证 `-j4` 路径可完成 `conan-build-test`、`test_package`、L0/L1 和 cleanup；这不等价于性能基线、长时间稳定性或其他并发档位全覆盖。 |

另外，CI #44703 在源码下载阶段失败，因此该轮没有产生新的 L1/L2/L4/L5 测试结果；不能把这次网络失败写成测试通过或测试失败。后续 PR CI #45033 已完成 Conan `test_package`、L0/L1 和全部 CI steps；R4 真机回归仍以 notes 中记录的 `10.62.229.155:2222` 结果为准。

## 验证结果

- 已核对 `download_prerequisites`，确认 snapshot 默认选择：  
  `gmp-6.3.0.tar.bz2` / `mpfr-4.2.2.tar.bz2` / `mpc-1.3.1.tar.gz`
- 代码级校验结果: `python -m py_compile` 通过，`conan export` 通过，`config.gcc` 的 aarch64/musl 变换锚点已在 snapshot 实包中对上（`aarch64*-*-linux*` 仍保留 `aarch64/t-aarch64 aarch64/t-aarch64-linux`，`*-*-*musl*` 与全局 `*-*-linux*android*|*-*-linux*uclibc*|*-*-linux*musl*` 分支仍在）
- 真机 `conan create` 已实际启动；早前一版半截下载文件的 hash 为 `8a4f1f89d84c66396ab0f1be7283ccb7578a148f0303b2f0d96f722ced1d2d88`，已被后续重新下载的官方 tarball 哈希替换
- 2026-09-04 继续真机手工验证：使用手工构建出的 flex 二进制推进 `make all-gcc`，已越过 `gengtype-lex.cc`、MPFR `get_patches.sh`、libcpp/GCC `move-if-change`、`checksum-options` 等断点，并到达 `cc1` 链接阶段。
- `gcc/c/Make-lang.in`、`gcc/cp/Make-lang.in`、`gcc/objc/Make-lang.in`、`gcc/objcp/Make-lang.in` 中的 checksum `move-if-change` 规则已补为 `$(SHELL)` 调用，避免 HMDFS 上 direct exec `Permission denied`。
- `cc1` 链接暴露旧构建目录的非 PIE 问题：旧 configure 生成 `-fno-PIE/-no-pie` 时 LLD 报 AArch64 重定位对齐错误；手工去掉非 PIE 后又提示对象需重新以 PIC/PIE 编译。recipe 已在 OHOS configure 参数中加入 `--enable-host-pie`，fresh build 应从一开始生成 PIE host tool 对象。
- 2026-09-11 build23 复核：`all-gcc` 已完成，GCC C frontend selftest 通过，记录为 `7,676,387 pass(es) in 3.617644 seconds`；当前继续执行 `all-target-libgcc`。
- 2026-09-11 真机消费验证：安装后的 `bin/gcc` wrapper 动态获取 GCC 目录版本 `17.0.0`，并以 `/data/service/hnp/bin/` 为最高优先级 `-B`；最小 AArch64 程序成功编译、链接、签名和运行。
- 2026-09-11 真机 torture 验证：50 个上游 `gcc.c-torture/execute` 源文件在 `-O0`、`-O2 -fno-strict-aliasing` 下共 100 次编译/签名/执行，结果 `100/100` 通过；执行器已支持读取源文件的 `dg-additional-options`。
- GCC 配置为 `--disable-lto` 后，snapshot 仍会在生成选项表和多个 LTO 源文件中引用 LTO-only 常量；recipe 已对 `gcc/c-family/c.opt` 的 `LangEnabledBy ... LTO`、`lto-opts.cc`、`lto-wrapper.cc`、`gcc.cc`、`opts.cc` 和 `toplev.cc` 做幂等的禁用 LTO 兼容变换。
- 目标端 option-completion selftest 的选项完成表包含当前 AArch64 OHOS 不适用的 `-Wno-underflow`、`-Wtarget-lifetime`、`-Warray-temporaries`；已在源码变换中移除这三个明确不适用项，避免把目标平台选项差异误判为编译器自测失败。
- OHOS 设备上的 `gcc/as` 可能是不可直接执行的脚本，且 GCC 的 `-B` 搜索顺序会优先命中构建树；`CC_FOR_TARGET` 必须让 `/data/service/hnp/bin/` 的 GNU `as` 优先于构建树，并通过 shell wrapper 注入 AArch64 sysroot、`__availability__` 兼容宏和新建的 `xgcc`。
- 安装后的包 wrapper 也必须保留同样的 `-B/data/service/hnp/bin/` 优先级；仅在构建期 wrapper 修正 `CC_FOR_TARGET` 不足以保证最终 `bin/gcc` 的用户编译路径。
- `libgcc/Makefile.in` 中 `mkheader.sh` 也必须经 `$(SHELL)` 调用；否则目标运行库已经开始配置，仍会在生成 `libgcc_tm.h` 时因 HMDFS 的 direct exec 策略失败。
- R3 曾因 `collect2: fatal error: posix_spawnp: Permission denied` 导致 torture 全部失败；`collect2 -debug` 确认实际选择的是 `gcc/collect-ld`，不是仅靠 `-B` 提供的 `ld`。增加三个 signed ELF launcher 别名后，R4 已将同一回归跑到 100/100。
- R4 官方 runner 结果：`conan create` 成功，L0/L1/L2/L4/L5 全部 `pass`，`test_package` 编译、链接并运行成功，最终退出码为 `0`。
- PR CI #44804 结果：修复后的 sysroot 候选解析已实际越过 `generate()`，并完成 `conan-build-test` 与 `Conan test_package`；PR CI 的 L0、L1 和 cleanup 均为 `pass`。
- PR CI #44812 结果：前置 L0 已通过，但因大源包单连接下载在 3600 秒窗口内未完成而由 CI 超时终止；本轮新增并行 Range 下载器后需要重新验证，不把该次记为编译器或测试失败。
- PR CI #44864 结果：源码和 GCC 自测阶段已推进，日志包含 `7,676,387 pass(es)`；由于 `build_jobs()` 在 OHOS profile 中退化为 1 路，`conan create` 超时，未进入 package/test_package 和 L1。随后 #44912 验证 `-j2` 已进入 `all-target-libgcc` 收尾但仍耗尽 3600 秒；当前改为 OHOS `-j4` pipe jobserver，并支持直接消费 CI 预下载的 `file://` GCC tarball，等待重新验证。
- PR CI #45033 结果：应用 `LIBGCC2_DEBUG_CFLAGS=-g0` 后已越过此前的 `all-target-libgcc` 超时边界；`conan-build-test` 用时 3562 秒、总耗时 3647 秒，Conan `test_package`、L0/L1 和全部七个构建步骤均通过。

## 历史问题与当前结论

- 当前无源码、编译或测试断言方面的功能性阻塞；PR CI #45033 已验证 bounded OHOS pipe jobserver、`--disable-decimal-float`、target `-O2 -fPIC` 和 `LIBGCC2_DEBUG_CFLAGS=-g0` 的组合可以完成构建、安装包消费测试和 L0/L1。仍未覆盖的测试矩阵已在本节逐项列明。
- 当前 Windows shell 没有 `conan` 命令，因此本机只完成静态检查；这不是设备 CI 的阻塞。
- 真机 SSH 复核过两个目标：
  - `10.62.238.136:2222` 连接被拒绝
  - `10.62.220.52:2222` 之后已可登录，SSH 入口可用
- 2026-09-03 复测 `10.62.220.52:2222` 已可登录，SSH 入口可用；但 `whoami` / `id` 在设备侧返回 `bad uid 20020083`，`getprop` 不可用
- 本机已重新下载并核对官方 `gcc-17-20260705.tar.xz`，真实 SHA256 为 `86253d2e3189cfffb1c9afb7779b67e792b980ce7cf072323b137473896dfcdc`
- 设备侧已用预置的 Conan source cache 跑通 `conan source`；完整 `conan create` 会直接复用 `tool_requires("flex/2.6.4")`
- 这轮发现 Conan 复制整棵 GCC 源码树进 build folder 太慢，已改为 `no_copy_source = True` 重新跑后续验证
- 生成阶段又暴露出 OHOS 设备工具路径差异，`llvm-objcopy` / `llvm-readelf` 实际在 `/data/service/hnp/bin/`，已补齐显式 fallback
- 继续构建时又发现 OHOS SDK sysroot 不在 `/data/service/sysroot`，而是在 `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot`，已改成自动探测
- CI #44737 进一步暴露了 clang 路径差异：`tools.build:compiler_executables` 可能解析到 SDK 内部的
  `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang`，
  不能再假定 clang 位于 `/data/service/hnp/bin`。配方现在沿解析后的 clang 路径识别
  `native/sysroot`，并保留从 `/data/service/hnp/ohos-sdk.org/ohos-sdk_*/...` 扫描的兜底，
  因而不会错误生成 `.../native/llvm/ohos-sdk.org`。
- 进一步排查发现 `configure` 会被 `CONFIG_SHELL=/data/service/hnp/bin/bash` 拉回 Bash，导致 `getcwd` / working directory 失败；已改成 `/bin/sh`
- 还发现 Conan cache 里的 wrapper 脚本不能直接执行，`configure` 需要通过 `sh <wrapper>` 方式调用；已把 build / configure / torture 入口统一改成 shell 解释 wrapper
- `test_package` 也改成在 OHOS 上通过 `sh <wrapper>` 调用被测 `gcc`
- MPFR configure 会回退到只读 `/tmp` 创建临时文件；已在 GCC 每个构建命令前显式导出 `TMPDIR`、`CONFIG_SHELL`、`SHELL`
- HMDFS/设备执行策略下源码脚本即使 chmod 后仍可能不能直接执行；已将 MPFR `GET_PATCHES_SH`、libcpp `move-if-change` 改为通过 `$(SHELL)` 调用
- 真机旧构建目录已跑过 GMP、MPFR、MPC、zlib、libcpp、libdecnumber、fixincludes，并进入 GCC generator 构建；当前已定位到 `gengtype-lex.cc` 生成需要 flex 和 m4
- 2026-09-09 build4 复跑：独立 `flex/2.6.4` 已在设备上重新构建并打包，后续已切换到 `10.62.229.155:2222` 完成 build23 验证
- 手工验证结果：
  - `TMPDIR=$PWD/.tmp sh /storage/Users/currentUser/.conan2/p/gcc-secdcff512bebd/s/configure --version` 成功
  - `sh .ohos-wrappers/clang-sign conftest.c -o conftest` 成功并生成 `.codesign`
  - `make --jobserver-style=pipe -j1 all-gcc`、`all-target-libgcc`、`make -C gcc selftest` 已完成；C selftest `7,676,387` 项通过
  - package install 已完成，安装后的 `bin/gcc` 已通过版本/sysroot 探测和 AArch64 smoke 编译、链接、签名、运行
  - 100 项 torture 子集已全部通过
- 2026-09-11 shadow CI 第 1 轮完成了 L0 前置、Conan setup 和 flex 依赖解析，但因设备直连 gcc.gnu.org 的 99.6 MB 长连接在 46.6 MB 处断流失败；后续缓存复跑发现制品仓 `flex/2.6.4` 缺少 `bin/flex`，已补充同版本 HNP flex 回退逻辑。
- 同日 R3 首次完整验证暴露 `collect2` 直接 spawn `collect-ld` 的 HMDFS 权限问题；现已通过 signed ELF launcher 和 `ld`/`collect-ld`/`real-ld` 别名修复，R4 完整回归通过。

## 真机复跑命令（R4 已验证）

```bash
ssh -i C:/Users/ASUS/.ssh/ohos_pc_codex_ed25519 -p 2222 currentUser@10.62.229.155
sh /storage/Users/currentUser/bin/ohos-test-runner.sh --user currentUser --lib gcc-snapshot --task gcc-snapshot-20260705-shadow-cache-r4 --mode heavy --lock -- sh /storage/Users/currentUser/ohos-users/currentUser/gcc-snapshot-20260705-shadow-20260911/run-shadow-cache-r4.sh
```

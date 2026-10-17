# libnxt 0.5.2 适配笔记

## 任务与上游
- 任务：libnxt 0.5.2 HarmonyOS PC 适配（积分赛，申请人 momimgya，队伍 干）
- 分支：feat/libnxt-0.5.2
- 上游仓库：https://github.com/schodet/libnxt（官方镜像源 https://git.ni.fr.eu.org/libnxt.git）
- 上游版本：0.5.2（tag 归档）
- 源 URL：https://github.com/schodet/libnxt/archive/refs/tags/0.5.2.tar.gz
- SHA256：ad8e6e2b32c841518f2ab36ed1eddba9eb74e42db1037711177c8776eea4f94e（Windows curl 实拉 tag 归档 + certutil 校验，37 条目含 meson.build/meson_options.txt）
- 语言：C（任务平台声明 cpp，c↔cpp 兼容族）
- 构建系统：meson（>= 0.60）
- 依赖：libusb-1.0（本配方 requires libusb/1.0.27，PkgConfigDeps 生成 .pc 供 meson dependency() 消费）
- 构建期工具：meson/1.11.0、pkgconf/3.0.6（tool_requires，CCI 提供）
- 产物：静态库 libnxt.a（nxt）+ 工具 fwflash/fwexec + 头文件（error/lowlevel/samba/firmware/flash/cmd/common）

## 适配方式（无补丁）
- 首轮无 patches/：上游 meson.build 无需 OHOS 源码修改即可配置（POSIX 代码 + libusb）。
- `-Dbuild_doc=disabled`：跳过 scdoc 手册页（真机/CI 无 scdoc，避免 man 构建失败）。
- MesonToolchain + PkgConfigDeps：libusb 头/库经 PKG_CONFIG_PATH 透传；archiver 显式注入 SDK llvm-ar/llvm-ranlib（libdrm 2.4.133 同款逻辑，防 CI 裸 `llvm-ar` 不在 PATH）。
- 上游 `static_library('nxt')` 默认不 install：package() 先 `meson install`（装 fwflash/fwexec），再从 build 树拷贝 libnxt.a 到 lib/、顶层 7 个公开头到 include/；缺失工具时从 build 树按名找回并拷贝到 bin/。
- OHOS 可执行签名：fwflash/fwexec 若存在 binary-sign-tool 则自签名（bossa 1.9.1 同款，失败不阻塞）。
- R32：validate 仅允许 Linux/OHOS；R33：无裸 shell 编译器变量，全经 MesonToolchain/conf；R26 不适用（libnxt 非系统同名库，静态库天然隔离）；R38：含可执行产物，已在软件级提供 commands.json（type tool）。

## W0 依赖检查
- libusb/1.0.27：本仓库 archives/l/libusb/1.0.27 已有配方（autotools，制品仓发布状态待 HMBS 真机预检复核；若未发布需先发布再跑本包 W3）。
- meson/pkgconf 为 CCI 工具包，tool_requires 拉取，不进运行时依赖链。

## 上游测试审计（R51，无测试）
- 源码包实拉验证（37 条目）：顶层无 tests/test/spec 目录，无 *test*/*check* 文件；meson.build 全文无 `test(` 注册，仅 static_library + 2 executable + custom_target（flash_routine.h 生成）；meson_options.txt 仅 `build_doc` 选项；flash_write 仅 ARM 固件构建（需 arm-none-eabi-gcc/as/ld/objcopy），doc 仅 scdoc 手册。
- 结论：`upstream_tests_exist: false`，`upstream_test_total: 0`（口径 auto），build() 不集成上游测试（upstream_test_in_build: false）。真实 flashing 需 NXT 真机硬件，无法在 CI/真机自动化。
- 风险：flash_write 需 ARM 交叉工具链。若真机无 arm-none-eabi-gcc，meson setup 将在 `find_program` 处失败；届时方案为补丁将其改为 `required: false` + 预生成 flash_routine.h（ARM blob 与宿主无关，可一次性在有 ARM GCC 的机器上生成后内嵌），首轮先让真机实测暴露。

## 消费者测试（test_package，1 项 ctest）
- test_nxt.c 真实调用库 API（非空壳）：
  1. `nxt_str_error` 对 NXT_OK/NXT_NOT_PRESENT/NXT_FILE_ERROR/NXT_INVALID_FIRMWARE/未知码断言非空且已知值匹配 "Success" 等；
  2. `NXT_ERROR_USB`/`NXT_ERROR_CMD` 宏阈值断言；
  3. `nxt_firmware_validate` 对不存在路径断言 NXT_FILE_ERROR，对临时小文件断言 NXT_INVALID_FIRMWARE（无需硬件，纯文件逻辑）；
  4. `nxt_init`/`nxt_exit` 配对调用（libusb 初始化路径；不断言设备存在，仅断言 init 成功或返回可解释错误后 exit 不崩溃，命令退出码为判据）。
- CMake + CMakeDeps 链接 libnxt::libnxt，ctest 1/1 为计数口径。含 HMBS_TEST_PACKAGE_RESULT 标记规划（discovered/passedCount 取自 ctest 输出，禁止字符串数数）。

## W3 本地验证
- 本机为 Windows，无 conan/OHOS 工具链，不在本机运行 conan（规范要求真机验证）。首轮仅完成未提交工作树，待 HMBS 真机预检（conan create + ctest + 上游 no_tests 标记）回填实测数字后再定 manifest status 与 PR 通过率。

## 已知限制
- 需 NXT USB 真机才能验证 fwflash/fwexec 实际烧录；本适配仅保证库编译链接 + 无硬件 API 路径正确。
- 若真机缺 ARM 交叉工具链，flash_write 配置失败需第二轮补丁（见上）。

---

**首轮状态**：未提交工作树，待真机预检。

## 真机复检记录
- pkg-config 注入已生效（真机日志 `meson pkg-config: using '.../bin/pkgconf'`），libusb 探测通过。
- 新失败：`flash_write/meson.build:1:5: Program 'arm-none-eabi-gcc' not found`。根因：顶层 meson.build 无条件 `subdir('flash_write')`，而该子目录用裸机工具链把 NXT 端 ARM7 驱动（flash.c + crt0.s）编成 flash.bin 再经 make_flash_header.py 生成 flash_routine.h；真机无该工具链。
- 修复路线：配方 `build_requirements` 新增 `tool_requires("arm-gnu-toolchain/14.2")`（CCI 官方裸机包，wolfssl 裸机用例同款；等价于 Debian 的 gcc-arm-none-eabi 构建依赖），meson 的 `find_program` 经 conanbuild PATH 直接命中，无需改上游构建文件，blob 仍由上游源码真实编译。修改保持未提交，待 HMBS 复跑真机预检。

## 真机复检记录（2026-09-20 第二轮）
- 新失败：`ERROR: Package 'arm-gnu-toolchain/14.2' not resolved: Unable to find 'arm-gnu-toolchain/14.2' in remotes`（conancenter + ohpcd 均无此包，依赖图解析阶段即失败）。
- 根因确认：上一轮假设错误。`arm-gnu-toolchain` 的 CCI 提案（PR #17528，11.3.0/12.2.0）从未合入 conancenter；且该配方 `validate()` 拒绝非 Linux-x86_64 宿主，即使存在某版本，在 OHOS armv8 真机上也会被拒。`tool_requires` 此包在真机与官方 CI 上永远不可解析。
- 新修复（保持“仍从上游源码真实编译 blob”，无预生成、无 stub）：删除 `tool_requires("arm-gnu-toolchain/14.2")`，改为配方 `build()` 内 `_ensure_arm_toolchain()`：
  1. 先 `shutil.which` 找宿主已装的 `arm-none-eabi-gcc/as/ld/objcopy`（Debian 系 CI 若自带 gcc-arm-none-eabi 则零下载直接用）；
  2. 缺失时按 `platform.machine()` 选官方 Arm GNU Toolchain 14.2.rel1 包（x86_64/aarch64 双宿主，developer.arm.com 官方地址 + sha256 校验，哈希与 STMicro meta-st-stm32mp / NXP meta-imx Yocto 层交叉一致），`get()` 到 build 目录解压，`bin/` 经 `os.environ PATH` + conanbuild save_script（R33 合规，与既有 compiler_fix 同模式）供给 meson `find_program`。
- 上游构建文件零修改；test_package、MANIFEST.yml 上游无测试审计结论不变。修改保持未提交，待 HMBS 复跑真机预检。

## 真机复检记录（2026-09-20 第三轮，工作树补齐 HMBS 机器证据）
- 对照 rule4 硬门禁与 libm2k 0.9.0 已通过先例，补上本包缺的机器证据输出：`test_package/conanfile.py::test()` 在 ctest 结束后必输出 `HMBS_TEST_PACKAGE_RESULT`（计数源：`CTestTestfile.cmake` 的 `add_test(` 注册数取 discovered，`Testing/Temporary/LastTest.log` 逐节 `Test Passed.`/`***` 结果取 executed/passed/failed，不对 stdout 字符串数数；`passed+failed==executed`、`executed==discovered`、`executed>=1`、`ctest_rc==0` 全满足才判 passed，否则如实失败并附 reason；失败仍先落标记再抛异常，测试失败不吞结果）与 `HMBS_UPSTREAM_TEST_RESULT`（`status:no_tests`、`framework:none`，reason 指向上游无测试审计）。
- 另修主配方 `_package_static_library` 死代码（首循环 `continue` 后同值再判，恒不可达），收拢为单次 walk 首命中即停；`Environment` 上提到顶层 import。
- `.hmbs/pr-body.md` 补充说明同步当前 ARM 工具链方案（构建期直取官方包），去掉已过时的“required:false + 预生成”预案描述；测试计数仍待真机 evidence 回填，不猜测。
- 修改保持未提交，待 HMBS 真机预检。

## 真机复检记录（2026-09-21 第四轮）
- 新失败：上一轮 Environment 链式调用已修复，工具链下载解压成功，但 `meson compile` 在 `flash_write/flash.o` 处失败：`arm-none-eabi-gcc: Permission denied`（ninja code 126）。根因：`get()` 解出的工具链二进制缺可执行位，真机 build 目录位于 HMDFS 上，直接 exec 报 EACCES。
- 新修复（与上轮不同策略，保持官方 GCC 真实编译上游源码）：`_ensure_arm_toolchain()` 在解压后对 `bin/` 与 `libexec/` 下文件做 best-effort `os.chmod 0o755`（HMDFS 上 0o755 落为 0o770，owner 保留 rwx，足够属主执行；`HMBS_CAP_CHMOD=0` 下 chmod 失败仅告警），随后 `os.stat` 打模式日志并用 `arm-none-eabi-gcc --version` 做可执行探针；探针仍失败则抛明示环境错误而非让 ninja 报 cryptic 126。上游构建文件、测试口径不变。
- 修改保持未提交，待 HMBS 真机预检。

## 真机复检记录（2026-09-21 第五轮）
- 新失败：工具链下载解压成功（`Uncompressing arm-gnu-toolchain-14.2.rel1-aarch64-...tar.xz`），chmod 后 `gcc mode 0o750, X_OK=True`，但 `arm-none-eabi-gcc --version` 探针报 `[Errno 13] Permission denied`，conan 直接 `ERROR in build()`。
- 根因确认：`os.access(X_OK)==True` 只看权限位，`execve` 返回 EACCES 是典型的 **noexec 挂载**行为。构建目录在 HMDFS 上（本轮 capabilities：`hardlink=0, chmod=0, symlink=1, local_mktemp=1`，任务独立 TMPDIR 已注入），解压到 `build_folder/arm-gnu-toolchain` 的 ELF 无论怎么 chmod 都无法执行。与上轮“丢执行位”（code 126）不同指纹：上轮是权限位问题，本轮权限位已对（0o750）仍 EACCES。
- 本轮“源码下载失败”摘要具有误导性：日志显示 `conandata` 的 github 归档经 2 次重试后 `Sources correctly downloaded`，失败点在 ARM 工具链探针，不在源码下载。`conandata.yml` 保持官方单 URL 不动：CI 的 `build_and_test.sh` 已有通用镜像映射（github.com → gh-proxy.com + 原地址兜底），构建时自动改写，无需手改（手改还可能触发 R37 版本占用误报）。
- 新修复（与上轮不同策略，仍坚持官方 GCC 从上游源码真实编译 blob，无预生成、无 stub、无测试口径变化）：`_ensure_arm_toolchain()` 改为多候选目录逐个尝试——`$TMPDIR`（HMBS 注入的任务独立可执行候选）→ `~/.cache` → `build_folder`（原行为，健康 CI 保持不变）。每个候选目录独立解压 → best-effort chmod → `--version` 实探针；探针 EACCES 只记 `failures` 并试下一个，不再直接抛错；全部失败才抛明示错误（列出所有尝试过的目录、各自失败原因与 HMBS caps，供后端判 infra）。探针通过的 `bin/` 才经 `os.environ PATH` + conanbuild save_script（R33 合规）供给 meson `find_program`，meson 永远看不到不可执行的工具链。
- 上游构建文件、test_package、MANIFEST.yml（no_tests 审计）均不变。
- 修改保持未提交，待 HMBS 真机预检。

## 真机复检记录（2026-09-22 第六轮）
- 新失败：`Downloading 152.0MB arm-gnu-toolchain-14.2.rel1-aarch64-...tar.xz` 到 6%（9.6MB）时 `Connection to 47.242.172.160 closed by remote host`，构建中断。失败点不在编译本身，而在构建期直取的 ~152MB 官方工具链包下载中途 SSH 会话断开；且旧逻辑每次都下载到全新的任务 TMPDIR（`runtime/.../tmp/...`），成功前每轮都从零重下，暴露窗口大。
- 根因确认：developer.arm.com 实为 302 跳转到 `armkeil.blob.core.windows.net` 同一文件（HEAD 验证），海外单链路慢且易中断；旧 `_ensure_arm_toolchain()` 只有单 URL、无跨轮复用。
- 本轮修复（仍坚持官方 GCC 从上游源码真实编译 blob，无预生成、无 stub、无测试口径变化，sha256 不变）：
  1. 同一文件的三个官方托管地址按序尝试（GitLab 通用包仓库新官方位置 → Azure blob 直链 → developer.arm.com 兜底，均 HEAD 验证 200 且内容长度与官方一致：aarch64 151967360、x86_64 149739784），单地址下载失败自动换下一个并记入 failures；
  2. 两阶段逻辑：先扫描全部候选目录复用已解压且 `--version` 探针通过的工具链（`~/.cache` 持久，成功一次后不再下载）；下载阶段先用 `.libnxt-exec-probe.sh` 小脚本实测各目录可执行性，可执行目录优先，损坏的残留树先清后下。
- 上游构建文件、test_package、MANIFEST.yml（no_tests 审计）均不变。
- 修改保持未提交，待 HMBS 真机预检。

## 真机复检记录（2026-09-26 第七轮）
- 新失败：本轮下载走完 92%（140.6MB，`Sources correctly downloaded`），在 `Uncompressing ... to runtime/libnxt-0.5.2/tmp/libnxt-arm-gnu-toolchain-14.2-aarch64` 后 `Connection closed by remote host`。即第六轮的三 URL + 两阶段复用已生效，但复用从未命中：`_arm_dest_candidates()` 把任务级 TMPDIR 排在 `~/.cache` 之前，且下载阶段稳定排序保持该顺序，可执行目录中 TMPDIR 永远优先；TMPDIR 每轮全新，`~/.cache` 从未被填充，每轮仍付全量 ~152MB 下载 + xz 解压，SSH 窗口最大。
- 根因确认：候选顺序错误导致持久缓存永不填充（本轮 dest 仍是 `runtime/.../tmp/...` 即证据），非单纯网络抖动；与“丢执行位/无执行权限”不同指纹。
- 本轮修复（与上轮不同策略，仍官方 GCC 真实编译 blob，无预生成、无 stub、无测试口径变化，sha256/URL 不变）：`_arm_dest_candidates()` 改为持久缓存优先——`~/.cache` → `$TMPDIR/TEMP/TMP` → `build_folder`；复用扫描与下载阶段均沿此顺序（下载阶段的 exec 探针稳定排序只把不可执行目录沉底，可执行集合内持久缓存仍优先）。一次成功后后续轮次 phase-1 直接复用，零下载零解压。
- 上游构建文件、test_package、MANIFEST.yml（no_tests 审计）均不变。
- 修改保持未提交，待 HMBS 真机预检。

## 真机复检记录（2026-09-26 第八轮）
- 新失败：第七轮的持久缓存优先已生效（本轮 dest 已是 `~/.cache/libnxt-arm-gnu-toolchain-14.2-aarch64`），下载走完 94%（143.4MB，`Sources correctly downloaded`）后仍在 `Uncompressing ...` 处 `Connection closed by remote host`。即瓶颈不在下载选址，而在 `conan get()` 对 ~152MB tar.xz 的全量静默解压（展开约 1GB，含 docs/samples/share，长期间无输出），两次均死在同一步。
- 根因确认：全量解压的 IO/时间窗口 + 全程无日志导致 SSH 会话被收割；换 dest 顺序已无法再缩小该窗口（同一指纹第 3 次，必须换策略）。
- 本轮修复（与前两轮不同策略，仍官方 GCC 真实编译上游 flash_write 源码，无预生成、无 stub、无测试口径变化，sha256/URL 不变）：1) 新增 `_find_system_arm_toolchain()`，对 SDK/harmonybrew/opt/usr 做有界 glob，命中且探针通过则零下载直接用；2) 下载改用 `download()` 落盘到 dest 同级 `.tar.xz`（sha256 校验，`~/.cache` 候选下落盘文件跨轮复用）+ `_slim_extract_arm_tarball()` 只解 `bin/lib/libexec/arm-none-eabi` 四个前缀（flash.o 构建所需），跳过 docs/samples/share，并每 200 成员打一条进度日志，IO 约降至四分之一且 SSH 不再静默。
- 上游构建文件、test_package、MANIFEST.yml（no_tests 审计）均不变。
- 修改保持未提交，待 HMBS 真机预检。

## 真机复检记录（2026-09-26 第九轮，第二策略周期：彻底换路线）
- 新失败：第八轮的免下载探测 + 瘦解压仍未通过，本轮日志 `Calling build()` 后即 `Connection closed by remote host`，且无任何 `arm toolchain:` 日志。上一方案无效的原因有二：1) 第八轮新增的 `_find_system_arm_toolchain()` 含无界递归 glob（`/usr/**/bin/...`、`~/**/bin/...` 会遍历整个 home，含此前解压的约 1GB 工具链），在打印第一条日志前就长时间静默，SSH 会话被收割——即“免下载探测”本身成了新的静默 hang 点；2) 同一根因（构建期获取约 152MB 官方工具链）已连续八轮失败，按策略必须换实现路线而非继续调缓存/解压参数。
- 新路线（与前八轮完全不同：构建期零下载、零解压、零全盘 glob）：不再获取 ARM 工具链。改用上游自带的预编译 NXT flash 驱动——`rvs/libnxt`（上游 SCons 时代树）`flash_write/flash.bin`，git blob `6408eb74376fc353fea21cf8158c0180f7d9eb4c`，136 字节；其 `flash.c`/`crt0.s` 与 schodet 0.5.2 逐项比对逻辑完全一致（同寄存器、同流程，仅空白/版权邮箱差异），且 blob 首字解码为 `0xE3A0D821` 即 crt0.s `_start` 的 `mov sp, #0x210000`，确认为同源真实 ARM7TDMI 驱动。上游发布包曾自带该驱动且 SCons 在缺交叉编译器时自动下载它，本方案只是将其内嵌（base64）到配方、`build()` 写出到源码树，仍经上游 `make_flash_header.py` 生成 `flash_routine.h`——非 stub。
- 改动：1) 新增 `patches/0001-use-prebuilt-flash-driver.patch`（顶层 meson 跳过 `subdir('flash_write')`，改用 `files('flash_write/flash.bin')`；`conandata.yml` 登记）；2) `conanfile.py` 删除 `_ARM_TOOLCHAIN_14_2` 及 `_ensure_arm_toolchain` 全套逻辑（多 URL 下载、持久缓存、瘦解压、无界系统探测），新增 `_provide_flash_bin()`（base64 解码 → 136 字节尺寸断言 → ARM 复位字断言 → 1024 上限断言 → 写出，失败 fast-fail 明示）；宿主编译器 fallback、archiver/pkg-config 注入、签名、test_package 机器证据均不变。
- 上游测试审计（no_tests）、test_package 口径均不变。
- 修改保持未提交，待 HMBS 真机预检。

## 真机复检记录（2026-09-26 第十轮）
- 新失败：`meson.build:1:0: ERROR: Unknown option: "b_thin_archives"`，`meson.configure()` 直接中断。
- 根因确认：Meson 根本没有 `b_thin_archives` 内建选项（Builtin-options 表无此项）。`tc.project_options["b_thin_archives"]="false"` 经 native 文件下发，meson 判未知选项。上游 `static_library('nxt')` 无 `install:true`，meson>=0.60 对未安装静态库默认打 thin 包（`!<thin>`）才是 thin 的真正来源。
- 本轮修复：1) 删除 `tc.project_options["b_thin_archives"]`（generate() 仅保留 `build_doc=disabled`，注释写明禁设原因）；2) 既有 `0001-use-prebuilt-flash-driver.patch` 追加第二 hunk，给 `static_library('nxt')` 加 `install : true`，使 meson 直接产出完整归档；3) `package()` 的魔数判定 + `ar rcs` 重打保留为兜底；`manifest.yaml` 去掉 `-Db_thin_archives=false` 并同步知识条目。
- 上游测试审计（no_tests）、test_package 口径均不变。
- 修改保持未提交，待 HMBS 真机预检。

## 真机复检记录（2026-09-26 第十一轮）
- 新失败：与第十轮同一指纹的第 2 次修复，但失败点不同——`apply_conandata_patches` 报 `extra lines for hunk no.2 at 25` / `Failed to parse patch`。即第十轮的方向（删虚构选项 + 补丁加 install:true）未被 meson 检验到，补丁文件自身先解析失败。
- 根因确认：第二 hunk 头 `@@ -26,3 +33,5 @@` 的新文件行数写错。hunk 体为 3 行上下文（flash_routine_h / dependencies / `)`）+ 3 行新增（2 行注释 + `install : true`），新文件行数应为 6 而非 5。属纯计数笔误，非 install:true 路线本身问题，故不换路线，仅修正 hunk 头为 `@@ -26,3 +33,6 @@`（旧文件 `-26,3` 与新文件起点 `+33` 逐项核对无误：首 hunk 净增 7 行，26+7=33）。
- 上游测试审计（no_tests）、test_package、配方其他逻辑均不变。
- 修改保持未提交，待 HMBS 真机预检。

## 真机复检记录（2026-09-26 第十二轮，evidence/rule4）
- 新失败：`rule4:新增测试不足100%，必须提供具体技术原因及证据（gaps）`，上游 0/0/0，test_package 未达 100% 且标记缺 gaps。
- 根因确认：1) `test_nxt.c` 硬编码 `/tmp/libnxt-test-XXXXXX`，OHOS 真机 /tmp 可能只读（libbf 同款），mkstemp 失败即 ctest 非零；2) `_TEST_START` 仅匹配 `Testing:`，若日志为 `Test #N:` 变体则 executed 漏计为 0；3) `_test_package_marker` 失败时仅写 reason，不发 rule4 要求的 gaps 数组，证据门禁直接判 incomplete。
- 本轮修复：1) `test_nxt.c` 改用 TMPDIR/TMP/TEMP（HMBS 注入）回落 /tmp 的 mkstemp 模板，新增 stdlib.h；2) `_TEST_START` 同时兼容 `Testing:` 与 `Test #N:`；3) 失败标记新增 gaps（count 合计=discovered-passedCount，category 仅 environment/test_failure，evidence 取自 CTestTestfile/LastTest.log 确定性产物，无字符串数数与算术修补）。
- 上游审计（no_tests，total 0）与测试口径不变。修改保持未提交，待 HMBS 真机预检。

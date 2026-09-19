# rvvm 0.6 适配笔记

## 状态

- 阶段：本机前置适配（W0–W4）+ 真机 shadow CI（W5）均已完成，全部门禁通过。
- 构建系统：makefile（GNU Make，上游 `Makefile`）
- 编译器：clang 15.0.4（`tools.build:compiler_executables` 提供，R33）
- 目标平台：HarmonyOS PC（os=OHOS arch=armv8，profile `ci/conan/profiles/ohos-aarch64`）
- Conan 包版本：`0.6`（上游源码 tag `v0.6`，首次适配，无版本递增）

## W0 依赖检查结论

- 依赖数量：0 个 Conan 依赖。
- 已满足依赖：libc / libm / pthread（均由 OHOS musl + LLVM 工具链提供）。
- 缺失依赖：无。
- 是否拆分依赖适配：否。
- 阻塞点：无。
- 下一步：直接进入配方与 test_package。

说明：RVVM 核心完全自包含，上游 Makefile 在 make 时探测 `-lpthread` / `-lrt` /
`-latomic`，OHOS musl 上 pthread 位于 libc，`-lrt`/`-latomic` 探测失败会自动跳过
（`-DNO_LIBATOMIC`）。可选功能（X11/SDL 帧缓冲、Linux TAP、JNI）默认已通过
USE 标志关闭，不引入额外依赖。

## W1 源码与构建系统分析

- 上游仓库：https://github.com/LekKit/RVVM
- Tag：`v0.6`（源码归档 `RVVM/archive/refs/tags/v0.6.tar.gz`，strip_root 后根目录
  `RVVM-0.6/`）
- 许可证：GPL-3.0-only OR MPL-2.0（双许可，`LICENSE-GPL` + `LICENSE-MPL`）
- 语言：C11（`-std=gnu11`），无 C++ 源（非 Windows/Haiku 目标下 `SRC_CXX` 为空）
- 构建系统：GNU Make（`Makefile`），另有 CMake 备选（本配方用 Makefile）
- 构建产物：
  - `make all` → `rvvm`（CLI 可执行文件）
  - `make lib` → `librvvm.so`（共享库）+ `librvvm_static.a`（静态库）
- 公共 API：`src/rvvmlib.h`（`rvvm_create_machine` / `rvvm_write_ram` /
  `rvvm_read_ram` / `rvvm_get_opt` / `rvvm_free_machine` 等），另有 `src/fdtlib.h`。
- 关键构建细节：
  - Makefile 用 `override MAKEFLAGS += -j $(JOBS)` 强制并行；配方传 `JOBS=1`（R9）。
  - `lib`/`install` 目标自动追加 `-DUSE_LIB -fPIC -ffat-lto-objects`（静态库 PIC +
    fat LTO 对象，可被下游共享库吸收，规避 E005）。
  - 静态库规则用 `$(AR)`，配方显式传 `AR`（llvm-ar）以配合 clang thin-LTO。
  - OS 从 `$(CC) -dumpmachine` 的 triplet（`aarch64-linux-ohos`）自动判定为
    linux，ARCH 判定为 arm64（RVJIT arm64 后端可用）。
- 测试审计：
  - `make test` 目标存在，但依赖外部 `riscv-tests.tar.gz`（RISC-V compliance
    测试二进制）与固件（`fw_jump.bin`/`fw_payload.bin`），均不在源码归档内。
  - 结论：上游测试不具自包含性，build() 不执行 `make test`；编译正确性由
    `make lib all` 验证，功能由 test_package 消费者级验证。

## W2 Conan 配方要点

- `package_type = "static-library"`（只打包静态库，避免 Conan 对 `library` 类型
  强制要求 `shared` 选项）；`settings` 含 os/compiler/build_type/arch 四项（L0p）。
- 源码 URL/SHA256 声明在 `conandata.yml`（sources 段），`source()` 用
  `self.conan_data["sources"]` 读取。URL 带 `.tar.gz` 后缀（规避 BadZipFile）。
- SHA256 `97e98c95d8785438758b81fb5c695b8eafb564502c6af7f52555b056e3bb7d7a`
  取自 FreeBSD ports distinfo（codeload tarball for tag v0.6）；真机下载已校验通过。
- `build()`：`make lib all CC=.. AR=.. BUILDDIR=build BINARY=rvvm JOBS=1
  USE_FB=0 USE_SDL=0 USE_XSHM=0 USE_JNI=0 USE_TAP_LINUX=0`（R9/R33）。
- `package()`：只打包 `librvvm_static.a` + `rvvmlib.h`/`fdtlib.h`/`devices/*.h` +
  `rvvm` + LICENSE。**不打包** `librvvm.so`（上游未设 DT_SONAME，会触发 CI L5a）。
- `package_info()`：`cpp_info.libs=["rvvm_static"]`、
  `system_libs=["pthread","m"]`、`bindirs=["bin"]`。
- 因打包 `rvvm` 可执行文件（bindirs 非空），按 R38 在软件级提供 `commands.json`
  （type=tool）。

## W3 test_package

- `test.c`：真实调用 `rvvm_create_machine` / `rvvm_write_ram` / `rvvm_read_ram` /
  `rvvm_get_opt` / `rvvm_free_machine`，验证 6 项（create 非空、写 RAM、读 RAM、
  往返一致、MEM_BASE、HART_COUNT）。R34/L1e：移除 lib/include 后无法编译链接。
- `conanfile.py`：显式校验包内 include/lib 目录存在（防回退系统库），R33 取编译器，
  静态链接 `-lrvvm_static -lpthread -lm`。

## W4/W5 验证结果（本机静态 + 真机 shadow CI）

### 本机静态验证

- Python 语法、YAML/JSON 结构、无 BOM、无尾随空白、`git diff --check` 全通过。
- 变更范围 `origin/main...HEAD` 仅 `archives/r/rvvm/` 9 文件，无基础设施改动。
- 模拟 CI L0 静态门禁（L0m/L0p/L0h/L0o/L0k/L0i）全过。

### 真机 shadow CI（2026-09-16，设备 10.62.178.77:2222）

- 隔离 job：`rvvm-0.6-shadow-20260916`；run id
  `codex-0.6-rvvm-0.6-shadow-20260916-conan-20260916-194144-29838`。
- 首次 run 失败：`Package type is 'library', but no 'shared' option declared`
  （Conan 2 对 `library` 类型强制 shared 选项）。修复：`package_type` 改为
  `static-library`，未改版本号（rvvm/0.6 尚未发布，L0j 确认 first publish）。
- 第二次 run 成功（exit code 0，锁 0s 即得，约 2 分钟完成）：
  - 源码下载 + SHA256 校验通过（GitHub tag v0.6 tarball）。
  - `make lib all`：Detected OS Linux / LLVM Clang 15.0.4 / arm64，全源编译通过
    （仅 `fpu_ops.h` 的 `FENV_ACCESS` pragma 被忽略的警告，无害）。
  - 打包：25 个 .h、`librvvm_static.a`、`rvvm`、LICENSE-GPL/MPL。
  - test_package：`rvvm 0.6 packaged API consumer test ok`。
  - L0=pass, L1=pass, L2=pass（`rvvm --help OK`）, L4=pass（无补丁）, L5=pass。
  - L1e 破坏性反向验证：移走 bin/lib/include 后测试失败，确认真依赖被测包。
- 结论：适配通过 shadow CI 全部门禁，可进入 PR/发布流程（尚未 upload 制品仓，
  manifest 状态保持 built）。

## B 类知识库扩展候选

本库适配中的"Makefile `override MAKEFLAGS` 让命令行 `-j1` 失效"问题已抽象为通用
知识草稿（DRAFT，不预占正式 E 编号）：Makefile 用 `override MAKEFLAGS += -j $(JOBS)`
强制并行时，命令行传 `-j1` 会被覆盖，须改传 Makefile 自定义并行度变量（`JOBS=1`）
才满足 R9 单线程。

- 草稿：`knowledge/drafts/DRAFT-rvvm-make-override-maflags.{kv,md}`
- 真机对照：`rvvm-0.6-shadow-20260916` run 29838，exit 0，`JOBS=1` 编译通过
- 去重：E074 是 make -j FIFO jobserver 卡住、E333 是仓库模板统一 `-j1`，二者均假设
  `-j1` 能生效，未覆盖 `override MAKEFLAGS` 的覆盖机制；E283 是 Conan library 包
  shared 选项契约（rvvm 的 package_type 修复，已被 E283 精确覆盖，故不再重复提交）。
- 新增价值：首次记录 `override MAKEFLAGS` 让命令行 `-j1` 失效的机制与 `JOBS=1` 解法。
- 完整证据：本 notes.md「W4/W5 验证结果」真机 shadow CI 段。

## 下一步（W6/W7）

- 推送 `feat/rvvm-0.6` 分支、创建 PR（单库单 issue 单 PR）。
- 提 PR 后走 release 流水线 `conan upload` 发布 `rvvm/0.6`，再据发布结果把
  manifest/commands.json 的 `binary` 置 true、status 置 published。

## 已知风险与待办（真机已验证部分已闭环）

- ~~L2 冒烟~~：已确认 `rvvm --help` 可用，L2 pass。
- ~~SHA256~~：已由真机下载校验通过。
- L4 安全扫描（readelf NX/PIE/RELRO）属 conan-verify 阶段，本次 shadow CI 未覆盖，
  发布前需在 CI 完整链路复核；上游 Makefile 未显式加 `-fPIE -pie -Wl,-z,relro,-z,now`。
- RVJIT 运行时使用 mmap RWX（JIT），OHOS W^X 策略（E045）可能导致运行期受限；
  编译不受影响，若运行期失败可设 `USE_JIT=0` 回退解释器（本轮未做运行期验证）。
- `ar` 缺失时（E012）可回退 GNU `ar`（`-ffat-lto-objects` 使其兼容）。

## Dependencies

- Runtime/Conan 依赖：无。
- 系统库：libc、libm、pthread（musl）。

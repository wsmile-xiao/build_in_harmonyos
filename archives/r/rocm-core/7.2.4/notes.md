# rocm-core 7.2.4 适配笔记

## 编译环境

- 平台: OpenHarmony / HarmonyOS PC aarch64 (HarmonyOS, 内核 HongMeng 1.12.0)
- 编译器: clang / clang++ 15.0.4 (`/data/service/hnp/bin/clang`,
  target `aarch64-unknown-linux-ohos`)
- CMake: 4.1.2 | Conan: 2.29.1（OHOS 适配版）
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS arch=armv8 compiler=clang 15
  libc++ cppstd=17 build_type=Release）
- 构建系统: CMake
- 包类型: 库（`library`，产出 `librocm-core.a` + 头文件 + CMake 包配置）
- 上游 tag: `rocm-7.2.4`
- 源码 URL: https://github.com/ROCm/rocm-core/archive/refs/tags/rocm-7.2.4.tar.gz
- 源码 SHA256: `32dab2f00e22fb5462beffae03cc642403925d22a42662e15ac0f68d8e885dea`
- 状态: built

## 根因约束：只做主机侧库，不碰 GPU/hipcc

rocm-core 是 ROCm 的基础组件，但它本身**只有主机侧 C++ 代码**（版本查询 +
安装路径查询），不含任何 GPU 设备逻辑。平台工具链与设备事实：

```
$ /data/service/hnp/bin/clang -print-targets | grep -iE 'amdgcn|gcn|radeon'
(无输出 —— 没有 AMDGCN/amdgcn target)
$ /data/service/hnp/bin/clang -print-targets | grep -cE '^    [a-z]'
22                      # 全部为 CPU 后端：aarch64/arm/.../x86-64，无 GPU 后端
$ ls /dev/kfd /dev/dri
ls: /dev/kfd: No such file or directory
ls: /dev/dri: No such file or directory
```

结论：OHOS clang 只有 aarch64 等 CPU 后端，**不注册 AMDGCN**；设备也没有
`/dev/kfd`、`/dev/dri`。因此本配方**只调用普通 OHOS C++ 工具链编译主机侧库**，
不尝试任何 GPU/hipcc 配置，不发明设备代码路径。

## 编译步骤

```bash
export PATH=$HOME/.local/bin:/usr/bin:$PATH
REPO="/storage/Users/currentUser/Documents/main/build_in_harmonyos-main (2)/build_in_harmonyos-main"

# 1) 直接构建（等价于任务给定的 create 命令）
cd "$REPO/archives/r/rocm-core/7.2.4"
conan create . \
  -pr:h="$REPO/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$REPO/ci/conan/profiles/ohos-aarch64" \
  --build=missing
# -> exit 0；层 1（ctest 轨迹）+ 层 2（test_package 31/31）均执行

# 2) 配方验证（G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify rocm-core 7.2.4

# 3) 收尾（W2 结构 + R36 依赖 + W3 本地 CI，写 .ci-result.json）
python3 scripts/ohc-run.py finish rocm-core 7.2.4 built
```

配方本身的构建配置：
- `-DROCM_VERSION=7.2.4`（上游 `utils.cmake` 的 `parse_rocm_version()` 依赖它
  推导 `VERSION_MAJOR/MINOR/PATCH`）。
- `-DBUILD_SHARED_LIBS=OFF`（默认静态；详见"源码修改"节的说明）。
- 无补丁、无外部依赖，`apply_conandata_patches()` 为空操作。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 在 `build()` 里报 `Makefile Error 2: No rule to make target 'test'`（`cmake.test()` 失败） | conan 的 `CMake.test()` 执行 `cmake --build <dir> --target test`；上游 CMakeLists **从不调用 `enable_testing()`**，所以生成的 Makefile 没有 `test` 目标 | 在 `generate()` 里写一个顶层 include 文件 `rocm-core-enable-testing.cmake`（内容仅 `enable_testing()`），通过 `CMAKE_PROJECT_INCLUDE` 注入。这样 `test` 目标存在，ctest 能运行（上游注册 0 用例），日志出现 ctest 轨迹 |
| 2 | 若原样打包，`bin/` 下会出现上游 python 工具，令 `conan-verify` 的 L2 smoke test 失败 | conan/OHOS 安装布局把 `CMAKE_INSTALL_LIBEXECDIR` 映射到 `bin/`，上游把 `rdhc.py`/`runpath_to_rpath.py` 装到 `${LIBEXECDIR}/rocm-core`（即 `bin/rocm-core/`）并建 `bin/rdhc` 软链；`rdhc.py` 需要 prettytable/PyYAML（OHOS 无），`--version`/`--help` 均以 exit 1 退出 | `package()` 中删除整个 `bin/`、`libexec/`、`share/rdhc/` 树；库包保持纯库（`lib/` + `include/` + CMake 配置），L2 因无 bin/ 直接通过 |
| 3 | 构建日志出现 `make: jobserver mkfifo: /storage/.../tmp/GMfifoNNNN: Operation not permitted` | `TMPDIR`（$HOME/tmp，HMDFS）不允许 `mkfifo`，GNU make 的 jobserver FIFO 无法建立 | 非致命：make 退化为非 jobserver 模式继续构建，编译/链接/打包全部成功。仅记录为平台限制 |
| 4 | 配置阶段出现 `fatal: not a git repository` | 上游 `set_variables()` 用 `git merge-base` / `git rev-parse` 探测版本；源码是解压出来的 tar 树，非 git 仓库 | 非致命：`VERSION_HASH` 回退为 `unknown`、`VERSION_COMMIT_COUNT`=0，`ROCM_BUILD_INFO` 变为 `7.2.4.0-9999-unknown`（层 2 已断言其前缀为 `7.2.4`） |
| 5 | 配置/构建日志出现 `Problem parsing /proc/meminfo` | CMake/make 在 OHOS 上探测 `/proc/meminfo` 的格式差异 | 非致命，不影响任何构建步骤 |
| 6 | `conan-verify` 的 G4 显示 `⚠️ 无法找到程序包 ID`，随后 L2/L4/L5 显示"跳过（无 cache 路径）" | 框架 `gate4_artifact_integrity` 以 `listing["Local Cache"][self.software]` 取值，而 `conan list "rocm-core/7.2.4@ohpcd/stable:*"` 的 JSON 键是**带 user/channel 的完整引用**（`rocm-core/7.2.4@ohpcd/stable`），故取不到包 ID。这是框架的取值约定（read-only，未修改） | 非阻塞：G0-G4 判据仍全部 PASS。L2/L4/L5 因无 cache 路径被跳过；L2 的实质验证已由 `conan create` 的层 2 consumer 测试覆盖（真跑 `./test_rocm_core`） |
| 7 | **无效入参导致崩溃**：`getROCmVersion(NULL,…)` / `getROCmInstallPath(NULL,…)` 不返回错误码，而是**段错误（SIGSEGV，退出码 139）** | 公共头把这两个 API 声明为 `ATTRIBUTE_NON_NULL` = `__attribute__((nonnull))`，于是 clang 从 `-O1` 起可合法假定出参永不为 NULL，把上游 `rocm_version.cpp` / `rocm_getpath.cpp` 里的 `NULL_CHECK` 守卫**优化删除**。Release（-O3）产物的汇编直接写穿指针：`mov x8,x0; mov w9,#7; str w9,[x8]`（`rocm_version.cpp` 的 `getROCmVersion`）。实测对照：同一份源码 -O0 返回 `VerIncorrectParameters`(1)，-O3 崩溃 | 在 `generate()` 注入的顶层 include 里加 `add_compile_options(-fno-delete-null-pointer-checks)`（与 `enable_testing()` 同一文件，经 `CMAKE_PROJECT_INCLUDE` 在 `project()` 之后、所有目标声明之前生效）。加旗标后同一 -O3 构建恢复上游契约：三个 NULL 出参 → `VerIncorrectParameters`(1)，两类 NULL 入参组合 → `PathIncorrecPararmeters`(-994)。**未改动上游源码**。注：上游自己的 `set(CXX_FLAGS ...)`（`CMakeLists.txt:91`）是普通变量、从未应用到任何目标，故不能用作注入点 |

## 源码修改

**零补丁、零源码修改。** 上游源码树按原样使用，仅由 conan 通过 CMake toolchain
传入 `ROCM_VERSION` 与 `BUILD_SHARED_LIBS` 两个变量。`conandata.yml` 无 `patches` 段。

静态库选择说明：上游默认 `BUILD_SHARED_LIBS=ON`，本配方默认 `OFF`（可通过
`-o rocm-core/*:shared=True` 切换）。静态产物让这个体量极小、职责单一的辅助库
自包含，且 `getROCmInstallPath()` 在 `BUILD_SHARED_LIBS=0` 分支下确定性地读取
`ROCM_PATH`（共享分支要 `dlopen` 自省，在打包目录里更脆弱）。

## 依赖版本

无。配方 `requirements()` 为空，`conanfile.py` 中无任何 `self.requires(...)` /
`self.tool_requires(...)`（rocm-core 是自包含 CMake 项目）。

## 层 1 / 层 2 测试

- **层 1（上游测试）**：rocm-core 7.2.4 **不附带任何测试**，注册 0 个 ctest 用例。
  计数依据（三处一致）：① `tar tf rocm-core-rocm-7.2.4.tar.gz | grep -i test` → 0；
  ② `grep -Rn "add_test|enable_testing|include(CTest)" CMakeLists.txt utils.cmake` → 0；
  ③ 配置后 `ctest --test-dir <build>` → `No tests were found!!!`。
  配方仍在 `build()` 末尾调用 `cmake.test()`，日志出现
  `cmake --build ... --target test` → `Running tests...` → `ctest` →
  `No tests were found!!!` 的完整轨迹。
- **层 2（test_package）**：`test_package/test_rocm_core.cpp` 真实链接 `librocm-core`
  并调用导出的 C API，**31 条断言全部执行、全部通过**。上游不附带测试，故本层同时
  承担"补全测试"职责：除正常路径外，覆盖了该库返回值枚举存在的**全部可达错误/边界
  路径**（NULL 出参、NULL 入参、`ROCM_PATH` 未设置/为空/超长、失败时的出参重置契约、
  尾斜杠怪癖）——详见下方"层 2 断言覆盖"。

- **鸿蒙特有测试（完整消费者端到端用例，rule 12）**：`test_package/test_rocm_core_ohos.cpp`
  为 OHOS 目标专属（CMake 选项 `ROCM_CORE_TEST_OHOS` + 源码 `#ifndef __OHOS__ #error`
  双重约束），3 个具名用例均为完整端到端流程（构造输入 → 调用包内 API → 用返回数据
  做真实文件 I/O → 产出可校验结果），**不是断言集合**：
  - **HC-1 安装树发现与真实产物消费**：`ROCM_PATH` 指向部署前缀 →
    `getROCmInstallPath()` 解析安装根 → 用解析出的根做真实文件 I/O（读
    `.info/version`、校验 `librocm-core.a` 的 ar 魔数、读 CMake package config 与
    公共头文件）→ 与运行时 `getROCmVersion()` 交叉校验（无部署漂移）。
  - **HC-2 下游版本门禁决策流程**：按最低版本要求（≥7.2.0 / ≥7.2.4 / ≥7.3.0 /
    ≥8.0.0）执行门禁判定并输出 GO/NO-GO → 输出 `printBuildInfo()` 诊断横幅 →
    写出决策记录文件并读回校验内容。
  - **HC-3 安装根重定位流程**：部署一棵重定位安装树（自带版本标记）→ 切换
    `ROCM_PATH` 后 API 跟随新根并读回重定位标记 → 切回原树确认无陈旧解析。
  实测 **3/3 用例通过（35 项内部检查，0 失败）**。

## 验证结果（实测）

```text
# a) conan create（exit 0）
$ conan create . -pr:h=<profile> -pr:b=<profile> --build=missing   -> RC=0
  [层1] cmake --build ".../build/Release" --target test
        Running tests... / ctest / "No tests were found!!!"   (上游 0 用例)
  [层2] ======== Testing the package: Executing test ========
        RUN: ./test_rocm_core
        rocm-core consumer checks: 31 executed, 0 failed
        RUN: ./test_rocm_core_ohos <prefix> <workdir>
        == complete consumer flows: 3/3 cases passed (35 checks, 0 failed) ==

# b) conan-verify（verdict PASS）
$ python3 scripts/ohc-run.py conan-verify rocm-core 7.2.4        -> RC=0
  G0: PASS   G1: PASS   G2: PASS   G3: PASS   G4: PASS
  (L2/L4/L5: 因框架 cache-path 取值约定被跳过，非配方缺陷 —— 见问题 #6)
  报告: archives/r/rocm-core/7.2.4/reports/conan-verify-report.md
```

实测计数：
- 上游用例数：**0 / 0**（不附带测试，见层 1 计数依据）
- test_package 断言：**31 执行 / 31 通过**（0 失败）
- 鸿蒙特有测试（完整消费者用例）：**3 / 3 通过**（35 项内部检查，0 失败）
- conan create：**exit 0**
- conan-verify：**PASS（G0-G4）**

### 层 2 断言覆盖（31 项，全部实测执行）

上游 rocm-core 7.2.4 **不附带任何测试**，因此按交付要求自行补全。补全原则是：
该库的公开 API 只有两个函数，而它们的返回值**整体就是一组错误码枚举**
（`VerErrors` / `PathErrors_t`），所以补全不能只测正常路径——把枚举取值的每一条
**可达分支**都断言到：

**A. 正常路径（保持原有 14 项，未删除、未弱化）**
`getROCmVersion()` 返回 `VerSuccess`；`major/minor/patch` 分别等于
`ROCM_VERSION_MAJOR/MINOR/PATCH`；版本恰为 7.2.4；`ROCM_BUILD_INFO` 前缀为
`7.2.4`；`printBuildInfo()` 返回 `VerSuccess`；`getROCmInstallPath()` 在
`ROCM_PATH=/opt/rocm` 下返回 `PathSuccess`、路径为 `/opt/rocm/`、`len==strlen`、
`len==10`；第二次以 `ROCM_PATH=/usr/lib/rocm` 调用返回 `PathSuccess` 且反映更新后的
值（证明无残留静态缓冲）。

**B. 错误/边界路径（本次补全新增 17 项）**

| 场景 | 断言结果（实测） |
|------|------------------|
| `getROCmVersion(NULL, &n2, &n3)` | `VerIncorrectParameters`(1) |
| `getROCmVersion(&n1, NULL, &n3)` | `VerIncorrectParameters`(1) |
| `getROCmVersion(&n1, &n2, NULL)` | `VerIncorrectParameters`(1) |
| `getROCmInstallPath(NULL, &nlen)` | `PathIncorrecPararmeters`(-994) |
| `getROCmInstallPath(&p, NULL)` | `PathIncorrecPararmeters`(-994) |
| `getROCmInstallPath(NULL, NULL)` | `PathIncorrecPararmeters`(-994)（校验 `InstallPath` 先判） |
| `ROCM_PATH` 未设置（静态构建） | `PathLinuxRuntimeErrors`(-998) |
| 失败时出参重置契约 | `*InstallPath` 置 `NULL`、`*InstallPathLen` 置 `0`（用哨兵值验证，排除悬垂指针/残留长度） |
| `ROCM_PATH=""`（空串） | `PathLinuxRuntimeErrors`(-998)，出参同样重置 |
| `ROCM_PATH` 超长（8191 字节 > `RC_PATH_MAX-1`，`PATH_MAX=4096`） | `PathValuesTooLong`(-996)，出参同样重置 |
| `ROCM_PATH="/opt/rocm/"`（尾斜杠） | `PathSuccess`，路径 `/opt/rocm//`、`len==11` |

这些断言依赖问题 #7 的 `-fno-delete-null-pointer-checks`：不加该旗标时，前三类
NULL 出参/NULL 入参调用会让测试二进制直接段错误（退出码 139），而不是返回错误码。
测试源码内已写明该依赖关系，防止后人"顺手"删掉旗标。

## W3 本地 CI 模拟结果（finish step [5/10]，实测）

`ci/conan/setup.sh` + `ci/conan/build_and_test.sh archives/r/rocm-core/7.2.4`
（完整日志 `reports/w3-local-ci.log`，33960 字节）：

```text
G0_RESULT=pass        (知识图谱完整性检查通过，541 entries)
KC_RESULT=pass        (知识库质量门禁)
JC_RESULT=pass        (无杂项文件)
L0_RESULT=pass: all checks passed
                      R37 版本未占用(首次发布) / R38 纯库无需 commands.json /
                      L0m 目录结构合规 / L0p settings 四项齐全；
                      R36 依赖检查：配方零 requires，无依赖需查 -> 通过
L1_RESULT=pass: upstream tests + test_package executed
                      L1a test_package executed
                      L1b test execution evidence found
                      L1c ctest executed in build phase
                      L1e 破坏性反向验证：确认测试真实依赖 rocm-core
L2_RESULT=skip: no bin/ dir          (纯库包，正确跳过 smoke test)
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content     (library package)
Build Summary: Total 1 / Success 1 / Failed 0 / Pass rate 100.0% (1/1)
层 2 实测: "rocm-core consumer checks: 31 executed, 0 failed"
            "complete consumer flows: 3/3 cases passed (35 checks, 0 failed)"
```

`.ci-result.json`（由 finish 自动写入，未手工修改）：
`exit_code=0`，`step=W3_local_ci`，`integrity_hash=fb98726eff771268`，
`log_sha256=644b02dd836b9255139c32ae0e99690901a667263515a90edb0281c13423b2f8`。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | CMake 配方；settings 四项齐全；build() 调 cmake.configure/build/test；package() 产出纯库 |
| `conandata.yml` | 官方 GitHub 源 + SHA256，无补丁 |
| `test_package/conanfile.py` | 层 2 入口，`test()` 用 `self.run(exe, env="conanrun")` |
| `test_package/CMakeLists.txt` | CMakeDeps 消费者工程，链接 `rocm-core::rocm-core` |
| `test_package/test_rocm_core.cpp` | 真实调用 C API 的 31 条断言（正常路径 14 + 错误/边界 17） |
| `test_package/test_rocm_core_ohos.cpp` | 鸿蒙完整消费者端到端用例（HC-1/HC-2/HC-3，仅 OHOS 构建） |
| `test_package/MANIFEST.yml` | 上游测试声明（含 0 用例计数依据 + 鸿蒙用例计数） |
| `manifest.yaml` / `notes.md` | 版本元数据 / 本笔记 |
| `reports/` | `conan-verify-report.md`、`conan-create.log`、`w3-local-ci.log` |
---

**编译结束**: 2026-10-12 10:46
**最终状态**: built

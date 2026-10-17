# simde 0.8.4-rc3 适配笔记

## 编译环境
- 软件：simde 0.8.4-rc3（header-only 跨架构 SIMD 可移植库）
- 上游仓库：https://github.com/simd-everywhere/simde（标签 `v0.8.4-rc3`）
- 上游 tarball：`simde-0.8.4-rc3.tar.gz`
  sha256 `a5407985439fef1435ac1f091a4d2e6c71981faed213e1be156aca575ce7052c`
  （官方直链 `github.com/.../archive/refs/tags/v0.8.4-rc3.tar.gz` 与镜像路径分别下载，
  两次 sha256 一致；tarball 顶层目录 `simde-0.8.4-rc3`，gzip magic 1f8b）
- 构建系统：meson（`meson setup -Dtests=true`；项目内声明版本号 0.8.4）
- 设备：HarmonyOS PC / aarch64-linux-ohos
- 编译器：clang 15.0.4 / clang++ 15.0.4（`/data/service/hnp/bin`）
- 工具链：meson 1.12.0、ninja 1.13.1、cmake 4.1.2、Conan 2.29.1
- Python：`/data/service/hnp/bin/python3` 3.12.8
- 编译日期：2026-09-10
- 状态：built

## 产物形态

simde 是纯 header-only 库，上游 meson 只做头文件安装与 pkgconfig 生成，没有任何编译产物。
本配方按 `package_type = "header-library"` 打包：

```text
include/simde/**/*.h   472 个头文件（与上游 tarball 逐字节一致，零漂移）
licenses/COPYING       MIT 许可证
```

`package_info()` 声明 `includedirs = ["include"]`，并提供 CMakeDeps 属性
`cmake_file_name = simde` / `cmake_target_name = simde::simde`，与上游 meson 的
`declare_dependency(version: 0.8.4)` 语义对应。

## 上游测试清点与全量执行（R51）

### 取数口径

- 注册入口（case）计数命令：`meson setup build -Dtests=true && meson test -C build --list`
  —— 实测 **2014 个**注册入口。
- 断言（assertion）计数：meson `protocol: 'tap'` 运行日志中 `ok <N>` 行累计
  —— 实测 **32710 条**，`not ok` **0 条**。
- 统计单位：**meson 注册入口**（等价于「测试源文件 × 语言(c/cpp) × 实现路径(emul/native)」
  的组合矩阵；common 族为 1 个源文件 × c/cpp 两种语言 = 2）。

上游 `test/meson.build` 逐族注册规则（注册数与 TAP 断言数均按实际运行日志逐块核对）：

| 族 | 注册入口 | TAP 断言 | 说明 |
|---|---:|---:|---|
| common | 2 | 10 | `common.c` 1 个源文件 × c/cpp 两种语言 |
| arm/neon | 1132 | 16536 | `simde_neon_families` 287 族，排除 ld3/ld4/st1/ld1 后 283 族 × c/cpp × emul/native |
| arm/sve | 28 | 688 | `simde_sve_families` 14 族，排除 7 个 native-only 族后 7 族 × c/cpp × emul/native |
| x86（mmx…aes，17 个） | 68 | 6572 | 每族 × c/cpp × emul/native |
| x86/avx512 | 472 | 7624 | `simde_avx512_families` 118 个族 × c/cpp × emul/native |
| wasm_simd128 | 240 | 1052 | 60 个族 × c/cpp × emul/native |
| wasm_relaxed_simd | 28 | 68 | 7 个族 × c/cpp × emul/native |
| mips_msa_simd | 44 | 160 | 11 个族 × c/cpp × emul/native |
| **合计** | **2014** | **32710** | |

TAP 断言按族分布（对 `meson-logs/testlog.txt` 逐块统计）：arm 族最多，共 **17224** 条
（arm/neon 16536 + arm/sve 688）；x86 族 **14196** 条（17 族 6572 + avx512 7624）；
wasm 族 **1120** 条（simd128 1052 + relaxed 68）；mips 族 **160** 条；common **10** 条。
各族按族内向量类型与参数化用例生成数量不等的断言。

### 执行命令与结果

```sh
meson setup "$TASK_DIR/build-ohos" -Dtests=true   # Build targets 2518
meson test -C "$TASK_DIR/build-ohos" --list       # 注册入口 2014
ninja -j4 -C "$TASK_DIR/build-ohos"               # 4532/4532 目标，RC=0
HOME="$TASK_DIR/test-home" meson test -C "$TASK_DIR/build-ohos" \
    --print-errorlogs --num-processes 2
```

实测结果（meson 只打印非零计数项，故设备摘要本身只有前两行；Timeout/Skipped/
Unexpected Pass 经日志全文核对确为 0）：

```text
Ok:                2014
Fail:              0
MESON_TEST_RC=0
```

- 2014/2014 注册入口全部通过，通过率 100%；`not ok` 计数为 0（TAP 层面同样零失败）。
- 本轮设备 load average 20–35，为安全采用 `-j4` 编译与 `--num-processes 2` 运行，
  不改变用例集合。
- 按 workflow §7.3 在沙箱 HOME 下执行（`HOME=$TASK_DIR/test-home`）：simde 测试不需要
  密钥/数据准备，沙箱内无任何主目录写入。
- 运行前后未修改任何上游测试文件（见下节「源码修改」）。

### 上游测试与 munit 子模块（E150 等价命中）

上游 `test/test.h` 只在**非** `SIMDE_TEST_BARE` 分支包含 `munit/munit.h`
（第 1192–1207 行：「The bare version basically assumes you just want to run a single
test suite. It doesn't use munit, or any other dependencies」）。而 meson 的**全部**
注册入口都显式携带 `-DSIMDE_TEST_BARE`（`test/common`、`test/x86`、`test/arm/neon`、
`test/arm/sve` 的 `meson.build` 均如此），只有 CMake 侧的 `test/run-tests.c` 聚合
runner 才需要 munit。

官方 release tarball 中 `test/munit/` 是空目录（子模块未随 tarball 发布，等价 E150
现象），但按上述注册方式不影响全量 `meson test`：本任务未补任何子模块、未改任何
上游文件即跑完 2014/2014。simde 0.8.2 的历史归档曾按 E150 从 munit master 补文件做
抽样测试；0.8.4-rc3 的实测证明该补充对 meson 路径非必需。

### ARMv8 CRC（与 0.8.2 归档的差异说明）

simde 0.8.2 的归档记录了 `crc32-native-c` / `crc32-native-cpp` 两个入口在
**默认 aarch64 配置**下未构建。0.8.4-rc3 的 `arm/neon/meson.build` 已经不再把
`crc32` 列入排除名单（排除项为 ld3/ld4/st1/ld1），本包实测注册入口 1132 个中
包含 `arm/neon/crc32/{emul,native}/{c,cpp}`，两者均在默认配置下**已构建并通过**，
无需额外 `-march=armv8-a+crc` 专项配置。

## 消费者验证（test_package）

`test_package/` 构建并真实运行 3 个消费者程序，全部链接包安装产物
（`find_package(simde REQUIRED)` + `simde::simde`），共 **76 项运行期断言，0 失败**：

| 消费者 | 断言 | 覆盖内容 |
|---|---:|---|
| `test_simde`（C） | 45 | NEON 便携接口（vld1q/vaddq_s8/vabdq_s16/vceqq_s32/vmulq_s32/vmaxq_s16/vaddq_f32/vgetq_lane）、跨 ISA 便携路径（SSE2 `simde_mm_add_epi32`、wasm `simde_wasm_i32x4_add`、MIPS MSA `simde_msa_addv_w`）在 aarch64 上的回退实现、版本宏与向量类型尺寸 |
| `test_simde_cpp`（C++） | 16 | C++ 模式下的同类 API（对应上游 c/cpp 双语言注册面），确认头文件在 C++ 编译环境可用 |
| `test_native`（原生别名） | 15 | `SIMDE_ENABLE_NATIVE_ALIASES` 下短名接口与 `simde_` 前缀接口结果逐字节一致；`SIMDE_ARM_NEON_A64V8_NATIVE` 已定义（原生 A64 NEON 路径生效）；simde 向量类型与 arm_neon.h 原生类型同尺寸 |

实测输出（`conan create` 的 test_package 阶段）：

```text
platform: aarch64, SIMDE_ARCH_ARM_NEON=1000 SIMDE_ARCH_AARCH64=1000
simde test_package (C): 45 checks, 0 failures
simde test_package (C++): 16 checks, 0 failures
SIMDE_ARM_NEON_A64V8_NATIVE=1 (expected 1)
simde test_package (native aliases): 15 checks, 0 failures
100% tests passed, 0 tests failed out of 3
```

### OHOS aarch64 原生 NEON 能力取证

「simde 在 OHOS 上真的走原生 NEON 而不是标量模拟」不只靠宏断言，另取编译器产物证据：
以 `-O0 -DSIMDE_ENABLE_NATIVE_ALIASES` 编译 `test_native.c`，用 `llvm-objdump -d`
反汇编消费者可执行文件，确认生成真实 NEON **向量**指令（非标量回退）：

```text
add  v0.16b, ...     (vaddq_s8  原生别名路径)
smax v0.4s, ...      (vmaxq_s32 原生别名路径)
mul  v0.8h, ...      (vmulq_u16 原生别名路径)
```

三个消费者 ELF 均为 AArch64 PIE + NX + Full RELRO
（`Type=DYN`、`GNU_STACK` RW、`GNU_RELRO` 存在、`BIND_NOW`）。

## 源码修改

**无。** 本任务未对上游源码、构建脚本或测试文件做任何修改，`patches/` 为空，
`conandata.yml` 的 `patches:` 为空映射。OHOS/aarch64 无需平台条件编译或等价改写：
simde 的 ISA 探测（`simde-features.h` / `simde-arch.h`）在 OHOS 上按标准
`__aarch64__` + `__ARM_NEON` 宏路径即正确识别原生 NEON。配方中
`export_conandata_patches()` / `apply_conandata_patches()` 为 G1 完整性要求保留
（零补丁时为 no-op）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `meson test` 在沙箱 HOME 下报 `No module named 'mesonbuild'` | meson 由 user site 安装（`~/.local/bin/meson`），切换 HOME 后 user site 解析随 HOME 变化 | 沙箱内显式注入 `PYTHONPATH=<真实 user site>`；**未**为测试安装任何新包，也未修改全局 Python 环境 |
| 2 | 设备 `/tmp` 只读且内存紧张（31G 中已用 26–27G，load 20–35） | 设备环境限制 | 全部临时目录使用 `$HOME/tmp/simde-0.8.4-rc3`；编译降为 `ninja -j4`、测试 `--num-processes 2`，不使用 `/tmp` |
| 3 | 全工作区所有 Git 仓库报 `dubious ownership` | 并发任务向共享 `$MAIN_REPO/.gitconfig` 追加了**空值** `safe.directory = `，git 把空值视为清空该多值键，使全部 safe.directory 条目失效 | 删除该空行恢复（快照存 `$TASK_DIR/gitconfig.before-repair`）；env 文件内用 `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n` 注入本任务所需两条 safe.directory 作为等价防护。已写入反馈（属容器层工具/流程问题，不进本 PR） |

## 依赖版本

无运行/编译依赖。配方 `requirements()` 为空；`meson.build` 只探测可选的 `libm`
（`cc.find_library('m', required: false)`）与可选的 SLEEF/OpenMP，均不影响头文件消费。

## 验证结果

```text
编译状态                     通过（meson setup -Dtests=true + ninja 4532/4532，RC=0）
上游测试用例通过率           2014/2014 = 100%（TAP 断言 32710 ok / 0 not ok）
消费者（新增）测试通过率     3/3 程序 = 100%（76 checks / 0 failures）
```

## 交付物

- `conanfile.py`、`conandata.yml`
- `manifest.yaml`（版本级）
- `test_package/`（`conanfile.py`、`CMakeLists.txt`、`test.c`、`test_cpp.cpp`、
  `test_native.c`、`MANIFEST.yml`）
- `notes.md`
- `reports/`（本机生成的验证日志与 W4 审计结果，受 `.gitignore` 的 `reports/`
  规则忽略，**不进入 PR**；`reports/test-report.md`、`.staging-verified` 属
  submit 阶段产物，本任务按 `built` 收尾故未生成）

## 注意事项

- 版本 slug `0.8.4-rc3` 满足 Conan `ConanName` 校验（`^[a-z0-9_][a-z0-9_+.-]{1,100}$`，
  且长度 ≥2），无需 `set_version()` 归一化；目录、分支名与配方版本三者严格一致
  （CI L0m/L0n 门禁）。
- 上游标签是预发布版 `v0.8.4-rc3`，项目内 `meson.build` 声明 `version: '0.8.4'`；
  本包版本按任务卡/上游标签取 `0.8.4-rc3`，未做版本号改写。
- `conandata.yml` 全文件除 `sources.url` 外无裸 http(s) URL，避免 CI 预下载器无边界抓取。

---

**编译结束**: 2026-09-10
**最终状态**: built

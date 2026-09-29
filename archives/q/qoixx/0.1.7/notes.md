# qoixx 0.1.7 适配笔记（依赖项任务 · 平台 id 14461 · 分支 feat/qoixx-0.1.7）

## 官方来源核验（2026-09-29 设备实测）

- 上游仓库：`wx257osn2/qoixx`（QOI「Quite OK Image Format」单头 C++20 编解码库），任务版本 tag `v0.1.7`。
- **三路取证一致**：
  1. `git ls-remote --tags <上游仓库>`：全量 **8 个 tag（v0.1.0 … v0.1.7）逐条命中**，
     `refs/tags/v0.1.7 = 542881c370dce466dbd6b95329a2217f360c707d`；
  2. 本地下载 tag 归档（**19770 字节**）`sha256 = 9da53e0fc035f4b75f872a196a76cd870b63568612254035dadc84e46f47d779`；
  3. CCI `conan-center-index` 的 `recipes/qoixx/all/conandata.yml` 中 `"0.1.7"` **同值**。
- 许可证 MIT（根 `LICENSE` + `LICENSES/{qoi,stb,doctest}.LICENSE`）；解包 **279K**；
  交付物 `include/qoixx.hpp`（54335 字节 / 1400 行）。
- 上游构建面：裸 `Makefile`（无 configure），三个目标 `bin/qoibench`、`bin/qoiconv`、`bin/test`。

## W0 立项预检

- **W0-2 依赖：0 conan 依赖** —— `bash ci/scripts/preflight_check.sh qoixx/0.1.7`
  → `预检通过（无依赖需要检查）`；配方 `requirements()` / `build_requirements()` 双零。
- 上游 `.gitmodules` 的三个子模块 **不随 tag 归档交付**（解包后 `.dependencies/{doctest,qoi,stb}`
  三个目录全空）：
  - `doctest` = 上游测试框架头，tag v0.1.7 树上 pinned `ae7a13539fb71f270b87eb2e874fbac80bc8dda2`
    （`git ls-remote` 实证该 commit 即 doctest tag `v2.4.11`，且两者的 `doctest/` 目录逐字节一致）
    → 按 doctest 官方 tag 归档进 `conandata.yml` 预下载（sha256 `632ed2c0…`）；
  - `qoi` / `stb` 只服务上游基准/转换工具，**不进配方**（本包不打包工具，见「未运行项」）。
- **W0-3 平台可移植性（架构可移植性档 · 三步裁量）**：
  1. **分桶**：`arm_sve.h` / `arm_neon.h` / `immintrin.h` 三处 include 全在
     `include/qoixx.hpp` 顶部，且全部处于 `#ifndef QOIXX_NO_SIMD` +
     `#if defined(__ARM_FEATURE_SVE) / #elif defined(__ARM_NEON) / #elif defined(__AVX2__)`
     条件块内（`QOIXX_NO_SIMD` 可整体关闭）；无捆绑子树、无 `#if 0` 死块命中；
     `printf.h` / `register_printf_*`（glibc printf 钩子族）与 `__GLIBC__` /
     `gnu_get_libc` **均 0 命中**。
  2. **编译探针**（设备 clang 15.0.4 / aarch64-unknown-linux-ohos）：
     `#include <qoixx.hpp>` 默认编译 **rc=0**；`-DQOIXX_NO_SIMD` 编译 **rc=0**；
     预处理探针打印 `__ARM_NEON defined -> NEON fast path active`
     （`__AVX2__`、`__ARM_FEATURE_SVE` 均未定义 ⇒ x86/SVE 分支不在本机构建面）。
  3. **构建面实证**：配方 `conan create` 内 `make bin/test` 单条编译行无任何 ISA 头报错，
     上游 38 条断言全过（见下）。
  ⇒ 判「非止损」，继续配方适配。

## 编译环境

- 构建系统: makefile（上游裸 Makefile，无 configure；prescan `build_systems=[make]`）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（OHOS 工具链，profile `ci/conan/profiles/ohos-aarch64`）
- 标准库: libc++ 15.0.4（`_LIBCPP_VERSION=15004`）
- 状态: built（O5：合并 + release upload 确认前不标 published）

## 编译步骤

配方 `source()` → `build()` → `package()`（`conan create` 全程）：

1. `source()`：下载主源（tag 归档，strip_root）+ 预下载 doctest 2.4.11 到
   `.dependencies/doctest`（先移除 tag 归档留下的空子模块占位目录，路径与上游 Makefile 的
   `DOCTEST=-I .dependencies/doctest/doctest` 完全一致），并断言 `doctest/doctest.h` 落位。
2. `build()`（沙箱 HOME `build/test-home` 下执行上游测试，层 1 必做）：
   ```sh
   make clean
   make -j1 CXX=/data/service/hnp/bin/clang++ \
        CXXFLAGS='-std=c++2a -O2 -Wall -Wextra -pedantic-errors -fexperimental-library' bin/test
   ./bin/test   # 输出落盘 + 回显 + 透传真实退出码
   ```
   之后**反假绿硬断言**：日志必须命中 `test cases:  2 |  2 passed` 与
   `assertions: 38 | 38 passed`，且不得出现 `All 0 tests`，任一不符即让 `conan create` 失败。
3. `package()`：交付 `include/qoixx.hpp` + `licenses/`（根 LICENSE 与 LICENSES/ 三个许可证）。
4. `test_package/`：消费者从**已安装包** include 头，CMake 编译后 `self.run()` 直跑二进制。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 归档解包后 `.dependencies/` 三个子模块目录全空，`make test` 缺 `doctest.h` | GitHub tag 归档不含 git submodule 内容（`.gitmodules` 只给 URL、不带文件） | 按 pinned commit（= doctest 官方 tag v2.4.11）把 doctest 归档进 `conandata.yml`，`source()` 解到上游 Makefile 期望的 `.dependencies/doctest`，不动上游构建面；`qoi`/`stb` 不进配方 |
| 2 | `src/test.cpp` 用 `std::ranges::copy`，设备编译报 `no member named 'copy' in namespace 'std::ranges'` | OHOS libc++ 15.0.4 的 ranges 算法默认关闭（探针：`-std=c++20` 下 `<algorithm>` 不提供 `std::ranges::copy`；`-fexperimental-library` 打开后 rc=0 且真跑通过） | 加编译旗标 `-fexperimental-library`（上游测试与上游工具都需要），**不 patch 上游测试源**，上游用例一字未改 |
| 3 | 上游 Makefile 默认 `CXXFLAGS=-march=native` | 设备与 CI worker CPU 不同，`-march=native` 结果不可复现 | 配方显式覆盖 CXXFLAGS（`-std=c++2a -O2 -Wall -Wextra -pedantic-errors -fexperimental-library`）；**NEON 快路径不依赖该旗标**（aarch64 基线特性，`__ARM_NEON` 默认定义） |
| 4 | `bin/qoiconv` 在 clang 15 下编译失败：`overloaded` 推导指引 `no matching constructor` | clang 15 与上游 CI 所用 clang-17 的 CTAD/继承构造推导差异（`template<typename...Fs> overloaded(Fs...) -> overloaded<Fs...>;`） | qoiconv **不是交付物**（本包 header-only、不进 commands.json），不打包不测试；如实记入「未运行项」 |
| 5 | 0 补丁包仍需满足 G1 文本门禁的「补丁应用调用」 | `conan_verify.py` G1 纯文本检查 `apply_conandata_patches` 字样、无 package_type 例外 | 配方保留 `export_sources()` + `build()` 内 `apply_conandata_patches(self)`（`patches: {}` 时是 no-op），不伪造补丁 |

## 源码修改

**0 个补丁，上游源文件一字未改**（`patches_applied: []`，`patches: {}`）。
所有平台差异用编译旗标与配方逻辑解决（问题 2/3），因此 PR 不含任何 `patches/*.patch`，
也就没有 PF5 平台宏风险面。

## SIMD 快路径判定（本任务重点提示项）

- `include/qoixx.hpp` 的 `arm_sve.h` / `arm_neon.h` / `immintrin.h` 全是条件 include，
  由 `__ARM_FEATURE_SVE` / `__ARM_NEON` / `__AVX2__` 选择，并受 `QOIXX_NO_SIMD` 总开关控制
  （README：*「When you don't want to use SIMD implementation … use `QOIXX_NO_SIMD`»*）。
- **本平台实测裁决：保留 SIMD 快路径，不加 `QOIXX_NO_SIMD`。**
  - 探针：`__ARM_NEON defined -> NEON fast path active`（`__AVX2__`、SVE 未定义）；
  - `encode_neon`（`qoixx.hpp:604`）随默认旗标进入构建面，编译 rc=0；
  - NEON 快路径下上游 doctest **38/38 断言全过**（encode/decode × 3ch/4ch 往返逐字节比对，
    NEON 编码结果与期望字节流完全一致）；
  - `-DQOIXX_NO_SIMD` 也能编译通过（可移植性备用开关可用，本包不需要）。
- 交付头保持上游默认行为：消费者以默认旗标编译即使用 NEON 快路径。

## 依赖版本

| 组件 | 版本 | 角色 |
|---|---|---|
| qoixx | v0.1.7（sha256 9da53e0f…） | 交付头 |
| doctest | 2.4.11（上游子模块 pinned） | **仅上游测试**，进 conandata 预下载，不进 requires |
| clang / libc++ | 15.0.4 | 设备与 CI 同源工具链 |
| cmake | 4.1.2 | 仅 test_package |
| conan | 2.29.1（OHOS 适配版） | 配方运行时 |

## 验证结果

```bash
# 1) 上游测试（配方 build() 内，沙箱 HOME）
$ ./bin/test
[doctest] doctest version is "2.4.11"
[doctest] test cases:  2 |  2 passed | 0 failed | 0 skipped
[doctest] assertions: 38 | 38 passed | 0 failed |
[doctest] Status: SUCCESS!            # rc=0，TOTAL=PASS 38 / FAIL 0 / SKIP 0 / NOT_RUN 0

# 2) 消费者测试（test_package，从已安装包 include）
$ ./test_qoixx
QOIXX-CONSUMER checks=14 failures=0   # rc=0，鸿蒙特有测试 14/14

# 3) 完整链（采信轮 conan-verify 的 conan create，见 reports/conan-create.log）
$ conan create <包目录> -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<同>   # rc=0
```

计数口径与 N 候选数法（源码宏 2 / 框架注册 2 / SUBCASE 16 / 断言 38 / 消费者 14）
与逐项差额归因见 `test_package/MANIFEST.yml`；两表见 `reports/test-report.md`。

## 未运行项（如实申报，不压分母）

1. **上游 CI 的外部数据集集成循环**（`.github/workflows/linux.yml` 的 `test` 步骤前半）：
   下载 `qoiformat.org` 的 `qoi_test_images.zip` + `qoi_benchmark_suite`、用
   `.dependencies/qoi` 子模块编译参考 `qoiconv`，再与 `../bin/qoiconv` 逐图 diff。
   **NOT_RUN**，原因有据：①被测 `bin/qoiconv` 在本设备 clang 15 下编译失败（问题 4，
   错误原文 `no matching constructor for initialization of 'overloaded<…>'`）；
   ②数据集需外网下载且不在仓库测试入口 `make test` 内、不产生测试用例计数。
2. **`bin/qoibench`（基准工具）**：加 `-fexperimental-library` 后本机可编译，但它是性能
   基准而非测试入口，不打包、不进上游用例分母。

## 状态

- 候选提交后按工作区 §3.3 走**采信轮**固序（inode 预检 → 清缓存四步 → `conan-verify` →
  证据三副本 → finish 前快照），干净轮证据以 `reports/conan-create.log`、
  `reports/conan-verify-report.md`、`reports/test-report.md` 为准；
- manifest `status: built`（O5 口径：合并 + release upload 确认前不标 published）。

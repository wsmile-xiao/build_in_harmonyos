# volk 3.3.0 测试报告（HarmonyOS PC / aarch64）

> **项目**: GNU Radio VOLK 3.3.0（HarmonyOS PC 适配，Conan 配方，**0 补丁**）
> **测试日期**: 2026-09-28
> **测试环境**: HarmonyOS PC / HongMeng Kernel 1.12.0 / aarch64；
> OHOS SDK 26.0.0.18 hnp clang 15.0.4（libc++ / `-D__MUSL__`）；
> cmake 4.1.2；ninja 1.13.1（探索）/ Unix Makefiles（conan）；conan 2.29.1（OHOS 适配版）；
> Python 3.12.8 + mako 1.4.3；依赖 fmt/11.1.3（ohpcd 制品仓，OHOS armv8）
> **测试类型**: 上游官方 ctest 套件（R51）+ 消费者 test_package（R34/R53）
> + conan-verify G0–G4 + W3 本地 CI L0–L5

---

## 一、测试摘要

### 1.1 上游官方测试（R51，ctest，lib/ 内核 QA）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 N | 154 | 100% |
| 实际运行 N′ | 154 | 100% |
| 通过 (PASS) | 154 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

- **清点**：`ctest -N` → `Total Tests: 154`（`qa_volk_*`，`lib/CMakeLists.txt`
  对每个 kernel 注册；`volk_test_all` 在同一 kernel 的 generic/neon/neonv8
  实现间做一致性/容差比较）。
- **实跑命令**：`ctest --output-on-failure -j2`
  （`LD_LIBRARY_PATH` = 构建树 `lib/` + fmt 包 `lib/`）。
- **结果**：`100% tests passed, 0 tests failed out of 154`，退出码 0。
- **耗时**：66.20s（探索轮，日志 `~/runner/volk-ctest.log`）；conan create 内
  同套件同样 154/154（日志 `reports/conan-create.log`）。
- **说明**：仓库 `tests/` 子目录的 GoogleTest 套件因制品仓无 GTest 按上游
  逻辑跳过（上游 `tests/CMakeLists.txt`：`if(NOT fmt_FOUND OR NOT GTest_FOUND) return()`），
  **不计入 N**。

### 1.2 消费者测试（test_package，R34 + R53）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 断言总数 | 7 | 100% |
| 断言通过数 | 7 | 100% |
| 断言失败数 | 0 | 0% |

R53 断证明细（conan create 内实际执行，程序输出 `ASSERTIONS: 7, FAILURES: 0`）：

| # | 断言 | 实测值 | 结果 |
|---|------|--------|------|
| 1 | `volk_get_machine()` 返回非空（运行期 SIMD 分发） | `neonv8` | ✅ |
| 2 | `volk_get_alignment() >= sizeof(void*)` | 16 | ✅ |
| 3 | `volk_get_alignment()` 为 2 的幂 | 16 | ✅ |
| 4 | `volk_malloc()` 返回非空缓冲 | 2 缓冲 | ✅ |
| 5 | `volk_malloc()` 满足请求对齐（`(uintptr_t)%alignment==0`） | — | ✅ |
| 6 | `volk_32f_s32f_multiply_32f()` 1024 点乘标量全部在 tol 1e-4 内 | 0 失配 | ✅ |
| 7 | `VOLK_VERSION_MAJOR/MINOR/MAINT == 3/3/0` | 3.3.0 | ✅ |

鸿蒙特有校验（同一 test_package `test()` 内**实际执行**）：

| # | 校验项 | 结果 |
|---|--------|------|
| H1 | `llvm-readelf -S <pkg>/lib/libvolk.so.3.3.0 \| grep -q codesign`（OHOS ELF 加载器强制要求，E077；缺签名则运行期 `Operation not permitted`） | ✅ |

### 1.3 配方验证（conan-verify G0–G4）与 W3 本地 CI（L0–L5）

| 项目 | 结果 | 证据 |
|------|------|------|
| conan-verify G0 预构建风险评估 | ✅ PASS | `reports/conan-verify-report.md` |
| conan-verify G1 配方完整性 | ✅ PASS | 同上 |
| conan-verify G2 干净构建（conan create：下载→configure→build→154/154 ctest→install→test_package） | ✅ PASS | `reports/conan-create.log` |
| conan-verify G3 系统同名库隔离（R26） | ✅ PASS | 同上 |
| conan-verify G4 产物完整性 | ✅ PASS（工具明细提示"无法找到程序包 ID"） | 人工复核 `reports/conan-verify-supplement.md` |
| conan-verify L2/L4/L5 | ⚠️ 框架跳过（`--user/--channel` reference 无法回解析 package ID） | 人工等价复核：`reports/conan-verify-supplement.md` |
| W3 本地 CI L0（结构/依赖门禁） | ✅ pass | `reports/w3-local-ci.log` |
| W3 本地 CI L1（上游测试 + test_package 执行证据 + L1e 破坏性反向验证） | ✅ pass | 同上 |
| W3 本地 CI L2 smoke（`volk-config-info --version` OK） | ✅ pass | 同上 |
| W3 本地 CI L4（补丁安全扫描） | ✅ pass | 同上 |
| W3 本地 CI L5（bin/ 产物基线） | ✅ pass | 同上 |
| W3 `.ci-result.json` | ✅ `exit_code=0`（`2026-09-28T12:09:32.726708`），`log_sha256=4c56fb89d040145fc3019467296f659e6eb1ef3b681d2bd0a54b3eb48435a8ae`（`integrity_hash=4f49fd89a72a68e8`） | `archives/v/volk/3.3.0/.ci-result.json` |

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**：上游 ctest 154/154（100%）、test_package 7/7 断言 + 鸿蒙
`.codesign` 校验通过、conan-verify G0–G4 PASS、W3 本地 CI L0–L5 全 pass
（`exit_code=0`）。

### 2.2 可用功能清单

```
✅ libvolk.so.3.3.0（SONAME libvolk.so.3.3）SIMD 内核分发 generic/neon/neonv8
✅ 运行期 CPU 特性探测（cpu_features 内置子模块真实编译启用）
✅ volk_get_machine()/volk_get_alignment()/volk_malloc()/volk_free() 公共 API
✅ 154 个 kernel 的 generic/neon/neonv8 多实现一致性（上游 QA 全过）
✅ bin/volk-config-info（--version/--machine 免 LD_LIBRARY_PATH，RUNPATH=$ORIGIN/../lib）
✅ bin/volk_profile（需 Conan runenv 提供 libfmt.so.11，属依赖链正常形态）
✅ bin/volk_modtool + lib/python3.12/site-packages/volk_modtool
✅ CMake 包配置（Volk::volk）与可重定位 pkg-config（volk.pc 用 ${pcfiledir}）
```

### 2.3 已知限制

1. ORC 加速关闭：上游 `ENABLE_ORC` 默认 ON，但制品仓 `orc/0.4.42` 未提供
   `orcc` 工具（tools disabled），`FindORC` 必然失败；本包显式 `ENABLE_ORC=OFF`，
   不影响其余 kernel 与 SIMD 分发。
2. fmt 版本替换：上游 FetchContent 钉 `fmt 10.2.1`，制品仓无该版本；改用
   `fmt/11.1.3` + fmt 官方兼容开关 `FMT_DEPRECATED_HEAVY_CORE`（等价恢复
   fmt 10 的 `<fmt/core.h>` 行为），上游源码 0 修改、0 补丁。
3. 上游 `tests/` 目录 GoogleTest 套件（非 lib/ CTest 主套件）因制品仓无 GTest
   未构建，属上游可选测试，不影响 R51 主套件。
4. 无静态库：上游 3.3.0 仅 `add_library(volk SHARED ...)`，本包按上游默认
   只提供动态库。
5. `volk_profile` 直接运行需 Conan runenv（链接 `libfmt.so.11`）；`volk-config-info`
   自带相对 RUNPATH 可独立运行。`volk_modtool` 依赖系统 `python` 别名，
   W3 L2 单列为 non-blocking warn。

---

## 三、测试详情

### 3.1 上游 ctest 通过记录（154/154，节选）

```
Test   #1: qa_volk_16i_32fc_dot_prod_32fc ....................... Passed
...
Test #152: qa_volk_8u_x3_encodepolar_8u_x2 ...................... Passed    0.04 sec
Test #153: qa_volk_8u_x3_encodepolarpuppet_8u ................... Passed    2.09 sec
Test #154: qa_volk_8u_x4_conv_k7_r2_8u .......................... Passed    0.05 sec

100% tests passed, 0 tests failed out of 154
Total Test time (real) =  66.20 sec
```

单 kernel 冒烟（探索轮）：
`volk_test_all volk_32f_s32f_multiply_32f` → generic/u_neon/neonv8 三份实现
时间与误差表，rc=0。

### 3.2 test_package 实跑输出（conan create 内）

```
volk machine: neonv8
volk alignment: 16
PASS: volk_get_machine() reports the selected machine
PASS: volk_get_alignment() >= pointer size
PASS: volk_get_alignment() is a power of two
PASS: volk_malloc() returns buffers
PASS: volk_malloc() honours the requested alignment
PASS: volk_32f_s32f_multiply_32f() multiplies 1024 samples
PASS: VOLK_VERSION macros are 3.3.0
ASSERTIONS: 7, FAILURES: 0
RUN: "/data/service/hnp/bin/llvm-readelf" -S ".../p/lib/libvolk.so.3.3.0" | grep -q codesign
```

### 3.3 L2/L4/L5 手工等价复核摘要（完整见 `reports/conan-verify-supplement.md`）

- **G4 产物**：194 文件 —— `lib/libvolk.so.3.3.0`（+ `.so`/`.so.3.3` 软链）、
  173 个公共头、`lib/cmake/volk`、可重定位 `volk.pc`、`bin/{volk-config-info,
  volk_profile,volk_modtool}`、volk_modtool python 包、`licenses/COPYING`；
  无 fmt 泄漏（依赖走制品仓）。
- **L2**：`<pkg>/bin/volk-config-info --version` → `3.3.0`、`--machine` → `neonv8`
  （免 LD_LIBRARY_PATH）；W3 的 L2 亦 pass。
- **L4**：三个 ELF 均 `DYN`（PIE/共享库）、`GNU_STACK RW`（NX）、`GNU_RELRO`
  + `BIND_NOW=1`、`.codesign`=1、`RUNPATH=$ORIGIN/../lib`。
- **L5**：GNU Radio VOLK 首个本地包，无旧基线；记录 sha256：
  `libvolk.so.3.3.0=f994c579da6d0fd4308c3afd32430870210497504a109cf07114d83ddb82c6f4`、
  `volk-config-info=ec7f16d78152ad276638ee918dcfe972420284b7b8803eaf5637d491049228ae`、
  `volk_profile=6841851a5a9c42dc4500de6fd712ee0cbae44007689dc15f9687deb612d4b0f2`、
  `volk.pc=0949ba3b0f61607f735f6d9dc0035932d4631afa4b340f9cce3d4d1b94c4963a`。
- **E537 复验**：`libvolk.so.3.3.0` 的 `DT_NEEDED` 仅 `libc.so`；消费者
  `test_volk` 的 `DT_NEEDED`=`libvolk.so.3.3`（SONAME）+`libc.so`，无 Conan
  cache 绝对路径泄漏。

---

## 四、测试环境与配方信息

```
设备:   HarmonyOS PC / HongMeng Kernel 1.12.0 / aarch64
工具链: OHOS SDK 26.0.0.18 hnp clang 15.0.4 / libc++ / -D__MUSL__
构建:   cmake 4.1.2 + Unix Makefiles（conan create）/ ninja 1.13.1（探索）
Conan:  2.29.1（OHOS 适配版）；profile ci/conan/profiles/ohos-aarch64
Python: 3.12.8 + mako 1.4.3（recipe build() 内确定性安装）
依赖:   fmt/11.1.3（ohpcd 制品仓，OHOS armv8）
配方:   archives/v/volk/3.3.0（0 补丁；源码官方 GitHub v3.3.0 release）
上游:   gnuradio/volk 3.3.0（LGPL-3.0-or-later）
```

---

*报告生成时间: 2026-09-28*

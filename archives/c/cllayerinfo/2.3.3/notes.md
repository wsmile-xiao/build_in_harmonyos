# cllayerinfo 2.3.3 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-10-12
- 编译器: clang/clang++
- 状态: built
- 目标平台: HarmonyOS PC（OHOS aarch64，三元组 `aarch64-unknown-linux-ohos`，设备原生编译）
- 包管理: conan 2.29.1（OHOS 适配版，来自鸿蒙社区 PyPI 源）
- 构建工具: autoconf / automake / libtool（`tool_requires`）、ruby 3.4.5（`ruby` 生成 OpenCL dispatch 表）

## 包定位

`cllayerinfo` 与 `ocl-icd`（OpenCL ICD Loader）**同一源码树**：它是 `ocl-icd` 2.3.3
tag 归档根目录下的 CLI 工具（`bin_PROGRAMS`），用于枚举当前进程可见的 OpenCL 层。
本包只交付工具本体；`libOpenCL.so`、OpenCL 头文件与 `.pc` 由 `archives/o/ocl-icd`
交付，避免同名 SONAME 由两个包各自持有（消费者链接会冲突）。

## 编译步骤

1. `init-build` 取上游 tag 归档（`v2.3.3.tar.gz`，sha256 `8cd8e8e1…`），归档**不含**
   `configure`/`config.h.in`/dispatch 表等生成物，构建期自举。
2. `conan create archives/c/cllayerinfo/2.3.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`：
   - `generate()`：`AutotoolsToolchain` 注入 `--build/--host=aarch64-unknown-linux-ohos`（E007）
   - `build()`：`os.umask(0o022)` → `apply_conandata_patches`（无补丁）→ `autoreconf()`
     → 修 `configure` 内嵌 `umask 077`（E011）→ `configure` → `make -j2`
     → `make check`（上游套件）→ 打印上游测试上报标记
   - `package()`：`make install` 后裁剪 `include/lib/lib64/libexec/share`，只留 `bin/cllayerinfo`
     与 `licenses/COPYING`
3. 交付物校验：`bin/cllayerinfo` 存在且 0755，`readelf -d` 仅 `libc.so`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 报出 `could not setup config files machinery`，并伴随写 `subs1.awk` 的 Permission denied | HMDFS 上 autoconf 模板的 `(umask 077 && mktemp -d)` 建出 0700 临时目录，UID 映射后当前进程不可写（E011） | 构建期把 `configure` 内嵌 `umask 077` 收敛为 `022`（conan `replace_in_file`；configure 属构建期生成物，不做补丁） |
| 2 | `config.guess` 报 `unable to guess system type` | 上游 `config.guess` 无 HarmonyOS/`__OHOS__` 分支（E007） | 显式钉住三元组 `--build=--host=aarch64-unknown-linux-ohos` |
| 3 | 归档无 `configure`，无法直接构建 | 上游 tag 归档不含生成物（R51） | `Autotools.autoreconf()` 自举；automake/libtool 走 `tool_requires`，dispatch 表生成需系统 `ruby` |
| 4 | 上游测试上报误判 `no_tests` | 上游 `make check` 直接跑 `tests/testsuite`（原生 autotest），计数只在日志横幅 `All 31 tests were successful.`，没有 automake 并行驱动的 `# TOTAL:` 汇总块 | 解析器兼容两种格式：优先 `# TOTAL:`，未命中回退解析 autotest 横幅，并与 `tests/*.at` 的 `AT_SETUP` 清点交叉校验（12+16+3=31） |
| 5 | 只导出 `OPENCL_LAYERS` 时 `cllayerinfo` 输出为空 | loader 中 `__initLayers()`（读 `OPENCL_LAYERS`）位于 `if (_num_icds == 0) goto abort;` 之后，无有效 ICD 时层根本不加载 | 消费者测试同时提供 dummy ICD（`test_icd.c` → `vendors/dummy.icd`）与 dummy 层（`test_layer.c`），复刻上游 `testsuite-standard.at` 的用例条件 |

## 源码修改

无补丁（`patches/` 为空，`patches_applied: []`）。全部适配差异通过构建期参数/生成物修复解决：

| 目标 | 位置 | 内容 |
|------|------|------|
| E011 | 构建期生成的 `configure` | `umask 077` → `umask 022`（不改上游源码，不入补丁） |
| E007 | conan 工具链参数 | `--build/--host=aarch64-unknown-linux-ohos` |

> 说明：`configure` 由 `autoreconf` 在构建期生成，不是上游发布的源码文件，因此按知识库
> E011 的处置在构建期改写；上游 source 未被修改。

## 依赖版本

- 运行时依赖：**无**（零 C/C++ 依赖；工具内联 loader 源码，仅链接 `libc`）
- 构建期依赖（`tool_requires`，非运行时）：
  - `automake/1.18`、`libtool/2.5.4.1`（autoreconf 自举链）
- 同源码树的运行期配套（由 `archives/o/ocl-icd` 交付，本包不重复提供）：
  - `libOpenCL.so`（ICD Loader）、`CL/*.h` 头文件、`OpenCL.pc`
- 系统侧：`ruby`（生成 OpenCL dispatch 表）、`clang/clang++`

## 验证结果

```bash
# 1) 上游测试（conan create 内 make check）
$ make check
All 31 tests were successful.

# 2) 消费者测试（test_package，真实执行 bin/cllayerinfo）
$ conan create archives/c/cllayerinfo/2.3.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
passedCount: 3/3
cases: no_icd_no_layer_exit0, icd_without_layer_prints_nothing, enumerate_dummy_layer

# 3) 层枚举实测输出（消费者用例 3）
$ OPENCL_LAYERS=<build>/libtestlayer.so OCL_ICD_VENDORS=<build>/vendors cllayerinfo
CL_LAYER_API_VERSION: 100
CL_LAYER_NAME: dummylayer

# 4) 交付物
$ readelf -d <pkg>/bin/cllayerinfo | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

取证明细见 `reports/test-report.md`（上游 31/31、消费者 3/3、staging 部署校验）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/cllayerinfo` | CLI 工具本体（ELF，OHOS aarch64，仅依赖 libc） |
| `licenses/COPYING` | 上游 BSD-2-Clause 许可证 |
| `commands.json` | 命令声明（`cllayerinfo`） |

## 注意事项

- 本包与 `archives/o/ocl-icd` **同源码树**，两者版本线应一致；若将来上游拆包，需同步复核本配方。
- 消费者若同时依赖本包与 `ocl-icd`，不应把本包当作 `libOpenCL` 提供者（本包 `cpp_info.libdirs` 为空）。
- `configure` 的 umask 修复依赖自举顺序（`autoreconf` 之后、`configure` 之前）；若上游
  autoconf 模板变更（不再出现 `umask 077`），配方会打印告警而不失败。

## 对话记录

### 对话 #1 2026-10-12 cllayerinfo 2.3.3 适配（HarmonyOS PC）

**W0/W0b 预检与历史核验**
- 上游确认为 `https://github.com/OCL-dev/ocl-icd`（BSD-2-Clause，cllayerinfo 为其同树 CLI 工具），
  版本 2.3.3，语言预检 = c（任务语言 cpp，符合）。
- 制品仓已归档 `ocl-icd/2.3.5`、`2.3.5.1`（历史配方同为 autotools + `make check` + 层枚举用例），
  逐项对比后本包沿用其结论并补齐 cllayerinfo 作为独立命令的消费者验证。

**W3 编译与自举**
- init-build 下载 `v2.3.3.tar.gz`（sha256 `8cd8e8e129db3081a64090fc1252bec39dc88cdb7b3f929315e014b75069bd9d`），
  确认 tag 归档无 `configure`。
- 第一次 `configure` 失败于 `could not setup config files machinery`（E011 命中）：
  HMDFS 上 `umask 077` 建出的 0700 临时目录跨 UID 不可写。修复为构建期 `umask 077` → `022` 后通过。
- `config.guess` 不识别 HarmonyOS（E007），改用显式三元组。

**W3 测试**
- 上游 `make check`：`All 31 tests were successful.`（清点 12+16+3 = 31，一致）。
- 首次消费者测试输出为空 → 定位到 loader 的 `_num_icds == 0` 提前返回（层初始化在其后），
  补 dummy ICD 后 3/3 全过，输出 `CL_LAYER_API_VERSION: 100` / `CL_LAYER_NAME: dummylayer`。

**W2 收尾**
- `ohc-run.py finish`：conan-verify（G2）PASS、W3 本地 CI 模拟 PASS、知识完整性 PASS、submit 就绪。
- G0 干净构建在 `configure` 处失败属**预期行为**（G0 不执行 `build()`，无法获得 autoreconf
  生成的 `configure` 与 E011 构建期修复），框架已按 `replace_in_file` 识别并放行，完整构建由 G2 覆盖。
---

**编译结束**: 2026-10-12 15:12
**最终状态**: built

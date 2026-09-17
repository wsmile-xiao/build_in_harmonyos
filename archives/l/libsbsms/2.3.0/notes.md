# libsbsms 2.3.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 `.github/workflows/build.yml` 的官方路径）
- 编译日期: 2026-09-15
- 编译器: clang / clang++ 15.0.4（OHOS SDK 26.0.0.18）
- 目标: OpenHarmony / HarmonyOS PC，aarch64，`ci/conan/profiles/ohos-aarch64`
- 状态: built

## 版本与源码
- 源码: `https://github.com/claytonotey/libsbsms/archive/refs/tags/2.3.0.tar.gz`
- sha256: `4f88d152bc06fedbda9d5d65517d40254a7310c9050601a93122309d45afd2c9`
  - 两次独立下载（设备 curl，450111 字节，gzip magic `1f 8b`）逐字节一致。
- 顶层目录: `libsbsms-2.3.0/`
- 上游 tag 只有 `2.3.0` / `2.2.0` / `2.1.0`，本版本为最新。
- 说明：Debian copyright 的 `Source:` 亦指向该 GitHub 仓库；`sbsms.sourceforge.net`
  与 `download.savannah.nongnu.org/releases/libsbsms/` 都已是失效的历史主页/下载区
  （Savannah 两个候选 URL 实测 404，见下文“问题 2”）。

## 依赖
无。`src/Makefile.am` 与 `CMakeLists.txt` 均只编译自身 11 个 `.cpp`，不 link 任何外部库；
Debian 的 `libsndfile1-dev` 构建依赖只服务于 Debian 自己打包的示例/测试程序，而
上游 2.3.0 仓库并不包含这些程序。W0 预检结论：`预检通过（无依赖需要检查）`。

## 编译步骤

```sh
# 原生探索（设备 clang，无 Conan）
cmake -S <src> -B <build> \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=<prefix> \
      -DCMAKE_CXX_COMPILER=clang++ \
      -DCMAKE_SYSTEM_NAME=OHOS -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_INSTALL_LIBDIR=lib
cmake --build <build> --parallel 2
cmake --install <build>

# 配方验证（采信轮）
sh tools/conan_verify_round.sh libsbsms 2.3.0 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
```

`--parallel 2`：本机 `os.cpu_count()=20` 而 affinity 只有 8、`MemFree` 仅约 0.9 GB
（device-facts §一.5/§一.7），必须显式限并发。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `CMake Error: Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 3.1)`，worker 的 CMake 为 4.1.2，已移除 <3.5 兼容 | recipe 用 **cache** 变量 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（E187/E321）。不能用 `tc.variables`：它写进 `conan_toolchain.cmake`，而该文件在 `cmake_minimum_required()` **之后**才被 include，故无效 |
| 2 | `System is unknown to cmake, create: Platform/HarmonyOS`，产物 `libsbsms.so` **无 DT_SONAME** | `os=OHOS` 被 Conan 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 没有 `Platform/HarmonyOS.cmake`，`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 为空 → `SOVERSION`/`VERSION` 属性被静默丢弃 | recipe 显式设 `CMAKE_SYSTEM_NAME=OHOS` + `CMAKE_SYSTEM_PROCESSOR=aarch64`：worker CMake 4.1.2 与 OHOS SDK CMake 3.28 **都自带** `Modules/Platform/OHOS.cmake`（内容仅 `include(Platform/Linux)`），于是恢复 `-Wl,-soname,`，实测得到 `SONAME: libsbsms.so.2` |
| 3 | autotools 路径不可靠 | commit 里同时有 autotools（`configure`/`Makefile.in`/`config.guess`/`config.sub`），但 `configure.ac` 的 `AC_INIT` 仍写 **2.2.0**、`LIBSBSMS_RELEASE_*` 写 2.1.0，`sbsms.pc` 版本与 libtool `-version-info` 都是陈旧的；prescan 另报 PSCAN-BUILD-001/102（老 `config.guess` 不认 ohos 三元组） | 选 CMake：版本号 2.3.0 正确（`project(sbsms VERSION 2.3.0)`）、是上游 CI 的实际路径，且完全不需要改 `config.guess/config.sub` |
| 4 | 自研消费者测试一开始把 `audio` 当成“实部/虚部”复数 | `typedef float t_fft[2]; typedef t_fft audio;` 是**按通道**的样本数组；`channels=2` 时 `[0]/[1]` 是左/右声道。mono（channels=1）只写/读 `[0]`，`[1]` 是未被库触碰的缓冲区垃圾 | 测试只校验通道 `[0]`；同时改用库自带的 `SBSMSQualityStandard`（其 `bands=8,H=3`、`getFrameSize()=384`），不再照搬 main 分支 `example/` 的参数表（那套参数在 2.3.0 上会崩溃，属更新版本的表） |
| 5 | 同配方两轮构建的 `lib/pkgconfig/sbsms.pc` 内容不同（**独立审计对首版产物的实测**：8 个交付产物只有 7 个一致） | 上游 `CMakeLists.txt` 用 `configure_file(sbsms.pc.in)` 生成该文件，把 `CMAKE_INSTALL_PREFIX`（=当轮的 Conan 包目录，如 `…/p/b/libsb698b9c997c655/p`）写死在 `prefix=` 行；目录名每轮重建，文件随之不同 | `package()` 的 `_make_pkgconfig_relocatable()` 把该行改写为 `prefix=${pcfiledir}/../..`：pkg-config 会展开 `${pcfiledir}`，`../..` 从任意安装位置都解析到包根。改写后两轮 8/8 产物与整树逐字节一致（实测见 `reports/conan-verify-supplement.md` §5.3） |

## 知识沉淀与路径判定

本版本的四个技术点全部**命中既有知识**，没有产生新的可复用条目，因此按路径 A
（基础适配）交付，不新增 `knowledge/drafts/` 草稿：

| 技术点 | 既有知识 |
|---|---|
| CMake 4.x 拒绝 `cmake_minimum_required(<3.5)` | `E187`（add-cmake-flag）；`DRAFT-E321`（明确 `tc.variables` 无效、必须 `cache_variables`） |
| `CMAKE_SYSTEM_NAME=HarmonyOS` 无平台模块 → SONAME 标志为空 | `DRAFT-cmake-harmonyos-platform-soname-flag`（根因链完整，含「存在 `Platform/OHOS.cmake`，其全文仅 `include(Platform/Linux)`」）；`E092`/`E140`/`E267`（平台名识别） |
| 选 CMake 规避老 `config.guess/config.sub` | `E007`；prescan 规则 `PSCAN-BUILD-001`/`PSCAN-BUILD-102` |
| 源码 URL 必须带显式 `.tar.gz` 后缀 | `E276` |

本草稿口径的差异值得单独说明：既有草稿 `rec_approach` 是**手工注入**
`CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"`；本配方改用
**选平台名**（`CMAKE_SYSTEM_NAME=OHOS`）让 CMake 自己从
`Platform/OHOS.cmake → Platform/Linux.cmake` 取到该标志。后者是同一根因下的第三种
写法（与仓内已发布配方 `archives/l/libvpl/2.16.0` 一致），并且顺带修好了
`check_function_exists(lrint)`（实测只在 `OHOS` 下被检出）。因为根因、适用范围与
验证命令都已被既有草稿覆盖，新增条目会构成重复，故不再申报；差异仅在本节与
`manifest.yaml` 的 `knowledge_gained` 中留痕。

## 源码修改

无源码补丁。本版本零补丁：**提交面不含 `patches/`，没有任何补丁文件**；`conandata.yml`
的 `patches: {}` 为空，W3 的 L4 亦为 `pass: patches clean`。（复验流水线会在本地重建一个
空的 `patches/` 工作目录，它未被 git 跟踪、不属于提交面，与"零补丁"结论并不矛盾。）
唯一对交付文件的加工在 `package()` 内（改写生成物 `sbsms.pc` 的 `prefix` 行为可重定位，
见问题 5），不涉及上游源码。

## 上游测试

**上游 2.3.0 没有任何测试**（清点证据见 `reports/upstream-test-inventory.md`）：
- `tar tzf` 共 72 项，无 `test/`、`tests/`、`testing/` 目录；
- `find . -iname '*test*'` 零命中；`find . -iname '*check*'` 仅命中 `m4/ax_check_compiler_flags.m4`；
- `src/` 下 11 个 `.cpp` 无任何 `int main(`；
- 顶层 `Makefile.am` 的 `SUBDIRS` 只有 `src`，无 `TESTS`/`check-local`/`check_PROGRAMS`；
- `CMakeLists.txt` 无 `enable_testing()`/`add_test()`/`include(CTest)`；
- README 提到的 `test.cpp` 未随仓库提供（该文件现在只存在于 main 分支新增的 `example/` 中）。

因此 `N(上游) = 0`；唯一可执行证据是 `test_package` 的消费者断言（分栏统计，不并入上游分母）。

## 验证结果

原生探索（设备 clang，`CMAKE_SYSTEM_NAME=OHOS`）：

```
SONAME: libsbsms.so.2
libsbsms.so -> libsbsms.so.2 -> libsbsms.so.2.3.0
install: lib/{libsbsms.so.2.3.0,libsbsms.so.2,libsbsms.so}, include/sbsms.h,
         lib/pkgconfig/sbsms.pc, lib/cmake/sbsms/{sbsmsConfig,sbsmsTargets}*.cmake
```

消费者测试（`test_package/test_sbsms.cpp`，440 Hz 单音驱动公开 API）：

```
[1] shipped quality table / API values     bands=8 H=3 N[0]=512 N2[0]=512 res[0]=1
                                           getFrameSize()=384 getMaxPresamples()=19584
[2] identity      want=44100 produced=44160 peak=0.50414 energy=5468.46  estHz=439.402
[3] pitch x2      want=44100 produced=44160 peak=0.50004 energy=5458.03  estHz=879.803
[4] rate  x2      want=22050 produced=22272 peak=0.50004 energy=2728.65  estHz=439.574
checks=26 failed=0
RESULT: PASS
```

采信轮（清缓存 + `conan-verify` + W3）结果见：

- `reports/conan-verify-report.md` — G0–G5 门禁结论；
- `reports/conan-verify-supplement.md` — **人工补测**：采信轮报告里 G4/L2/L4/L5 因工具
  路径解析缺陷被静默跳过（`⚠️ 无法找到程序包 ID` / `⏭️ 跳过（无 cache 路径）` 却并列
  `✅ PASS`），该报告补齐产物清单↔`package_info()`、消费者加载与运行、库与消费者
  二进制的 `readelf` 安全属性、两条稳定产物聚合，以及跨轮可复现性；
- `reports/conan-create-log.md` — 干净轮 `conan create` 日志**逐字留档**（含字节数、
  行数、sha256、可复制抽取命令与两级自检结论；原 `*.log` 不入库）；
- `reports/w3-local-ci-log.md` — W3 本地 CI 日志**逐字留档**（同上口径）。

W3 摘要：`L0_RESULT=pass` / `L1_RESULT=pass`（含 L1e 破坏性反向测试）/ `L2_RESULT=skip: no bin/`
（纯库，预期）/ `L4_RESULT=pass: patches clean`（零补丁）/ `L5_RESULT=pass: lib/ has content`，
`Success 1, Failed 0, Pass rate 100.0% (1/1)`。

同一 SHA（`c9c5fb32714eb222b399d53483a386a1654a9e72`）两轮独立清缓存构建
（采信轮 `conan-verify` 与 `finish` 内嵌 W3）的 **8 个交付产物与整树逐字节一致**，
两条聚合值亦相同（包内容 `3254bf8f…`、头文件树 `ede0a0a9…`）→ 基线可复现。
取值口径：两轮的包目录分别从各自日志取（`…/p/b/libsb698b9c997c655/p` 与
`…/p/b/libsbf2cff71db885c/p`），**不能**用 `conan cache path "<ref>:<pid>"` 取"第二轮"
——它返回的是 recipe 登记的那一个，会变成同一目录自比（首版即因此把同一目录读了两遍，
得出过错误的"8/8 逐字节一致"结论；独立审计用两个真实包目录实测为 7/8，随后按问题 5
根治了根因）。逐轮数值与复算命令见 `reports/conan-verify-supplement.md` §5.3。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libsbsms.so.2.3.0` + `libsbsms.so.2` + `libsbsms.so` | 共享库与版本化 SONAME 符号链接 |
| `include/sbsms.h` | 公开头文件（`namespace _sbsms_`） |
| `lib/pkgconfig/sbsms.pc` | pkg-config 元数据（CMake 路径写入 2.3.0；`prefix` 已改写为可重定位的 `${pcfiledir}/../..`） |
| `lib/cmake/sbsms/sbsmsConfig.cmake` 等 | 上游导出的 CMake 包（`sbsms::sbsms`） |
| `licenses/LICENSE.txt` | GPL-2.0-or-later |

## 注意事项

- 库**不提供命令行工具**，因此软件级目录**没有** `commands.json`（R38 仅 tool 类型需要）。
- 默认 `shared=True`：上游 `option(BUILD_SHARED_LIBS ... ON)` 即动态库，且设备
  `/lib`、`/lib64`、`/system/lib` 无 `libsbsms*`，不撞 R26 的系统同名库约束。
- `SBSMS::read()` 会无限补零、永不返回 0；消费者必须自己按
  `iface->getSamplesToOutput()` 设停止条件（README 亦如此说明）。test_package 按此实现。
- `generate()` 里的 `CMAKE_SYSTEM_PROCESSOR` **由 `self.settings.arch` 派生**
  （`armv8 → aarch64`），不硬编码；换 arch 不会静默错配。`validate()` 只接受
  `Linux`/`OHOS`（集合判断，R32），因此没有为其它系统保留分支。
- `package()` 对**生成物** `sbsms.pc` 做了一次 `prefix` 改写（问题 5）。这是让同一配方
  两轮构建逐字节可复现的必要条件；若后续把该文件改回绝对 `prefix`，"跨轮可复现"
  这一结论会立即失效（**独立审计对首版产物的实测为 7/8**，即为此形态）。

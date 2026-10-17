# openbabel 3.2.1 适配笔记

## 编译环境
- 构建系统: cmake（CMake 4.1.2 / ctest 3.26.4，OHOS SDK 自带）
- 编译日期: 2026-10-03
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64, -stdlib=libc++)
- 状态: built

## 编译步骤

```bash
# Conan 配方驱动（ohos-aarch64 profile）
conan create archives/o/openbabel/3.2.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

CMake 关键选项（conanfile.py `generate()` 注入，全部 cache 变量）：
- `BUILD_SHARED=ON`（共享构建：仅共享模式构建 5 个插件组 + 全部格式插件 MODULE，运行时 dlopen 加载；上游 348 项 ctest 以此为前提）
- `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,` / `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,`（OHOS 工具链默认不设 SONAME 旗标，见问题 #3）
- `CMAKE_LIBRARY_OUTPUT_DIRECTORY=<build>/lib`（OHOS 下 if(UNIX) 为假，上游默认把构建树库放 <build>/bin；上游测试 ENVIRONMENT 烘焙了 <build>/lib，见问题 #4）
- `LIB_INSTALL_DIR=<package>/lib`（**必须绝对路径**，本环境 CMake 4.1.2 相对值陷阱，见问题 #5）
- `LIBXML2_INCLUDE_DIR` / `LIBXML2_LIBRARY`（libxml2 包注入，cmake_find_mode=none 回退 module 模式，见依赖表）
- `RAPIDJSON_FOUND=TRUE` / `RAPIDJSON_INCLUDE_DIRS` / `RAPIDJSON_VERSION=1.1.0`（rapidjson 包注入，避免上游从 github 外拉，见依赖表）
- `ZLIB_INCLUDE_DIR` / `ZLIB_LIBRARY{,_RELEASE,_DEBUG}`（OHOS SDK sysroot 共享 libz.so 注入，见依赖表）
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 cmake_minimum_required 2.8.12 + 新 CMake 的 policy 下限）
- WITH_INCHI / WITH_JSON / BUILD_GUI / ENABLE_TESTS 等保持上游默认（WITH_INCHI=ON 用内置源码、ENABLE_TESTS=ON 实跑 ctest）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 共享构建下所有格式转换失败：`SetInFormat()` 恒 false、`FindType()` 返回 null（上游 ctest 大量假失败） | 插件注册表按 DSO 分裂：plugin.h 默认分支把 `Map()` 定义为**头内 inline 的 function-local static**，每个 DSO（libopenbabel.so、各插件 .so、可执行文件）各持一份私有注册表——插件注册进 A 表的 Map，调用方查 B 表的 Map，`Map().count(ID)` 恒 0。上游为 Cygwin/MinGW 早已备好同一问题的正解（`Map()` 外置声明 + `PLUGIN_CPP_FILE` 在库内 .cpp 单点定义），只是用 `#if defined(__CYGWIN__)||defined(__MINGW32__)` 圈死 | 自研补丁组 1（10 补丁中的 8 个）：plugin.h 删除平台条件、**无条件**采用外置定义路径；7 个 .cpp（chargemodel/descriptor/fingerprint/forcefield/format/op/ops-loader）解除 `PLUGIN_CPP_FILE` 调用的同守卫。补丁为可移植形式，无平台宏 |
| 2 | 修 #1 后 test_runner 仍 SIGSEGV：`dynamic_cast<OBPairFloatingPoint*>` 等跨 DSO 判定失败返回 null 后解引用 | `OBPairTemplate<int/double/bool>` 的模板成员在多个 DSO 各自实例化出 **WEAK 的 typeinfo/vtable**；aarch64 的 Itanium ABI 采用**唯一 typeinfo 语义**（`type_info::operator==` 只比指针），跨 DSO 的 typeinfo 指针不同 → dynamic_cast 恒失败 | 自研补丁组 2（2 个）：generic.h 对三个特化加 `extern template` 声明、generic.cpp 在库内**单点显式实例化**，三个特化在 libopenbabel 中各有一个强符号 typeinfo |
| 3 | 插件 dlopen 失败：插件 DT_NEEDED 记录的是相对路径 `../../bin/libopenbabel.so.8`，按进程 CWD 相对解析 | OHOS 工具链默认不给共享库设 SONAME 旗标；无 SONAME 时链接器把**依赖库的相对路径**写进 DT_NEEDED | 注入 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,`（CMake 追加库名），全部 .so 获得规范 SONAME，DT_NEEDED 变为 `libopenbabel.so.8` 经 LD_LIBRARY_PATH 解析 |
| 4 | build() 内 ctest 找不到库/找不到插件 | 上游 test/CMakeLists.txt 的 `ENVIRONMENT` 在 **configure 期**烘焙 `$ENV{LD_LIBRARY_PATH}` 进 CTestTestfile.cmake（`$ENV{...}` configure 期求值后定死），事后补环境无效；且插件加载 DLHandler 优先读 `BABEL_LIBDIR` 环境变量，回退的编译期 `OB_MODULE_PATH`（= <prefix>/lib/openbabel/3.2.1）构建期尚未生成 | configure **之前**把依赖 libdirs + 构建树 lib/bin 预置进 `os.environ["LD_LIBRARY_PATH"]`；ctest **之前**置 `BABEL_LIBDIR=<build>/lib`（经 ctest 父进程环境继承给各测试） |
| 5 | 包内缺主库：`install(TARGETS openbabel)` 零安装行，libopenbabel.so 未进包（test_package 报 Library 'openbabel' not found in package） | **本环境 CMake 4.1.2 行为**（最小复现实验证实）：`-D` 传入的 `LIB_INSTALL_DIR` 相对值（UNINITIALIZED 缓存条目），在上游 `set(CACHE PATH)` 类型升级时被解析到 `CMAKE_BINARY_DIR`（实测 `-DLIB_INSTALL_DIR=lib` → `<build>/lib`）；主库"安装"目的地因此落在构建树，源=目的，`cmake --install` 静默跳过。绝对值 -D 可直通（已实测） | `tc.cache_variables["LIB_INSTALL_DIR"] = os.path.join(self.package_folder, "lib")`（包目录绝对路径）。附带修复 .pc 文件装错位置（其 DESTINATION 派生自 LIB_INSTALL_DIR） |
| 6 | build() 内 `subprocess.run(["ctest", ...])` 报 `FileNotFoundError: 'ctest'` | conan 进程的 PATH 不含 profile 的 buildenv PATH（仅注入 self.run 的 shell 环境） | 显式解析：`shutil.which("ctest")` + `/data/service/hnp/bin/ctest` 回退，缺失即 `ConanException` 硬失败（本配方以上游测试实跑为交付前提，R51，不静默跳过） |
| 7 | test_package 的 `self.run(exe, env=[...])`：传 dict 断言失败；传 "VAR=VALUE" list 无效果（库仍找不到） | `ConanFile.run()` 的 env 参数是 **env 脚本文件名列表**（在 generators 目录找 `<name>.sh` source 后执行），不是 VAR=VALUE 列表；"VAR=VALUE" 被当文件名找不到后原样执行、无任何环境修改 | test() 改用 shell 前缀直接注入：`self.run('LD_LIBRARY_PATH="<依赖图全部 libdir>" "<exe>"')` |

## 源码修改

| 补丁组 | 文件 | 修改 |
|--------|------|------|
| 组 1（8 个）：插件注册表单实例化 | include/openbabel/plugin.h | 删除 `__CYGWIN__/__MINGW32__` 条件编译，无条件采用外置定义路径（`Map()` 库内单点定义 + `PLUGIN_CPP_FILE`） |
| | src/chargemodel.cpp / descriptor.cpp / fingerprint.cpp / forcefield.cpp / format.cpp / op.cpp / ops/loader.cpp | 解除 `PLUGIN_CPP_FILE(OBXxx)` 调用的平台守卫（7 文件） |
| 组 2（2 个）：OBPairTemplate 跨 DSO typeinfo 唯一性 | include/openbabel/generic.h | `OBPairTemplate<int/double/bool>` 三个特化加 `extern template` 声明 |
| | src/generic.cpp | 库内单点显式实例化三个特化（与头文件声明对应） |

全部 10 个补丁由 `refresh-patch --auto` 从干净基线（.orig）与修改后（.work）的 diff 生成；无平台宏（可移植形式）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| eigen | 3.4.1 | 必需（力场 L-BFGS）。`find_package(Eigen3 CONFIG)`；conan eigen 包声明 cmake_file_name=Eigen3 / cmake_target_name=Eigen3::Eigen，CMakeDeps 生成的 Eigen3Config.cmake 在 CONFIG 模式即命中，无需注入 |
| libxml2 | 2.15.3.1 | 必需（CML 格式）。上游用 module 模式 `find_package(LibXml2)` 判 `LIBXML2_FOUND`；CMake 3.24+ PREFER_CONFIG 会被 conan 生成的 LibXml2Config.cmake 抢占（只置 LibXml2_FOUND）→ 置 `cmake_find_mode=none` 回退 module 模式并注入 `LIBXML2_INCLUDE_DIR`/`LIBXML2_LIBRARY` |
| rapidjson | 1.1.0 | 必需（JSON 格式）。上游判大写 `RAPIDJSON_FOUND`，`RAPIDJSON_VERSION` 缺失或 <1.1.0 时从 github 拉取（网络不稳）→ `cmake_find_mode=none` + 注入 `RAPIDJSON_FOUND/INCLUDE_DIRS/VERSION=1.1.0` 确定性短路 |
| zlib | sysroot 共享 libz.so（ohos-sdk_26.0.0.18） | 必需（gzip 读写 + png 输出链）。**不用 conan zlib/1.3.1**：该包为静态非 PIC，链入共享库触发 aarch64 重定位错误（与仓内其他配方对平台库的同款取舍一致）；经 `ZLIB_INCLUDE_DIR`/`ZLIB_LIBRARY` 注入 OHOS SDK sysroot 的共享 libz.so |
| inchi | 内置源码（src/formats/libinchi） | 必需（InChI 生成/解析）。`WITH_INCHI=ON`（默认）+ `OPENBABEL_USE_SYSTEM_INCHI=OFF`（默认）→ 用随源码分发的 inchi 源码构建 libinchi.so，上游自带安装规则，无需系统包 |
| boost | 不引入 | 上游非 REQUIRED（仅个别 program_options/iostreams 工具用到） |

## 验证结果

```bash
# 1) 上游 ctest（build() 内实跑，配方自动执行）
ctest --output-on-failure --timeout 120 -j 4 --test-dir <build>
# 结果：100% tests passed, 0 tests failed out of 348（总耗时 85.13s）

# 2) Conan L1 测试（test_package）：SMILES→InChI 转换硬断言
# - SetInAndOutFormats("smi","inchi")（插件 dlopen 加载 + 注册表查找）
# - ReadString(&mol, "CCO")（SMILES 解析）
# - WriteString(&mol) 产出非空（InChI 生成，经 libinchi）
# - 断言输出含 "InChI=1S/C2H6O"
# 结果：4/4 断言通过，输出 InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3

# 3) conan create 全流水线：编译（1066 targets）→ ctest → install →
#    package() 全 ELF selfSign 签名 → test_package，全绿
```

包布局：`lib/libopenbabel.so{,.8,.8.0.0}` + `lib/libinchi.so{,.1,.1.07.5}` + `lib/openbabel/3.2.1/`（92 个插件 .so）+ `bin/`（20 个命令行工具）+ `include/openbabel3/openbabel/` + `share/openbabel/3.2.1/`（力场参数等数据）。

## R51 上游测试三步法声明

**Step 1 清点**（实测）：
- 上游测试位于 `test/`（单数）目录；ctest 用例由 `test/CMakeLists.txt` 的**双重 foreach 动态注册**（`foreach(cpptest ${cpptests})` × `foreach(part ${${cpptest}_parts})` + origtests/inchi 测试块）
- **`ctest -N` 实测总用例数 = 348**（cpptests×parts + origtests×parts + inchi 测试 + fuzz 回归）
- 测试数据：源码树 `data/`（BABEL_DATADIR，测试 ENVIRONMENT 已烘焙）+ `test/` 子目录（各测试程序的 fixture 与 fuzz 用例）

**Step 2 运行**：已实跑。build() 内 `ctest --output-on-failure --timeout 120 -j 4` 全量执行 348 项（本机 OHOS aarch64 原生环境，与 CI 同构：clang 15 / ohos-sdk_26.0.0.18）。前置条件：问题 #3 的 SONAME 修复 + 问题 #4 的 configure 期环境预置。

**Step 3 回填**：上游 ctest 实测 **348/348 通过，通过率 100%**（2026-10-03，conan create 内自动执行，日志留档）。L1 test_package 另以 SMILES→InChI 断言验证消费者链路（插件 dlopen + 注册表 + libinchi 生成）。

## 注意事项

1. **共享构建是完整形态**：仅 `BUILD_SHARED=ON` 构建格式插件（MODULE + dlopen）；上游 348 项 ctest 与完整格式转换能力以此为前提。
2. **zlib 走 sysroot 共享库**：ohpcd 制品仓 zlib/1.3.1 为静态非 PIC，不可链入共享库；sysroot 共享 libz.so 是平台原生设施（`/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot`，配方自动探测最新 SDK）。
3. **BABEL_LIBDIR 运行时变量**：共享构建的消费者建议设 `BABEL_LIBDIR=<pkg>/lib/openbabel/3.2.1`（配方 `runenv_info` 已自动导出）；未设时回退编译期 `OB_MODULE_PATH`（已指向包内，实测可用）。
4. **CMake 4.1.2 陷阱（实测，供后续配方参考）**：`-D` 传入的 `LIB_INSTALL_DIR`/`BIN_INSTALL_DIR` 类相对值会在上游 `set(CACHE PATH)` 类型升级时被解析到 `CMAKE_BINARY_DIR`（最小复现：`-DLIB_INSTALL_DIR=lib` → `<build>/lib`；`-DBIN_INSTALL_DIR=bin` → `<build>/bin`）；此类安装目录变量一律传**绝对路径**。
5. **头文件版本化 include 目录**：openbabel 3 头文件安装在 `<prefix>/include/openbabel3/openbabel/`（版本化目录），配方 `package_info()` 已设 `includedirs=["include/openbabel3"]`，消费者 `#include <openbabel/base.h>` 经此路径解析。
6. **签名**：`package()` 对全部 ELF（bin/ 工具、lib/ 主库+inchi、插件）执行 `binary-sign-tool sign -selfSign 1` 就地签名（OHOS 拒绝执行/dlopen 未签名 ELF）；soname 符号链接链跳过（指向已签名文件）。
7. **OpenBabel 3 API 变更**：测试/下游代码须用 v3 API（`SetAtomicNum`/`GetAtomicNum`），v2 旧名已移除。
---

**编译结束**: 2026-10-03 20:14
**最终状态**: built

# ismrmrd 1.15.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-04
- 编译器: clang 15.0.4 / clang++（target aarch64-unknown-linux-ohos）
- 目标平台: OpenHarmony / HarmonyOS PC (aarch64)，profile `ci/conan/profiles/ohos-aarch64`
- conan: 2.29.1（OHOS 适配版）
- 状态: built

## 编译步骤

```bash
# 1. 源码（官方 tag tarball，SHA-256 已核验）
#    https://github.com/ismrmrd/ismrmrd/archive/refs/tags/v1.15.0.tar.gz
#    sha256: 57739de6d93203adc86f5e510729b7e2a45917bcab480dd1c1a6b6d16508a42c

# 2. conan create（构建 + 全部上游测试 + 消费者用例）
cd archives/i/ismrmrd/1.15.0
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

构建配置：`BUILD_STATIC=OFF`（动态库）、`USE_HDF5_DATASET_SUPPORT=ON`、
`BUILD_TESTS=ON`、`BUILD_UTILITIES=ON`、`BUILD_EXAMPLES=OFF`。

1.15.0 与 1.7.0 的关键差别：**上游把 `test_dataset.cpp` / `test_end_to_end.cpp`
放在 `USE_HDF5_DATASET_SUPPORT` 开关内，且 EndToEnd 用例会调用
`utilities/ismrmrd_*` 可执行文件**。因此 1.7.0 那套
`-DUSE_HDF5_DATASET_SUPPORT=OFF -DBUILD_UTILITIES=OFF` 的省事配置在 1.15.0 上会
静默裁掉 2 个上游用例，本配方改为两者全开。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 配错 include 变量，`boost/test/unit_test.hpp` 与 `boost/filesystem.hpp` 全部找不到 | 上游 `tests/CMakeLists.txt` 的 `include_directories` 用的是 FindBoost 模块变量 `${Boost_INCLUDE_DIR}`；而 Boost.Test 改走纯头文件后不再调用 `find_package(Boost)`，该变量为空 | 补丁 0001 把该行换成配方传入的 `${BOOST_INCLUDE_DIR}`，并保留 `find_package` 兜底 |
| 2 | `find_package(Boost CONFIG COMPONENTS filesystem random program_options unit_test_framework)` 整体失败，`Boost_LIBRARIES` 为空，`test_dataset.cpp` 链接缺 `Boost.Filesystem` | 鸿蒙 boost 包不导出 `random` 组件（Boost.Random 自 1.69 起纯头文件）；CONFIG 模式少一个组件即整体 `Boost_FOUND=FALSE` | 补丁 0003 把组件表收窄为 `filesystem program_options`（真正提供的两个）；测试框架则由补丁 0001/0002 走纯头文件 |
| 3 | `utilities/` 链接失败 | 上游用 FindBoost 模块变量 `${Boost_PROGRAM_OPTIONS_LIBRARY}`，CONFIG 模式不产出该变量 | 补丁 0004 改用 BoostConfig 导出的导入目标 `Boost::program_options`；同时把 `${Boost_INCLUDE_DIR}` 换成 `${BOOST_INCLUDE_DIR}` |
| 4 | `find_package(FFTW COMPONENTS FLOAT_LIB)` 报 `FFTW_FLOAT_LIB-NOTFOUND`，utilities 未构建，EndToEnd 两个用例报 `Could not find utilities directory` | 鸿蒙 `fftw` 包 `ENABLE_FLOAT=OFF`，只装双精度 `libfftw3`；而上游 utilities 只用 `fftwf_*`（单精度） | 依赖改为独立的 `fftw3f/3.3.10`（提供 `libfftw3f`） |
| 5 | clang 15 报 `-Wimplicit-const-int-float-conversion` 并被 `-Werror` 变成硬失败 | 上游 CMakeLists 自己追加 `-Wall -Werror`；`tests/test_serialization.cpp` 里 `(float)(std::rand()) / RAND_MAX` 属于有意的边界转换 | 只降级该诊断：`-Wno-error=implicit-const-int-float-conversion`，其余告警仍是硬失败 |
| 6 | 直接运行 `test_ismrmrd` 报 `Error relocating ... symbol not found`，但 `ctest` 通过 | 该二进制把 `DT_NEEDED` 记成**相对路径** `../libismrmrd.so`，只有在自身目录为工作目录时才能启动 | 配方直跑时显式指定 `cwd` 为其所在目录（ctest 天然如此） |
| 7 | 依赖图 `Conflict between zlib/1.3.1 and zlib/1.3.1.1` | `boost/1.84.0`、`1.85.0` 配方钉 `zlib/1.3.1`，与 `hdf5/1.14.6` 拉入的 `zlib/1.3.1.1` 冲突 | 选 `boost/1.90.0.4.1`（同图可解） |
| 8 | `HDF5::HDF5` / `${HDF5_INCLUDE_DIRS}` 目标名对不上 | Conan 的 hdf5 配置包只导出 `hdf5::hdf5` | 不启用 `CMAKE_FIND_PACKAGE_PREFER_CONFIG`，用 CMake 自带 FindHDF5 模块（配方传 `HDF5_ROOT` 指向包目录），上游期望的 `HDF5::HDF5` 与 `HDF5_C_LIBRARIES` 均成立 |
| 9 | L5 闸门：`libismrmrd.so` 缺少 `DT_SONAME`，下游只能按完整路径链接 | conan 在 `os=OHOS` 时把 `CMAKE_SYSTEM_NAME` 映射成 `HarmonyOS`，而 SDK 里只有 `Modules/Platform/OHOS.cmake`；名字对不上时 CMake 不报错，只把平台变量留空，其中 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空 → 链接命令没有 `-Wl,-soname,` | `generate()` 中按 `os == "OHOS"` 守卫显式设置 `cmake_system_name=OHOS`、`cmake_system_processor=aarch64`（该守卫是必须的，否则非 OHOS profile 会被写死） |
| 10 | 补上 SONAME 后，test_package 消费者报 `Error loading shared library libismrmrd.so.1.15` | 两处叠加：(1) test_package 显式写 `generators=` 会**替换** conan 默认集，漏掉 `VirtualRunEnv` 就没有 `conanrun` 环境；(2) `cmake --install` 会做安装期 RPATH 改写 | test_package 显式声明 `VirtualRunEnv`/`VirtualBuildEnv` 并用 `env="conanrun"` 跑 ctest 与二进制；配方设 `CMAKE_SKIP_RPATH=ON`（不烘焙 RPATH，交给 run 环境），同时把 build 根目录加入 `build()` 阶段的 `LD_LIBRARY_PATH` |

## 源码修改（补丁）

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001 | `tests/CMakeLists.txt` | 测试闸门由 `Boost_UNIT_TEST_FRAMEWORK_FOUND` 改为 `BOOST_INCLUDE_DIR`；修正 `include_directories` 里未被赋值的 `${Boost_INCLUDE_DIR}` |
| 0002 | `tests/test_main.cpp` | 定义 `BOOST_TEST_MODULE` 的 TU 改用 `<boost/test/included/unit_test.hpp>`（Boost.Test 纯头文件实现） |
| 0003 | `CMakeLists.txt` | Boost 组件表收窄为 `filesystem program_options`；`pugixml::static` / `pugixml::shared` 统一为 Conan 唯一导出的 `pugixml::pugixml` |
| 0004 | `utilities/CMakeLists.txt` | `${Boost_PROGRAM_OPTIONS_LIBRARY}` → 导入目标 `Boost::program_options`；`${Boost_INCLUDE_DIR}` → `${BOOST_INCLUDE_DIR}` |

补丁均为平台/构建系统适配，**不改变任何被测逻辑**：没有删除、跳过或放宽任何断言。

## 依赖版本

| 包 | 版本 | 说明 |
|----|------|------|
| boost | 1.90.0.4.1 | 提供 headers / filesystem / program_options / unit_test_framework |
| pugixml | 1.16 | 核心库 `libsrc/xml.cpp`、`libsrc/meta.cpp` 的硬依赖（上游 `REQUIRED`） |
| hdf5 | 1.14.6 | `USE_HDF5_DATASET_SUPPORT=ON`，DatasetTest / EndToEndTest 需要 |
| fftw3f | 3.3.10 | 单精度 FFTW，utilities 的 `fftwf_*` 需要（`fftw` 包只有双精度） |

## 上游测试台账

上游是**单一 `test_ismrmrd` 二进制**（Boost.Test，ctest 注册名 `check`），
源码里有 10 个 suite；`BOOST_AUTO_TEST_CASE_TEMPLATE` 按类型展开后，
实际实例化并执行 **54 个 case**。

| suite | 源文件 | 声明 case | 说明 |
|-------|--------|-----------|------|
| AcquisitionsTest | test_acquisitions.cpp | 5 | Acquisition 生命周期与 header 字段 |
| ImagesTest | test_images.cpp | 5 | Image 生命周期与 header 字段 |
| NDArrayTest | test_ndarray.cpp | 3 | NDArray 初始化/创建/拷贝 |
| FlagTest | test_flags.cpp | 5 | flag 位操作 |
| ChannelTest | test_channels.cpp | 4 | channel mask |
| QuaternionTest | test_quaternions.cpp | 3 | 四元数/方向向量互转 |
| SerialiationTest | test_serialization.cpp | 7（含模板展开） | 序列化/反序列化 |
| HeaderTest | test_xml_header.cpp | 3 | XML header 往返 |
| DatasetTest | test_dataset.cpp | 1 | HDF5 dataset 读写（**需 HDF5 开启**） |
| EndToEndTest | test_end_to_end.cpp | 2 | 流式重建端到端（**需 utilities + HDF5**） |

## 验证结果

```bash
# conan create（构建 + 上游测试 + 消费者用例），exit 0
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 上游测试（ctest 注册名 check）
100% tests passed, 0 tests failed out of 1
Running 54 test cases...
Test module "ISMRMRD Unit Tests" has passed with:
  54 test cases out of 54 passed
  270765 assertions out of 270765 passed

# 消费者用例（test_package）
100% tests passed, 0 tests failed out of 2
  test_consumer ... Passed
  test_ohos     ... Passed
ismrmrd consumer test PASSED (flags/channels/acquisition/ndarray OK)
ismrmrd OHOS C++ XML round-trip PASSED (1383 bytes XML)
```

**通过率：上游 54/54 = 100%（270765/270765 断言）；消费者 2/2 = 100%。**
无跳过、无禁用、无用例减少。

本地 CI 模拟（`CI_PACKAGES=archives/i/ismrmrd/1.15.0 zsh ci/conan/build_and_test.sh`，exit 0）：

```
G0_RESULT=pass        # 知识图谱完整性
KC_RESULT=pass
JC_RESULT=pass        # 无杂项文件（按 PR diff 范围）
L0_RESULT=pass        # test_package 结构 / MANIFEST / 依赖发布(R36) 等
L1_RESULT=pass        # 上游测试 + test_package 均在 conan create 中真实执行
L1e                   # 破坏性负向测试：移走 bin//lib//include/ 后测试失败 —— 用例确实依赖本库
L2_RESULT=skip        # utilities 上游本就不支持 --version/--help（非阻塞）
L4_RESULT=pass        # 补丁静态扫描
L5_RESULT=pass        # 含 DT_SONAME 质量闸门
Pass rate: 100.0% (1/1)
```

## 交付物

| 产物 | 说明 |
|------|------|
| `lib/libismrmrd.so.1.15.0` | 动态库本体，带 `DT_SONAME = libismrmrd.so.1.15` |
| `lib/libismrmrd.so.1.15` → `.1.15.0`、`lib/libismrmrd.so` → `.1.15` | 版本软链 |
| `include/ismrmrd/*.h`、`include/ismrmrd/version.h` | 公开头（C 与 C++ API） |
| `lib/cmake/ISMRMRD/*.cmake` | `find_package(ismrmrd)` 导出目标 `ismrmrd::ismrmrd` |
| `bin/ismrmrd_info` 等 8 个 | utilities（`BUILD_UTILITIES=ON`，上游 EndToEnd 用例需要） |
| `share/ismrmrd/schema/ismrmrd.xsd` | XML schema |

## 注意事项

- 本配方**不能**照搬 1.7.0 的 `USE_HDF5_DATASET_SUPPORT=OFF` / `BUILD_UTILITIES=OFF`：
  1.15.0 把 2 个用例放进了 HDF5 开关内，且 EndToEnd 用例依赖 utilities 可执行文件，
  关掉会静默减少上游覆盖。
- `fftw3f` 是独立包，不是 `fftw` 的一个选项；本仓 `fftw` 各版本配方均
  `ENABLE_FLOAT=OFF`。
- test_package 的消费者用例只使用**已安装的公开头 + 公开 API**，验证的是
  「别人把这个库拿去能不能编译、链接、调用跑通」。

## 结束

最终状态：适配完成（built）。上游 54/54 用例、270765/270765 断言通过，
test_package 消费者用例 2/2 通过，`conan create` 退出码 0；
未删除或跳过任何上游用例。

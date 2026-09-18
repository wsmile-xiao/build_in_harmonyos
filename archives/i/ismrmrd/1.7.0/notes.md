# ismrmrd 1.7.0 适配笔记

## 编译环境
- 构建系统: cmake (CMake 4.1.2, 上游 cmake_minimum_required 2.8.12)
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, /data/service/hnp/bin)
- 目标平台: HarmonyOS PC (aarch64-linux-ohos), profile: ci/conan/profiles/ohos-aarch64
- 状态: built (conan-verify 八门禁通过)

## 编译步骤

```bash
# 1. 源码（官方 tag tarball，SHA-256 已核验）
#    https://github.com/ismrmrd/ismrmrd/archive/refs/tags/v1.7.0.tar.gz
#    sha256: 25954c8495406359e40b80f7a8bc14e0d4d93c0da9d53e6763e0764c8a6dc10c

# 2. 手动编译（Step 2 探索性编译，HDF5 关闭、测试开启）
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DUSE_HDF5_DATASET_SUPPORT=OFF -DBUILD_TESTS=ON \
  -DBUILD_UTILITIES=OFF -DBUILD_EXAMPLES=OFF \
  -DBOOST_INCLUDE_DIR=<boost 头文件目录> -DCMAKE_INSTALL_PREFIX=...
cmake --build build -j2
make check            # 25/25 用例通过

# 3. conan-verify（G0-G4 + L2/L4/L5 全部通过）
python3 scripts/ohc-run.py conan-verify ismrmrd 1.7.0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时/HTML | 网络受限 | 经 gh-proxy.com 官方镜像下载；conandata.yml 保留官方 HTTPS URL（R39），sha256 已核验 |
| 2 | CMake 4.1 拒绝 cmake_minimum_required(2.8.12) | CMake>=4 移除 <3.5 兼容 | 配方 build() 用 `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM":"3.5"})` 命令行传参（实测 toolchain 缓存变量对该检查无效） |
| 3 | Boost `pthread_setcancelstate` 未声明 | OHOS libc 不暴露该符号（同 Android） | 定义 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`（Boost 官方逃生宏），配方 generate() 注入 CMAKE_C_FLAGS/CXX_FLAGS |
| 4 | 上游测试链接失败（boost_unit_test_framework 缺失） | ohpcd 制品仓 boost/1.84.0 只发布头文件与 4 个静态库，无 unit_test_framework 组件 | Boost.Test >= 1.64 支持纯头文件模式：补丁 tests/CMakeLists.txt（不再 require unit_test_framework 库）+ test_main.cpp 改用 `boost/test/included/unit_test.hpp`（源码测试入口恢复规则） |
| 5 | zlib/1.3.1 本地缓存条目损坏（缺 conanfile.py） | 缓存污染 | `conan remove "zlib/*" -c` 后重新 download，重装成功 |
| 6 | test_package 消费者测试段错误 | create_acquisition 后未调用 ismrmrd_init_acquisition 就写 traj（NULL） | 补 ismrmrd_init_acquisition 调用，去掉对未分配缓冲区的写入 |

## 源码修改（补丁）

- `0001-tests-CMakeLists.txt.patch`（+12/-9）：Boost.Test 纯头文件模式，不再要求链接 unit_test_framework；支持 BOOST_INCLUDE_DIR 注入
- `0002-tests-test_main.cpp.patch`（+1/-1）：BOOST_TEST_MODULE 所在 TU 改用 `boost/test/included/unit_test.hpp`

## 依赖版本

- boost/1.84.0（制品仓已发布，头文件 + filesystem/iostreams/program_options/regex 静态库；测试用纯头文件 Boost.Test）
- zlib/1.3.1（boost 传递依赖，制品仓已发布）
- HDF5（可选，USE_HDF5_DATASET_SUPPORT=OFF 关闭：hdf5/1.14.6 已发布但上游单测不覆盖 HDF5 路径，本适配关闭以聚焦核心库；dataset 文件 I/O 不可用已明确记录）

## 上游测试台账（双口径统计）

### 口径 A：源码声明总数（source_declared_total）

官方 tag 源码 `tests/` 目录按 BOOST_AUTO_TEST_CASE 可复制枚举：

| 测试源文件 | 声明用例数 | 独立上游用例 |
|---|---|---|
| tests/test_acquisitions.cpp | 5 | ✅ 是（用户测试源，Suite: AcquisitionsTest） |
| tests/test_images.cpp | 5 | ✅ 是（用户测试源，Suite: ImagesTest） |
| tests/test_ndarray.cpp | 3 | ✅ 是（用户测试源，Suite: NDArrayTest） |
| tests/test_flags.cpp | 5 | ✅ 是（用户测试源，Suite: FlagTest） |
| tests/test_channels.cpp | 4 | ✅ 是（用户测试源，Suite: ChannelTest） |
| tests/test_quaternions.cpp | 3 | ✅ 是（用户测试源，Suite: QuaternionTest） |
| tests/test_main.cpp | 0 | ❌ 否（BOOST_TEST_MODULE 定义 + GlobalConfig fixture，非用例） |
| tests/test_ismrmrd.h | 0 | ❌ 否（fixture 头文件） |
| **源码声明总数** | **25** | |

### 口径 B：当前 OHOS 配置实例化/执行（configured_executable_total / executed_passed_total）

- configured_executable_total: 25（BUILD_TESTS=ON，单二进制 test_ismrmrd 内 6 个 Suite 全部注册）
- executed_passed_total: 25/25（**25/25 = 100.0%**），断言 7151/7151 通过
- 失败数: 0；未运行/未实例化数: 0

逐项映射（源码声明 -> 构建目标 -> 实际执行日志）：
- tests/*.cpp 25 个 BOOST_AUTO_TEST_CASE -> CMake target `test_ismrmrd`（tests/CMakeLists.txt add_executable 7 个源文件）-> `make check` / `./test_ismrmrd --report_level=detailed` 输出 "Running 25 test cases... 25 test cases out of 25 passed"，完整日志 SHA-256 见最终回报

### 其他测试相关条目（不计入独立用例，逐项标注）

| 条目 | 类别 | 是否独立用例 | 是否运行 | 说明 |
|---|---|---|---|---|
| tests/matlab/Hdf5Test.m | 测试脚本 | ❌ 否 | ❌ | MATLAB 脚本，非 C/C++ 用例；依赖 HDF5（本适配关闭）与 MATLAB 运行时（OHOS 不可用） |
| matlab/test/xmlTest.m | 测试脚本 | ❌ 否 | ❌ | MATLAB 脚本，非独立用例 |
| examples/c/main.c | 样例 | ❌ 否 | ❌ | 样例程序（BUILD_EXAMPLES=OFF） |
| examples/matlab/test_*.m (3 个) | 样例脚本 | ❌ 否 | ❌ | MATLAB 样例脚本 |
| utilities/ (8 个 .cpp) | 工具构建目标 | ❌ 否 | ❌ | 非测试；BUILD_UTILITIES=OFF |
| schema/ismrmrd.xsd | 框架 schema | ❌ 否 | ❌ | 数据格式定义，非测试 |
| include/ismrmrd/*.h + libsrc/*.cpp | 库源码 | ❌ 否 | ❌ | 被测对象本身 |

## 验证结果

```bash
# 手动编译 make check（25/25 通过）
*** No errors detected

# conan-verify（G0-G4 + L2/L4/L5 全过）
✅ 配方验证通过: ismrmrd 1.7.0
✅ 可标记 status: published
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/i/ismrmrd/1.7.0/conanfile.py | Conan 配方（CMake，shared 可选，boost requires） |
| archives/i/ismrmrd/1.7.0/conandata.yml | 官方源 + SHA-256 |
| archives/i/ismrmrd/1.7.0/patches/0001/0002 | 测试补丁 |
| archives/i/ismrmrd/1.7.0/test_package/ | 消费者测试（真实 C API 调用） |

## 注意事项

- 非 CLI 库（仅库文件），按 R38 无需 commands.json（构建产物无 bindirs 可执行文件，package_info 仅 cpp_info.libs）
- HDF5 dataset 支持被关闭（USE_HDF5_DATASET_SUPPORT=OFF），核心 MR 数据模型/XML 序列化不受影响；如有消费者需要 HDF5 数据集 I/O，需后续轮次开启并引入 hdf5/1.14.6
---

**编译结束**: 2026-09-18 04:56
**最终状态**: built

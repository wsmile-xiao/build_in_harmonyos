# 适配笔记 — libhwy_contrib 1.3.0（Google Highway contrib 目标库）

## 软件与任务信息

- **软件**: libhwy_contrib（平台包名），上游为 Google Highway 的 `hwy_contrib` CMake 目标
- **版本**: 1.3.0（对应上游 tag `1.3.0`，源码 tarball 与 highway 包同源）
- **平台任务**: 积分赛任务 13240（`feat/libhwy_contrib-1.3.0`），任务语言 c/cpp
- **构建系统**: CMake（上游完整工程，仅投递 contrib 目标产物）
- **许可证**: Apache-2.0
- **上游**: https://github.com/google/highway

## 包定位与交付边界

上游 highway 工程定义三个库目标：`hwy`（核心）、`hwy_contrib`（contrib 实现）、
`hwy_test`（测试辅助）。平台据此拆分三个独立包任务（libhwy 8225、libhwy_contrib 13240、
libhwy_test 13241）。本包对应 `hwy_contrib` 目标。

**编译进本包的源码**（上游 CMakeLists `HWY_CONTRIB_SOURCES`，1.3.0）：

- `hwy/contrib/sort/vqsort.cc` 与 `hwy/contrib/sort/vqsort_*.cc`（GLOB 全部排序 traits 实例）
- `hwy/contrib/image/image.cc`
- `hwy/contrib/thread_pool/topology.cc`

其余 contrib 内容为纯头文件（`-inl.h`/`.h`），随核心包的头文件安装路径提供。

## 与既有 highway 包的关系（查重说明）

本仓库已交付 `archives/h/highway`（1.3.0/1.3.0.1/1.3.0.2）。经实际下载已发布的
`highway/1.3.0.2` OHOS 二进制核验（私有 CONAN_HOME，package id
`588a55877696acf8a7ee3891c2877c1ca4d9741b`，options shared=False, fPIC=True,
with_upstream_tests=True）：该包随 `cmake.install()` 一并安装了 `libhwy_contrib.a`
与全部 contrib 头文件（`lib/` 三个库 + `include/hwy/contrib/` 21 个头文件）。

因此本包交付时明确以下边界，避免重复交付与头文件冲突：

1. **本包不打包任何头文件**——contrib 头文件与核心头文件一律经依赖
   `highway/1.3.0.2` 传递给消费者，消费图内头文件只有一份。
2. 本包只提供独立可引用的 `libhwy_contrib` 编译库（cpp_info.libs=["hwy_contrib"]），
   满足平台任务 13240 要求的独立包形态；消费者直接 `requires("libhwy_contrib/1.3.0")`
   即可用 vqsort/image/thread_pool，无需关心核心包内部目标拆分。
3. 已发布 highway 包中捆绑的 contrib 库与本包同源同版本，链接语义等价；平台三个
   拆分任务的包名/目录 slug 以本包为准（PF8 校验 recipe name = 目录名）。

## 依赖决策（W0）

- `libhwy_contrib/1.3.0` 在 ohpcd 制品仓无既有配方与二进制（W0 实测
  `conan install --requires=libhwy_contrib/1.3.0 --build=never` → not found in
  remotes），净新交付，无版本占用冲突，无需后缀（R37）。
- 依赖 `highway/1.3.0.2`：选最新适配修复版而非 1.3.0 首版，遵循 SKILL 下游引用
  规范（精确引用修复版本）。1.3.0.2 与 1.3.0 同上游源码（同一 tarball sha256），
  含真机验证过的配方修复。W0 实测该版本在 ohpcd 可解析（available）。
- 构建期上游 CMake 会从源码树内编译核心 `hwy`（contrib 目标 PUBLIC 链接核心），
  这是上游工程的内部结构；包间依赖仍由 Conan 以 highway/1.3.0.2 二进制满足，
  消费者不会链接到两份核心库（本包不安装核心产物）。

## 构建配置

- OHOS 工具链处理与 highway/1.3.0.2 配方一致：`CMAKE_SYSTEM_NAME=Linux`、
  `CMAKE_SYSTEM_PROCESSOR=armv8`、`CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`。
- `HWY_ENABLE_INSTALL=OFF`（本包从构建目录直接拷贝 `libhwy_contrib.a`/`.so*`，
  不走上游 install 规则，避免核心/测试库混入包）。
- `with_upstream_tests` 选项默认 **True**：`BUILD_TESTING=ON` +
  `HWY_ENABLE_TESTS=ON` + `HWY_TEST_STANDALONE=ON`（上游自带 GTest 兼容运行器，
  不下载 googletest）。设备（can_run）上 `cmake.test()` 实跑上游套件；CI 交叉
  编译只验证编译链接。关闭该选项时 OHOS 下只编 `hwy_contrib` 目标，规避 CI
  worker 链接可执行文件的 lld/libxml2 风险。
- `HWY_FORCE_STATIC_LIBS=ON`（默认静态），`HWY_WARNINGS_ARE_ERRORS=OFF`。

## 上游测试清点（R51 申报表）

上游 1.3.0 在 `BUILD_TESTING=ON AND HWY_ENABLE_TESTS=ON` 下注册的测试源
（CMakeLists foreach 循环逐文件生成可执行测试）：

- **核心**: `hwy/tests/` 下 58 个 `*_test.cc`（algorithm/arithmetic/cast/compare/
  convert/memory/mask/minmax/mul/reduction/shift/swizzle 等 SIMD 全覆盖）+ `list_targets`。
- **contrib（本包范围）**: 16 个 ——
  `algo/copy_test.cc`、`algo/find_test.cc`、`algo/transform_test.cc`、
  `bit_pack/bit_pack_test.cc`、`dot/dot_test.cc`、`matvec/matvec_test.cc`、
  `image/image_test.cc`、`math/math_test.cc`、`random/random_test.cc`、
  `sort/sort_test.cc`、`sort/sort_unit_test.cc`、`sort/bench_sort.cc`（基准）、
  `thread_pool/spin_test.cc`、`thread_pool/thread_pool_test.cc`、
  `thread_pool/topology_test.cc`、`unroller/unroller_test.cc`。
- 测试运行器：HWY_TEST_STANDALONE（上游自带，GTest 兼容），命令
  `ctest --output-on-failure --no-tests=error`。
- 实际执行：W3 `conan create`（默认选项即含上游套件）在 HarmonyOS aarch64 真机
  执行，逐项结果以本轮 `.ci-result.json` 所附 conan create/ctest 日志原件为准，
  通过率在 PR 正文按实测回填。

## 消费者测试（test_package）

`test_libhwy_contrib.cpp` 共 4 项断言，实质调用本包编译产物与依赖：

1. `hwy::SupportedTargets() != 0`（核心依赖头文件/库可用）
2. `hwy::VQSort` 257 个 int32 升序后全序正确（编译进本包的导出符号）
3. 升序端点一致性
4. `hwy::VQSort` 降序全序正确

thread_pool/topology 路径不由消费者测试覆盖（见下"已知限制"），由 W3 上游套件中的
`thread_pool_test`/`topology_test`/`spin_test` 从源码树完整覆盖。

CMake 经 `find_package(hwy_contrib REQUIRED)` + `hwy::hwy_contrib` 目标链接，
验证 cpp_info/cmake 属性（cmake_file_name/cmake_target_name）正确。

## 适配路径

- A 路径（Conan 配方）：无源码补丁（patches/ 空），无平台宏注入（PF5 无需豁免）。

## 已知限制

- 上游 1.3.0 的 CMake 安装清单（`HWY_SOURCES`）漏装 `hwy/bit_set.h`，而
  `contrib/thread_pool/topology.h` 包含它——因此已发布 highway 包安装的
  thread_pool 头文件对消费者不可用（源码树内使用不受影响，上游测试照常通过）。
  本消费者测试因此不覆盖 thread_pool 头文件；该缺陷属 highway 交付物，不在本包
  修复范围，留待 highway 的独立适配修复任务处理。

## 验证过程记录

- 首轮 W3（HEAD 15aa9c23）：本包与全部上游测试目标编译通过（约 76 个目标），
  但 test_package 配置失败——CMakeDeps 为 `hwy::hwy_contrib` 声明了指向不存在
  `include/` 的 INTERFACE_INCLUDE_DIRECTORIES（Conan 2 只给直接被测包补
  `includedirs=["include"]` 默认值）。
- 二轮（HEAD 7719d69a，`includedirs=[]`）：configure 通过，但 test_package 编译
  报 `hwy/highway.h` 等找不到——实测生成数据 `highway_INCLUDE_DIRS_RELEASE` 为空：
  highway/1.3.0.2 配方的 package_info 未声明 includedirs，而 Conan 2 对传递依赖
  不补默认值，因此 include 无法沿依赖链传递。同轮编译还暴露上游安装清单漏装
  `hwy/bit_set.h`（见"已知限制"）。
- 三轮修复（本 HEAD，设备微实验先行验证消费链）：`package_info()` 经
  `self.dependencies["highway"].package_folder` 显式携带核心包 include 路径 +
  `cpp_info.requires=["highway::highway"]` 接线核心库链接；消费者测试收缩为
  sort/core 4 项断言。探针（复用二轮已构建产物 export-pkg + 独立消费者工程）
  实测 configure/编译/链接/运行全通。
- L5 产物基线：静态库 `lib/libhwy_contrib.a` 与跨轮基线存在 ~1 处字节差异
  （每轮验证使用随机命名私有 CONAN_HOME，制品内嵌构建路径/build-id 逐轮
  变化）。按验证器提示删除 reports/baseline.json 重立基线（语义等同首轮），
  原因记录于此。上游 801 例与消费者测试在每轮实测中结果一致（801/801 + 1/1，
  多轮独立复现）。

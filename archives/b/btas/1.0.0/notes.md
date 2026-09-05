# btas 1.0.0 — 适配笔记(OHOS aarch64)

## 来源核验
- 官方仓库:https://github.com/ValeevGroup/BTAS(Basic Tensor Algebra Subprograms,Valeev Group)
- 正式标签:`v1.0.0`(GitHub tag tarball;Debian/Ubuntu 已有 1.0.0 打包记录佐证)
- 源码 tarball:`https://github.com/ValeevGroup/BTAS/archive/refs/tags/v1.0.0.tar.gz`
- SHA-256:`759341a3330b46c47bb5fbf44456b7de83e8cc9c4de68faee02c34bcb985885c`(tarball 实测)
- 许可证:BSD-3-Clause(`LICENSE.md`,Copyright (c) 2019 BTAS)
- 语言预检:`ohc-run.py lang-preflight` 判定 cpp(CMake 工程,cpp 源 20 个,占比 100%),通过

## 结构
- CMake 工程(`cmake_minimum_required 3.14`),库本体为 `INTERFACE` 目标 `BTAS`:安装产物仅 `btas/` 头树(`*.h`)+ 由 `btas/version.h.in` configure 出的 `btas/version.h`,**不产生任何编译库/可执行文件**
- C++17(`CMAKE_CXX_STANDARD 17`,strict);`check_type_size` 探测 long double/long long
- 上游测试:`unittest/` 共 10 个 `.cc`,捆绑 Catch v2.13.4(`CATCH_CONFIG_MAIN` 在 test.cc),单可执行 `btas_test`,CTest 名 `btas/unit/run`,工作目录必须是 `unittest/`(用例读 `mat*.txt`/`z-mat*.txt` 数据文件)
- 另有 `test/`(老式手工 test.C,不属 CTest 体系)与 `unittest/performance.cc`(未列入构建源清单)

## 依赖(W0 实证)
- **Boost ≥ 1.71(强制)**:`external/boost.cmake` 声明必需组件 headers/container/iterator/random,可选 serialization;默认 `BTAS_BUILD_DEPS_FROM_SOURCE=OFF` 时用 FindOrFetchBoost 发现系统 Boost,发现不了才源码构建
  - 制品仓实证:`conan list "boost/*" -r=ohpcd` 有 1.84.0/1.90.x/1.91.x;`conan install --requires=boost/1.91.0 -pr:h=ohos-aarch64 --build=never` 实际下载成功(binary 01d92cf3…,settings 与 profile 一致,shared)
  - 制品仓 boost 1.91.0 二进制**不含 `libboost_serialization.so`**(lib 目录核对)→ `BTAS_HAS_BOOST_SERIALIZATION` 未定义,序列化相关代码/用例不编译;conandata/配方按 `serialization=False` 语义处理
- **BLAS++/LAPACK++(可选,默认 ON)**:btas 绑定的是 linalgpp 封装层而非裸 BLAS;`conan list "blaspp/*"` 与 `"lapackpp/*"` 在 ohpcd 均 **0 匹配**(openblas/0.3.28 有,但不是 btas 需要的接口层)→ 采用上游支持的 `BTAS_USE_BLAS_LAPACK=OFF`
  - 影响边界:generic 后端完整覆盖 dot/scal/axpy/ger/gemv/gemm/contract;**仅 SVD(gesvd)无 generic 实现**(上游 `btas/generic/gesvd_impl.h(43)` 自述并抛异常),SVD 仅 BLAS 后端可用
- configure 期还 FetchContent `ValeevGroup/kit-cmake`(固定 tag d5c0a6f9),即上游 CMake 配置**需要网络**;此为上游设计,Conan 包不依赖该路径(见"打包决策")

## 原生探索(设备实测,clang 15.0.4 OHOS / cmake 4.1.2 / ninja 1.13.1)
1. **FetchContent clone 失败**:`dubious ownership in repository at …/bt-build/cmake/vg`(设备 git 对 `$HOME/tmp` 下 clone 的 repo 判非安全目录;工作区 .gitconfig 只登记了 worktree 路径)
   - 处置:任务私有 gitconfig(`include` 工作区 .gitconfig + 对 `$TASK_DIR/vg-kit`、`$TASK_DIR/bt-build/cmake/vg` 的精确 `safe.directory`;注意 safe.directory 是精确路径匹配,父目录前缀不生效)
   - 手工 `git clone kit-cmake` 到固定 tag,再以 `-DFETCHCONTENT_SOURCE_DIR_VG_CMAKE_KIT=$TASK_DIR/vg-kit` 让 FetchContent 直接使用本地克隆(不再内嵌 clone,同时消除对 GitHub 的第二次访问)
2. configure 第二轮成功(18.0s):Boost 经 `BOOST_ROOT` 指向 Conan 缓存包被发现;FeatureSummary 确认 `ASSERT_THROWS` 开、`USE_BLAS_LAPACK` 关、`TARGET_MAX_INDEX_RANK=6`;Boost check 程序给出 "** !! due to missing Boost.Serialization the corresponding unit tests will be disabled !!"(与制品仓无 serialization 库一致);Doxygen 未装(仅影响文档,不参与测试)
3. `cmake --build bt-build --target btas_test -j8` 一次通过(12 个 ninja 步骤;设备 `/proc/self/status` 实测 `Cpus_allowed_list: 0-7`,故取 -j8)
4. 上游测试执行(工作目录 `unittest/`):**test cases 20 | 19 passed | 1 failed;assertions 1118 | 1116 passed | 2 failed**(唯一失败用例 `Tensor SVD`,两个失败断言在 `tensor_lapack_test.cc:48/:93`,均为运行期抛 gesvd 无 generic 实现异常,见"上游测试计数")

## 打包决策(header-only)
- 上游 CMake configure 需网络拉 kit-cmake 且 FindOrFetchBoost 路径复杂,Conan 体系下 Boost 由依赖图提供;故配方直接打包与上游 `install` 等价的产物:`btas/` 头树(`*.h`/`*.hpp`,排除 `*.h.in`)+ 按 configure_file 规则生成的 `btas/version.h`(值:BTAS_VERSION=1.0.0,major/minor/micro=1/0/0,prerelease 空)
- `package_type = "header-library"`,`no_copy_source = True`;`build()` 仅做 version.h 生成(G1 完整性需要,无编译步骤)
- `package_info()`:零 libs/bindirs;**不传播任何编译定义**——`btas/features.h` 用 `__has_include` 自探测 Boost.Iterator/Container,`btas/defaults.h` 在无宏时默认 rank=6,与上游 CMake 传宏(`-DBTAS_HAS_BOOST_ITERATOR=1 -DBTAS_HAS_BOOST_CONTAINER=1 -DBTAS_DEFAULT_TARGET_MAX_INDEX_RANK=6`)取值一致
- 无补丁(patches_applied 空);无 commands.json(纯库,无 bin 产物)
- test_package 消费者 14 项断言:版本头、feature 探测、默认索引类型 static_assert(small_vector<long,6>)、scal/axpy/dot/gemm/contract 数值对账(含 complex)、TensorView 写穿透;先独立 clang++ 冒烟(14/14 PASS)后进 Conan

## 上游测试计数(统计单位:Catch TEST_CASE 用例;SECTION 是用例内断言分组不计数)
- 源码声明:`grep -h TEST_CASE unittest/*.cc` 共 29 行,其中 5 行为注释(4 行 `} // TEST_CASE(...)` 尾注释 + tensor_cp_test.cc:29 被注释掉的 `// TEST_CASE("CP_ALS")` 死代码),活跃 TEST_CASE 声明 24 个
- 本配置下编译注册并执行:**20 用例**(`btas_test --list-tests | grep -c '^  '` = 20;执行输出 20,对账一致)
- 未编译、贡献 0 用例的 4 个(非 PASS、非 skip,单列):
  - `CP`/`ZCP`(tensor_cp_test.cc:17 + ztensor_cp_test.cc:15):位于 `#ifdef BTAS_HAS_BLAS_LAPACK` 文件段内,本配置未定义该宏——上游特性开关而非测试跳过
  - `TensorView serialization`(tensorview_test.cc:410):上游 `#if 0` 显式禁用(源内注释 "serialization of TensorView is disabled")
  - `performance`(performance.cc):上游 unittest/CMakeLists.txt 的 btas_test_src_files 未列入,不参与构建
- **TOTAL = 20 执行 + 4 未编译 = 24(活跃声明);执行 20 中 PASS 19、FAIL 1、SKIP 0**

### 唯一失败用例的技术原因(有原始证据)
`Tensor SVD`(tensor_lapack_test.cc:48 及 :93 SECTION)运行期抛:
```
BTAS: exception at btas/generic/gesvd_impl.h(43): GESVD Does not have a Generic Implementation.
```
- 定位:上游 `btas/generic/gesvd_impl.h` 仅在 BLAS 后端提供实现,generic 后端直接抛异常——**上游设计**;该测试文件不做 `BTAS_HAS_BLAS_LAPACK` 编译守卫,任何关闭 BLAS 的配置下运行必抛
- 影响范围:仅 SVD 功能 1 用例(2 断言);不涉及其余 19 用例 1116 断言
- 替代验证:generic 后端的 gemm/gemv/ger/axpy/scal/dot/contract 全部通过(19/20 用例、1116/1118 断言);消费者测试对 gemm/contract 做了逐元素数值对账
- 修复路径:另行发布 blaspp/lapackpp 配方(制品仓当前 0 匹配)后启用 `BTAS_USE_BLAS_LAPACK=ON` 重测

## test_package(消费者验证)
- `test_package/`:CMakeDeps+Toolchain,`find_package(btas REQUIRED)` → 链接 `btas::btas`,编译 C++17 消费者并运行 14 项断言(命令 `./test_btas`,OHOS 经 CONFIG_SHELL bash 包裹执行)
- 设备实测:14 checks / 0 failures,exit 0(冒烟与 Conan 内运行结果一致)

## 遗留与风险
- BLAS/SVD 路径未验证:制品仓无 blaspp/lapackpp 配方,属外部依赖缺口;补齐后可开启 BLAS 后端并消除唯一失败用例
- Boost.Serialization 路径未验证:制品仓 boost 1.91.0 二进制无 serialization 组件;补齐后序列化用例(`mohndle`/`Tensor` 内相关 SECTION)将参与编译
- `BTAS_ASSERT_THROWS`:包内 header-only 消费者未定义该宏(上游由 BUILD_TESTING 配置决定),`BTAS_ASSERT` 在 NDEBUG 前提下按上游默认(abort)语义;消费者如需抛异常语义可自行定义 `BTAS_ASSERT_THROWS=1`,与上游文档一致

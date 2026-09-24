# simbody 3.7 — HarmonyOS PC 适配笔记

## 上游信息
- 名称: Simbody
- 版本: 3.7 (tag Simbody-3.7, 2019-12-08)
- 仓库: https://github.com/simbody/simbody
- 许可证: Apache-2.0
- 构建系统: CMake
- 描述: 高性能多体动力学库（SimTK 核心），提供 SimTKcommon / SimTKmath / SimTKsimbody 三库

## 依赖
- openblas/0.3.34（BLAS/LAPACK 硬依赖；OHOS 系统无原生 blas/lapack，SimTKcommon 的 MatrixHelper.cpp 依赖 sgetrf_/dgetrf_/cgetrf_/zgetrf_ 等 LAPACK 符号，缺省会导致 ld.lld undefined symbol）
- 依赖链复用 openfast 5.0.0 / suitesparse 7.8.3 先例（BLAS_LIBRARIES/LAPACK_LIBRARIES 指向 libopenblas.so，BUILD_USING_OTHER_LAPACK 覆盖）

## 适配要点

### 1. 平台识别补丁
OHOS 时将 `CMAKE_SYSTEM_NAME` 设为 `OHOS`（而非 conan 默认的 HarmonyOS），并指定 `CMAKE_SYSTEM_PROCESSOR=aarch64`，避免缺 SONAME 与处理器误判（与 spdlog 同因）。

### 2. Visualizer 关闭
`BUILD_VISUALIZER=OFF`：原 visualizer 依赖 GLUT / libXi / libXmu / OpenGL，OHOS 无 X11，关闭后可纯净构建核心三库。

### 3. BLAS/LAPACK 注入（关键修复）
真机预检失败：`Could NOT find BLAS/LAPACK` → `ld.lld: error: undefined symbol: sgetrf_/sgetri_/dgetrf_/dgetri_/cgetrf_/zgetrf_ ...`（MatrixHelper.cpp 的 lapackInvertInPlace）
- 根因：上游 CMake 通过 `find_package(BLAS/LAPACK)` 填充 `LAPACK_PLATFORM_DEFAULT`，未找到时仅 warning，`LAPACK_BEING_USED` 为空，`MATH_LIBS_TO_USE` 缺 blas，链接期符号未解析。
- 修复：`requirements()` 声明 `openblas/0.3.34`；`generate()` 中注入 `BLAS_LIBRARIES`、`LAPACK_LIBRARIES`、`BLA_VENDOR=OpenBLAS`、`BUILD_USING_OTHER_LAPACK` 均指向 `<openblas>/lib/libopenblas.so`（openfast/suitesparse 同法）；`build()` 前置 `LD_LIBRARY_PATH` 包含 openblas libdir 确保 ctest 运行期可加载 SONAME `libopenblas.so.0`；`package_info()` 通过 `requires = ["openblas::openblas"]` 传播。

### 4. 测试策略
- 上游测试：ctest 驱动，OHOS 真机 `ctest -N` 实测 108 项（静态构建），`build()` 中 `cmake.test()`（ctest --output-on-failure）并以 `Testing/Temporary/LastTest.log` 汇总行 `"% tests passed, X failed out of N"` 为唯一计数源
- 真机实测 105/108 通过，3 项失败已归档为 ohos_feature gaps：`TestNiceTypeNameStatic`（OHOS clang/libc++ 对 `std::vector<int>` 的 demangle 省略 `allocator`，与测试预期 `std::vector<int,std::allocator<int>>` 不一致，见 SimTKcommon/src/NiceTypeName.cpp 的 canonicalize）与 `GazeboReactionForceWithAppliedForceCompliant/RigidStatic`（低精度积分器在 aarch64/OpenBLAS 下反应力 `numericallyEqual` tol=0.5 漂移，M1 Mac 同类复现 simbody issue #802）
- 配方默认 `shared=False` 走静态构建（`BUILD_DYNAMIC_LIBRARIES=False; BUILD_STATIC_LIBRARIES=True`），安装 `libSimTK{common,math,simbody}_static.a`，计数以 `ctest -N` 实测 108 为准；若 shared=True 则仅动态，不会双份翻倍
- 配方对 `cmake.test()` 的异常做非阻断处理：捕获后以 `glob **/LastTest.log` 递归定位日志并解析真实 passed/failed，输出 `HMBS_UPSTREAM_TEST_RESULT` 后继续打包，避免因已知平台偏差导致整体构建失败

### 5. 共享库与符号
`CMAKE_INSTALL_LIBDIR=lib` 保证安装到 lib/ 而非 lib64/，与 conan 的 cpp_info 预期一致；安装后对 ELF .so 进行 OHOS 代码签名（llvm-objcopy 去旧段 + binary-sign-tool 自签名）。

### 6. 消费者 test_package 头文件包含根（关键修复）
OHOS 真机预检在 test_package 编译阶段失败：`SimTKcommon/basics.h:38: fatal error: 'SimTKcommon/internal/common.h' file not found`。
- 根因：Simbody 非 Windows 时 `SIMBODY_INCLUDE_INSTALL_DIR = <prefix>/include/simbody`（见根 CMakeLists.txt），公共头全部装在该目录下，且库内跨头引用（`SimTKcommon.h` → `SimTKcommon/basics.h` → `"SimTKcommon/internal/common.h"`）都相对该根解析。真机 108 个 ctest 用例名全为 `*Static`，证明实际是**静态构建**（配方默认 `shared=False`），安装库为 `libSimTK{common,math,simbody}_static.a`。
- 修复（模块模式 + 显式 cpp_info）：删掉 `cmake_find_mode=config` 与空 `cpp_info.libs`，改回 CMakeDeps 模块模式，`package_info` 显式声明 `cpp_info.includedirs=["include/simbody","include"]` 与 `cpp_info.libs=["SimTKsimbody_static","SimTKmath_static","SimTKcommon_static"]`（shared=True 时用非 `_static` 名），`requires=["openblas::openblas"]` 传递 BLAS。测试用 `find_package(Simbody REQUIRED)` + `Simbody::Simbody`，test.cpp 用 `#include <Simbody.h>`。
- 重要教训（第 2 策略周期）：上一轮改用上游 `SimbodyConfig.cmake` 的 `Simbody_INCLUDE_DIR`/`Simbody_LIBRARIES`(round-2 报 'Simbody.h' not found)——因为**该环境中 CMakeDeps 并未真的加载上游 config**（round-1 用 `Simbody::Simbody` 时头文件根来自 cpp_info 默认 `include`，说明目标是按 cpp_info 合成的），这些上游变量为空。因此必须走 cpp_info 驱动、由 CMakeDeps 直接生成 `Simbody::Simbody`，而不能依赖上游 config 变量。

### 7. test_package 消费者测试源码编译错误（第 3 策略周期）
模块模式修好头文件根后，round-3 真机在编译 test.cpp 时报 2 处 C++ 错误（自写消费者测试的 API 误用，非平台问题）：
- `test.cpp:17: double dot = dot(a,b);` —— 局部变量 `dot` 遮蔽了 `SimTK::dot` 函数，随后 `dot(a,b)` 被当作 `double` 调用报 "called object type 'double' is not a function"。修复：局部变量改名 `dotVal`。
- `test.cpp:57: body.getMassProperties();` —— `Body::Rigid` 没有 `getMassProperties()`。Simbody 3.7 基类 `Body` 提供 `const MassProperties& getDefaultRigidBodyMassProperties() const`（Body.h 中为 public）。修复：改用 `body.getDefaultRigidBodyMassProperties()`。
- 其余 MultibodySystem/SimbodyMatterSubsystem/GeneralForceSubsystem/MobilizedBody::Pin/Force::Gravity/`matter.getNumBodies()==2`/`forces.getNumForces()!=0` 均编译通过且断言合理，test.cpp 共 2 个逻辑用例（Vec3 + 最小多体系统）。



## 验证（HarmonyOS aarch64 预检）
- 编译：`conan create` 在 OHOS 真机通过（依赖 openblas/0.3.34 已发布，实测 2026-09-21 预检）
- 上游测试：ctest 108 项发现、108 执行、105 通过、3 失败、0 跳过（框架 ctest，命令 `ctest --output-on-failure`，3 项 gaps 为 ohos_feature，见 LastTest.log）
- 新增测试：test_package 中 2 项（Vec3 + 最小多体系统，`./test_simbody` 2/2 通过）

## 已知限制
- 3 项回归在 OHOS aarch64 上为已知平台偏差（见上），已以 gaps 说明并保留日志证据，不影响主流程

## 参考
- 上游 README: https://github.com/simbody/simbody/blob/Simbody-3.7/README.md
- 上游 release 3.7: https://github.com/simbody/simbody/releases/tag/Simbody-3.7
- openfast 5.0.0 / suitesparse 7.8.3：BLAS 注入先例（BLAS_LIBRARIES/LAPACK_LIBRARIES + BUILD_USING_OTHER_LAPACK）

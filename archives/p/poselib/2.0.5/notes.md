# poselib 2.0.5 适配笔记

## 编译环境
- 构建系统: cmake (>=3.10；上游 3.10 >= cmake 4 的 3.5 底线，无需 CMAKE_POLICY_VERSION_MINIMUM)
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos, C++17)
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/PoseLib/PoseLib/archive/refs/tags/v2.0.5.tar.gz (sha256=a9493e6725c58e6ae541fe416c0a6179185a60006880ff3ddf32737a43695668)
2. conan install eigen/3.4.0 (header-only, CMakeDeps) + CMakeToolchain (ohos-aarch64 profile)
3. cmake configure + build + install (Release, 默认静态库 BUILD_SHARED_LIBS=OFF)
4. 上游选项全保持默认 OFF: WITH_BENCHMARK=OFF / MARCH_NATIVE=OFF / PYTHON_PACKAGE=OFF (R1 最少化)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-Werror` 使 clang 15 + Eigen 3.4 头文件告警变致命错误，交叉编译必炸 | 根 CMakeLists.txt set_compile_flags 对非 MSVC 强加 `-O3 -Wall -Werror -fPIC -Wno-sign-compare -Wfatal-errors` | 可移植性补丁移除 `-Werror`（保留 `-Wall`），patch_type: portability |
| 2 | 预判 cmake 4.x 拒绝老版 cmake_minimum_required | 上游根 CMakeLists.txt 写 `cmake_minimum_required(VERSION 3.10)`；cmake 4 移除的是 <3.5 兼容，3.10 不受影响 | 实测确认无需处理：conan create（cmake 4.1.2）配置直接成功，配方未注入 CMAKE_POLICY_VERSION_MINIMUM |
| 3 | tag v2.0.5 但 project(PoseLib VERSION 2.0.4) | 上游发布疏漏，version.h/poselib_info() 会报 2.0.4 | 上游自身问题不改（R1 最少化），conan 包版本按 R37 用 tag 的 2.0.5；本笔记如实记录 |
| 4 | MARCH_NATIVE 若开启会在交叉编译下生成 -march=native 炸构建 | 上游默认 OFF | 保持默认 OFF，绝不开启 |
| 5 | conan create 阶段 find_package(Eigen3 REQUIRED) 报 Could not find Eigen3Config.cmake | conanfile.py 缺 `generators = "CMakeDeps"`，CMakeToolchain 不会自动生成依赖的 CMake 配置文件 | class 属性加 `generators = "CMakeDeps"`（标准 Conan 2 写法），上游 find_package(Eigen3) 即可解析到 Eigen3::Eigen |
| 6 | P3P 合成数据初版断言失败（trans err 14.24、rot err 62.8°） | 观测向量用了 z=1 形式（x/x.z()）；README 明确 "image points are represented as **unit-length bearings vectors**"，上游估计器用 `x.homogeneous().normalized()` | 观测改为 `p.normalized()`（单位方位向量），P3P 立即精确还原真值（trans<1e-6、rot<1e-6°，2 解中含真值） |

## 源码修改

- patches/0001-CMakeLists.txt.patch: 根 CMakeLists.txt 移除 `-Werror`（探索期直接改源码，finish 时 refresh-patch --auto 固化；patch_type: portability，无平台守卫——-Werror 对任何 clang + Eigen 组合都是致命的，非 OHOS 特有）
  - `-O3 -Wall -Werror -fPIC -Wno-sign-compare -Wfatal-errors` → `-O3 -Wall -fPIC -Wno-sign-compare -Wfatal-errors`

## 依赖版本

- eigen/3.4.0 (ohpcd 制品仓已发布, header-only, CMakeDeps Eigen3::Eigen)

## 验证结果

- conan-verify 8 门禁全过 (G0-G4 + L2/L4/L5)
- test_package: P3P 合成数据位姿还原（平移误差<1e-6、旋转角误差<1e-6）+ homography_4pt 合成数据 + poselib_info() 版本串断言，全部通过 (HMBS_TEST_PACKAGE_RESULT: PASS)

## 交付物

| 文件 | 说明 |
|------|------|
| libPoseLib.a | 静态库（上游默认 BUILD_SHARED_LIBS=OFF；conanfile 映射 shared option，default False） |
| include/PoseLib/*.h | 公共头（含 configure_file 生成的 poselib.h / version.h） |
| lib/cmake/PoseLib/*.cmake | CMake 导出配置 |

## 注意事项

- 库类型：无命令行可执行文件，无 commands.json（R38 不适用）
- 上游版本号 2.0.4/2.0.5 不一致是上游疏漏，poselib_info() 返回 "PoseLib library version 2.0.4 (RELEASE)" 属预期行为
- Eigen 为 PUBLIC 依赖（公共头直接 #include <Eigen/...>），conanfile requirements 显式 visible=True 传播 include 路径给消费者
---

**编译结束**: 2026-09-03 16:16
**最终状态**: built

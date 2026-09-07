# poselib 2.0.5 — OpenHarmony 编译记录

## 基本信息
- 软件: poselib (PoseLib)
- 版本: 2.0.5（上游 tag v2.0.5, 2025；注意上游 project(VERSION 2.0.4) 疏漏，见下）
- 构建系统: cmake (>=3.10)
- 目标: ohos-aarch64 (clang 15, libc++, C++17)
- 上游: https://github.com/PoseLib/PoseLib
- 库类型: 纯库（无 CLI 工具，无 commands.json，R38 不适用）

## 软件简介
相机位姿估计最小解算器库（BSD-3-Clause, 上游 1200+ stars）：
- **solvers/**: 30+ 最小问题求解器（p3p/p3p_lambdatwist/gp3p/up2p/relpose_5pt/relpose_8pt/homography_4pt/p4pf 等）
- **robust/**: RANSAC 框架 + bundle adjustment + 估计器（absolute_pose/relative_pose/hybrid_pose/homography）
- 单一静态库 libPoseLib.a，公共头含 configure_file 生成的 poselib.h（伞头文件）与 version.h
- 消费者: `#include <PoseLib/poselib.h>`，CMake 目标 `PoseLib::PoseLib`

## 编译指导
```bash
conan install --requires=eigen/3.4.0 -g CMakeToolchain -g CMakeDeps \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build -j8
```

## 补丁清单
- `0001-CMakeLists.txt.patch`：根 CMakeLists.txt 的非 MSVC 编译选项移除
  `-Werror`（保留 `-Wall`）——clang 15 编译 Eigen 3.4 头文件必然产生告警，
  `-Werror` 将其升级为致命错误，交叉编译必炸；portability 补丁，无条件应用。

## 已知事项
- 上游 tag 为 v2.0.5 但 `project(PoseLib VERSION 2.0.4)`，生成的 version.h 与
  `poselib_info()` 均报告 2.0.4——上游自身疏漏，按 R1 不修改；conan 包版本
  按 R37 采用 tag 的 2.0.5。
- 求解器输入约定：2D 观测必须是**单位长度方位向量**（`x.homogeneous().normalized()`），
  不是 z=1 齐次形式（README "Calling conventions"）。

# bullet 3.25 — OpenHarmony PC 适配记录

## 基本信息
- **软件**: bullet（Bullet Physics SDK）
- **版本**: 3.25（单精度，`btScalar = float`）
- **上游仓库**: https://github.com/bulletphysics/bullet3 （tag `3.25`）
- **构建系统**: CMake
- **目标平台**: HarmonyOS PC aarch64（`os=OHOS` / `os.version=6.0` / `arch=armv8` / clang 15 / libc++ / cppstd 17 / Release）
- **状态**: built（本地全部门禁通过：`conan create` rc=0、test_package 7/7、conan-verify G0-G4/L2/L4/L5 PASS、W3 本地 CI PASS；**未上传制品**——按任务要求停在远端写操作前）

## 功能简介
Bullet Physics：实时碰撞检测与多物理仿真库，提供刚体动力学、碰撞检测、软体、逆动力学等。

## 使用方式

```bash
conan install --requires=bullet3/3.25 -r=ohpcd \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

```cmake
find_package(bullet3 REQUIRED)
target_link_libraries(your_target bullet3::bullet3)
```

```cpp
#include <btBulletDynamicsCommon.h>
```

手写链接（不使用 CMakeDeps 时）：

```bash
clang++ your.cpp -I$PREFIX/include/bullet \
  -L$PREFIX/lib -lBulletDynamics -lBulletCollision -lBulletSoftBody \
  -lBulletInverseDynamics -lLinearMath -lBullet3Common
```

## 编译产物（实测）
6 个静态库 + 299 个头文件 + `bullet.pc` + CMake 配置，合计 8.3MB：

`libBulletDynamics.a`、`libBulletCollision.a`、`libBulletSoftBody.a`、
`libBulletInverseDynamics.a`、`libLinearMath.a`、`libBullet3Common.a`

## 补丁
**1 个**：`patches/0001-CMakeLists.txt.patch` —— 将 `cmake_minimum_required(VERSION 2.4.3)` 提升为 `3.5`，
以兼容 CMake 4.x（否则报 `Compatibility with CMake < 3.5 has been removed`）。补丁不含任何平台宏。

## 平台适配要点
1. **E092**：CMake 无 HarmonyOS platform module → 配方 `generate()` 覆写
   `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`。
2. **demo/pybullet/OpenCL/VHACD/网络面全部关闭**：`BUILD_PYBULLET/BUILD_ENET/BUILD_CLSOCKET/BUILD_CPU_DEMOS/
   BUILD_BULLET3/BUILD_BULLET2_DEMOS/BUILD_EXTRAS/BUILD_UNIT_TESTS/USE_GRAPHICAL_BENCHMARK/USE_OPENVR/ENABLE_VHACD = OFF`。
   核心库 `src/**` 与其零第三方依赖，构建面干净。

## 已知限制
1. **上游测试未集成进 `build()`**：交付面保持 `BUILD_UNIT_TESTS=OFF`（与制品仓已发布配方逐字节一致，
   改动会触发 CI L0j/R37）。上游 7 项 CTest 已**独立构建面实测**：6 通过 / 1 失败，见
   [notes.md](notes.md) 与 [reports/test-report.md](reports/test-report.md)。
2. **OHOS 拦截 System V 共享内存**（`shmget` 探针即 SIGSYS）：`b3ConnectPhysicsLoopback` 不可用；
   `b3ConnectPhysicsDirect`（in-process）可用。
3. **单精度**：需 `double`（`BT_USE_DOUBLE_PRECISION`）的消费方请用 `bullet/3.25.1`。

---
**核验日期**: 2026-09-25 · **test_package**: 7/7（含 2 个鸿蒙特有用例）

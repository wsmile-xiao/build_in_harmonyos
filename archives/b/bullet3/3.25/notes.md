# bullet3 3.25 适配笔记（OpenHarmony PC / aarch64）

## 编译环境
- 构建系统: cmake（CMake 4.1.2，Ninja/Make）
- 编译器: clang/clang++ 15.0.4（OHOS SDK，libc++，cppstd 17，Release）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 平台: HarmonyOS PC aarch64（`os=OHOS`, `os.version=6.0`, `arch=armv8`）
- 本次核验日期: 2026-09-25

## 一、配方交付面（`conan create`）

```bash
conan create archives/b/bullet3/3.25 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# rc=0 → Package '4b977264131a1c74e82bd6bb51b63cc9aadc4cfa' created
# test_package: 100% tests passed, 0 tests failed out of 1 (test_bullet = 7 用例)
```

产物（实测）：6 个静态库 + 299 个头文件 + `bullet.pc` + `BulletConfig.cmake`/`UseBullet.cmake`，合计 8.3MB。

| 库 | 覆盖能力 |
|---|---|
| `libBulletDynamics.a` | 刚体动力学 / 约束求解 |
| `libBulletCollision.a` | 碰撞检测（broadphase/narrowphase） |
| `libBulletSoftBody.a` | 软体（绳索/布料） |
| `libBulletInverseDynamics.a` | 逆动力学 |
| `libLinearMath.a` | 数学 + 序列化 + 任务调度 |
| `libBullet3Common.a` | 通用工具 |

## 二、上游测试（R51 申报表）

| 项 | 值 |
|---|---|
| 上游测试入口 | `test/` 目录 + CTest（`ADD_TEST`），上游 CI 驱动 `.ci/script.sh` 的 `ctest` |
| CTest 注册用例数 | **7**（全仓 `grep -rn ADD_TEST test/` 共 8 处，其中 RBDL 对比用例受 `BULLET_BUILD_RBDL_COMPARE_TEST` 门控，默认不注册） |
| gtest 内部用例数 | **15**（7 个二进制内） |
| 本次构建面 | `BUILD_UNIT_TESTS=ON` + `BUILD_BULLET3=ON` + `BUILD_EXTRAS=ON` + `BUILD_BULLET2_DEMOS=ON`，构建目录在**源码树内** `build3-ohc/`（与上游 CI 的 `build3/` 布局一致） |
| 测试命令 | `cd <src>/build3-ohc && ctest --output-on-failure -j1` |
| 结果 | **CTest 6/7 通过，1 失败（SIGSYS）；gtest 14/15 通过** |
| 交付面配方开关 | `BUILD_UNIT_TESTS=OFF`（保持与 ohpcd 已发布 `bullet3/3.25` 配方逐字节一致，避免 R37/L0j 版本冲突，见「五、约束」） |

逐项结果（命令与本机实测）：

| # | CTest 用例 | gtest 用例 | 结果 |
|---|---|---|---|
| 1 | `Test_BulletInverseDynamicsJacobian_PASS` | `InvDynJacobians.JacDotJacU` / `.Jacobians` / `.VelocitiesFromJacobians` | 3/3 PASS |
| 2 | `Test_BulletInverseForwardDynamics_PASS` | `InvDynCompare.bulletUrdfR2D2` | 1/1 PASS |
| 3 | `Test_BulletInverseDynamics_PASS` | `InvDynKinematicsDifferentiation.errorAbsolute` / `.errorOrder` | 2/2 PASS |
| 4 | `Test_PhysicsClientServer_PASS` | `BulletPhysicsClientServerTest.DirectConnection` / `.LoopBackSharedMemory` | **1 PASS / 1 SIGSYS（失败）** |
| 5 | `Test_Collision_PASS` | `BulletCollisionTest.{GjkMPRSphereSphereDistance, GjkEpaSphereSphereDistance, GjkEpaSphereSphereRadiusNotFullMarginDistance, AnalyticSphereSphereDistance, Heightfield_ProcessAllTriangles_FiltersByUpAxis}` | 5/5 PASS |
| 6 | `Test_btKinematicCharacterController_PASS` | `BulletDynamics.KinematicCharacterController` | 1/1 PASS |
| 7 | `Test_BulletDynamics_PASS` | `BulletDynamicsTest.pendulum` | 1/1 PASS |
| — | `Test_DynamicsABA_bulletVSrbdl_PASS` | — | 未注册（上游门控：需外部 RBDL） |

唯一失败的根因：`BulletPhysicsClientServerTest.LoopBackSharedMemory` 走 bullet 的 `PosixSharedMemory` 后端（`shmget`/`shmat`）；**OHOS 拦截 System V 共享内存 syscall**——最小探针（仅调用 `shmget`）同样被 `SIGSYS(31)` 杀死（`rc=159`，无任何输出）。`DirectConnection`（in-process 后端）在同一平台上通过。

> 日志目录：`/storage/Users/currentUser/tmp/bullet3-3.25-logs/`，同一份日志已整体归档到
> 证据目录 `/storage/Users/currentUser/Desktop/lan workspace/bullet3-3.25-evidence/logs/`（两处内容一致）。
> `12_ctest_insrc_run.log`（CTest 全量）、`14_gtest_*.log`（逐二进制 gtest 明细）、`15_shm_syscall_probe.log`（shm 探针）、`16_test_package_dryrun.log`、`18_test_package_conan_built.log`

## 三、遇到的问题与解决方案

| # | 现象（首个错误） | 根因 | 修复/绕行 | 重新验证 |
|---|---|---|---|---|
| 1 | `CMake Error: Compatibility with CMake < 3.5 has been removed`（CMake 4.1.2） | 上游 `cmake_minimum_required(VERSION 2.4.3)` | 补丁 `0001-CMakeLists.txt.patch` 提升至 3.5（等价 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`） | 配置 `rc=0` |
| 2 | `Could NOT find OpenGL` + `CMake 不认识 HarmonyOS 平台` | CMake 无 HarmonyOS platform module（E092） | 配方 `generate()` 覆写 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`；OpenGL 探测非致命（GLEW/GL 仅 demo 面） | `conan create rc=0` |
| 3 | `ld.lld: error: unable to find library -lBussIK`（`Test_PhysicsClientServer` 链接） | 上游不一致：`test/SharedMemory/CMakeLists.txt` 无条件链接 `BussIK`，但该 CMake 目标只在 `examples/CMakeLists.txt`（`BUILD_BULLET2_DEMOS=ON`）下定义 | 上游测试构建面加 `-DBUILD_BULLET2_DEMOS=ON`，只 `ninja Test_PhysicsClientServer`（不构建 GUI demo 目标） | 链接成功，测试运行 |
| 4 | `InvDynCompare.bulletUrdfR2D2` 断言 `findResourcePath(kUrdfFile)` 失败 | `b3FileUtils::findFile` 按 **cwd 相对路径** 搜索 `./data/…../../../../data/`；构建目录在源码树外时找不到 `<src>/data/r2d2.urdf` | 把构建目录放到**源码树内**（`build3-ohc/`，与上游 CI `build3/` 同布局） | 用例转为 PASS |
| 5 | `BulletPhysicsClientServerTest.LoopBackSharedMemory` → `SIGSYS`（`rc=159`） | OHOS 拦截 System V 共享内存 syscall（`shmget`）；最小探针复现 | **平台限制**，无源码级绕行；记录为已知限制（K004），不改上游代码 | 记录：1/15 失败 |
| 6 | `examples/ThirdPartyLibs/clsocket/src/StatTimer.h:90: error: unknown type name 'uint32'`（`BulletRoboticsGUI`） | clsocket `Host.h` 的 `uint32` typedef 仅在 `_LINUX/_DARWIN/_BSD`/`WIN32` 下定义，OHOS 皆无 | 该面属 `BUILD_EXTRAS=ON` 的 GUI/网络 demo，**配方已关闭**；不为 demo 面打补丁 | 交付面不受影响（`conan create rc=0`） |

## 四、test_package（消费者视角）

`test_package/test.cpp` 重写为 7 个用例（此前仅 1 个断言），全部实质调用发布物 API：

| 用例 | 覆盖 | 鸿蒙特有 |
|---|---|---|
| `physics_rigidbody_fall` | 刚体落地仿真（BulletDynamics/Collision/LinearMath） | |
| `collision_contact_detection` | 离散碰撞检测 + 接触流形 | |
| `serialization_default_serializer` | `btDefaultSerializer` 世界序列化 | |
| `task_scheduler_parallel_for_api` | `btITaskScheduler` + `btParallelFor`（本包 `BT_THREADSAFE=0`，顺序回退） | |
| `softbody_rope_simulation` | `btSoftBodyHelpers::CreateRope` + 步进（BulletSoftBody） | |
| `ohos_platform_abi` | `__OHOS__` 宏 + `__aarch64__` + 64 位 ABI + `sizeof(btScalar)==4` | ✅ |
| `ohos_precision_contract` | 包为单精度（`BT_USE_DOUBLE_PRECISION` 未定义）+ OHOS 走通用回退平台分支 | ✅ |

实测：`total=7 passed=7 failed=0 skipped=0`（`reports/test-report.md`）。

## 五、约束与已知限制

1. **包名 `bullet3`（本次交付）**：制品仓既有的 `bullet/3.25`、`bullet/3.25.1` 是同一上游（Bullet Physics SDK）在旧命名下的**已发布包**，本次不改动它们；`bullet3/3.25` 在制品仓不存在（`conan download bullet3/3.25 -r=ohpcd --only-recipe` → 未找到），属**首次发布**，因此不存在 R37/L0j 同版本 revision 冲突。目录名 / `conanfile.name` / 分支名三者一致（`archives/b/bullet3/3.25` ↔ `name = "bullet3"` ↔ `feat/bullet3-3.25`），满足 L0m-4 与 L0n。
2. **交付面 `BUILD_UNIT_TESTS=OFF`**：上游套件以**独立构建面实测**（见第二节），使 `conan create` 交付面与已验证产物一致、构建更快；如需 CI 内跑上游 ctest，可改为 `BUILD_UNIT_TESTS=ON` + `cmake.test()`（代价是 CI 构建时间增加）。
3. **单精度**（`btScalar=float`）：需 `double`（`BT_USE_DOUBLE_PRECISION`）的消费方请用既有 `bullet/3.25.1`。
4. **OHOS 无 System V 共享内存**（K004）：依赖 `b3ConnectPhysicsLoopback`/共享内存传输的用法在 OHOS 上不可用；`b3ConnectPhysicsDirect`（in-process）可用。
5. **`patches/0001` 为唯一补丁**：仅提升 `cmake_minimum_required`，不含平台宏（符合 R8）。

## 六、依赖
无第三方依赖（`requirements()` 为空；上游 `CMakeLists.txt` 无强制第三方 `find_package`）。系统库：pthread / libdl / libc++ 由 OHOS 工具链提供。

---
**核验日期**: 2026-09-25
**配方交付面状态**: built（`conan create` rc=0 + test_package 7/7 + conan-verify 全门禁 PASS + W3 本地 CI PASS；未上传制品，停在远端写操作前）
---

**编译结束**: 2026-09-25 17:35
**最终状态**: built

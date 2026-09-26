# bullet3 3.25 — 测试报告（HarmonyOS PC aarch64）

- 日期：2026-09-25
- 平台：HarmonyOS PC aarch64（`os=OHOS` / `os.version=6.0` / `arch=armv8` / clang 15.0.4 / libc++ / cppstd 17 / Release）
- 源码：`bullet3` tag `3.25`，tarball sha256 `c45afb6399e3f68036ddb641c6bf6f552bf332d5ab6be62f7e6c54eda05ceb77`（与 `conandata.yml` 逐字一致）
- 证据目录（本机）：`/storage/Users/currentUser/Desktop/lan workspace/bullet3-3.25-evidence/logs/`

---

## 一、A 面：上游官方测试（CTest / gtest）

### 1.1 测试入口清点（清点证据）

```bash
$ grep -rn "ADD_TEST\|add_test" test/ | grep -v gtest-1.7.0
test/BulletDynamics/CMakeLists.txt:19:            ADD_TEST(Test_btKinematicCharacterController_PASS Test_btKinematicCharacterController)
test/BulletDynamics/pendulum/CMakeLists.txt:25:  ADD_TEST(Test_BulletDynamics_PASS Test_BulletDynamics)
test/InverseDynamics/CMakeLists.txt:60:          ADD_TEST(Test_DynamicsABA_bulletVSrbdl_PASS Test_DynamicsABA_bulletVSrbdl)   ← 门控 BULLET_BUILD_RBDL_COMPARE_TEST（需外部 RBDL，默认不注册）
test/InverseDynamics/CMakeLists.txt:94:          ADD_TEST(Test_BulletInverseDynamicsJacobian_PASS Test_BulletInverseDynamicsJacobian)
test/InverseDynamics/CMakeLists.txt:159:         ADD_TEST(Test_BulletInverseForwardDynamics_PASS Test_BulletInverseForwardDynamics)
test/InverseDynamics/CMakeLists.txt:191:         ADD_TEST(Test_BulletInverseDynamics_PASS Test_BulletInverseDynamics)
test/SharedMemory/CMakeLists.txt:100:           ADD_TEST(Test_PhysicsClientServer_PASS Test_PhysicsClientServer)
test/collision/CMakeLists.txt:37:               ADD_TEST(Test_Collision_PASS Test_Collision)
```

### 1.2 构建面（覆盖全部上游用例，避免漏测）

```bash
$ cmake -S <src> -B <src>/build3-ohc -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
    -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DBUILD_UNIT_TESTS=ON -DBUILD_BULLET3=ON -DBUILD_EXTRAS=ON -DBUILD_BULLET2_DEMOS=ON \
    -DBUILD_PYBULLET=OFF -DBUILD_CPU_DEMOS=OFF -DBUILD_ENET=OFF -DBUILD_CLSOCKET=OFF \
    -DUSE_OPENVR=OFF -DUSE_GRAPHICAL_BENCHMARK=OFF -DENABLE_VHACD=OFF -DINSTALL_LIBS=ON
rc=0                                    # 日志: 10_inSrc_configure.log

$ ctest -N
Total Tests: 7                          # 日志: 04_ctest_list.log

$ ninja -C <src>/build3-ohc Test_Collision Test_btKinematicCharacterController Test_BulletDynamics \
      Test_BulletInverseDynamics Test_BulletInverseDynamicsJacobian Test_BulletInverseForwardDynamics \
      Test_PhysicsClientServer
rc=0  errors=0                          # 日志: 11_inSrc_build_tests.log
```

> 构建目录置于**源码树内**（`build3-ohc/`，对应上游 CI 的 `build3/`）：上游测试用 cwd 相对路径查找
> `data/`（`b3FileUtils::findFile`：`./`、`./data/`、`../data/` … `../../../../data/`），
> 树外构建目录会导致 `InvDynCompare.bulletUrdfR2D2` 找不到 `data/r2d2.urdf` 而误报失败。

### 1.3 测试命令与总结果

```bash
$ cd <src>/build3-ohc && ctest --output-on-failure -j1
86% tests passed, 1 tests failed out of 7
Total Test time (real) =   0.86 sec
The following tests FAILED:
          4 - Test_PhysicsClientServer_PASS (SIGSYS)
rc=8                                    # 日志: 12_ctest_insrc_run.log
```

| 指标 | 数值 |
|---|---|
| CTest 注册用例总数 | **7** |
| 通过 | **6** |
| 失败 | **1** |
| 跳过 | **0** |
| （上游门控未注册） | `Test_DynamicsABA_bulletVSrbdl_PASS`（需外部 RBDL） |
| gtest 内部用例总数 | **15** |
| gtest 通过 | **14** |
| gtest 失败 | **1** |

### 1.4 逐用例明细（每项名称 / 结果 / 日志）

| CTest # | CTest 用例 | gtest 用例名 | 结果 | 日志 |
|---|---|---|---|---|
| 1 | `Test_BulletInverseDynamicsJacobian_PASS` | `InvDynJacobians.JacDotJacU` | PASS | `14_gtest_Test_BulletInverseDynamicsJacobian.log` |
| 1 | 〃 | `InvDynJacobians.Jacobians` | PASS | 〃 |
| 1 | 〃 | `InvDynJacobians.VelocitiesFromJacobians` | PASS | 〃 |
| 2 | `Test_BulletInverseForwardDynamics_PASS` | `InvDynCompare.bulletUrdfR2D2` | PASS | `14_gtest_Test_BulletInverseForwardDynamics.log` |
| 3 | `Test_BulletInverseDynamics_PASS` | `InvDynKinematicsDifferentiation.errorAbsolute` | PASS | `14_gtest_Test_BulletInverseDynamics.log` |
| 3 | 〃 | `InvDynKinematicsDifferentiation.errorOrder` | PASS | 〃 |
| 4 | `Test_PhysicsClientServer_PASS` | `BulletPhysicsClientServerTest.DirectConnection` | PASS (344 ms) | `14_gtest_Test_PhysicsClientServer.log` |
| 4 | 〃 | `BulletPhysicsClientServerTest.LoopBackSharedMemory` | **FAIL — SIGSYS (rc=159)** | 〃 / `13_loopback_direct.log` |
| 5 | `Test_Collision_PASS` | `BulletCollisionTest.GjkMPRSphereSphereDistance` | PASS | `14_gtest_Test_Collision.log` |
| 5 | 〃 | `BulletCollisionTest.GjkEpaSphereSphereDistance` | PASS | 〃 |
| 5 | 〃 | `BulletCollisionTest.GjkEpaSphereSphereRadiusNotFullMarginDistance` | PASS | 〃 |
| 5 | 〃 | `BulletCollisionTest.AnalyticSphereSphereDistance` | PASS | 〃 |
| 5 | 〃 | `BulletCollisionTest.Heightfield_ProcessAllTriangles_FiltersByUpAxis` | PASS | 〃 |
| 6 | `Test_btKinematicCharacterController_PASS` | `BulletDynamics.KinematicCharacterController` | PASS | `14_gtest_Test_btKinematicCharacterController.log` |
| 7 | `Test_BulletDynamics_PASS` | `BulletDynamicsTest.pendulum` | PASS | `14_gtest_Test_BulletDynamics.log` |

### 1.5 唯一失败的根因（平台限制，已用最小探针复现）

```bash
$ cd <src>/build3-ohc/test/SharedMemory && ./Test_PhysicsClientServer --gtest_filter='*LoopBackSharedMemory*'
[ RUN      ] BulletPhysicsClientServerTest.LoopBackSharedMemory
$ echo $?
159                                     # 128 + 31 = SIGSYS ；日志: 13_loopback_direct.log
```

最小复现（不依赖 bullet）：

```c
int main(void){ int id = shmget(IPC_PRIVATE, 4096, IPC_CREAT|0666); printf("shmget -> %d\n", id);
                void *p = shmat(id, 0, 0); printf("shmat -> %p\n", p); return 0; }
$ /data/service/hnp/bin/clang shm_probe.c -o shm_probe && ./shm_probe
$ echo $?
159                                     # 无任何输出即被 SIGSYS 杀死；日志: 15_shm_syscall_probe.log
```

结论：**OHOS 拦截 System V 共享内存 syscall（`shmget`）**。bullet 的 `b3ConnectPhysicsLoopback` 走
`examples/SharedMemory/PosixSharedMemory.cpp`（`shmget`/`shmat`）→ 该用例在 OHOS 上无法通过；
同套件中的 `DirectConnection`（in-process 后端）通过。属平台限制，无源码级绕行，未打补丁。

---

## 二、B 面：`test_package`（消费者视角，`conan create` 内建）

```bash
$ conan create archives/b/bullet3/3.25 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
bullet3/3.25: Package '4b977264131a1c74e82bd6bb51b63cc9aadc4cfa' built
bullet3/3.25: Package '4b977264131a1c74e82bd6bb51b63cc9aadc4cfa' created
======== Launching test_package ========
1/1 Test #1: test_bullet ......................   Passed    0.06 sec
100% tests passed, 0 tests failed out of 1
rc=0                                    # 日志: 36_conan_create_bullet3_v2.log
```

`test_package/test_bullet` 独立运行输出（对 conan 构建产物）：

```
==== bullet3/3.25 test_package (consumer view) ====
[ OK ] physics_rigidbody_fall             sphere rest y=1.0000 (expect ~1.0, radius=1, ground y=0)
[ OK ] collision_contact_detection        manifolds=1 contactPoints=1 (expect >=1 contact)
[ OK ] serialization_default_serializer   serialized 14572 bytes (buffer=non-null)
[ OK ] task_scheduler_parallel_for_api    scheduler='Sequential' numThreads=1 BT_THREADSAFE=0 wrong=0/4096
[ OK ] softbody_rope_simulation           rope nodes=12 fixed-end y=10.0000 free-end y=-0.2117 (free end must hang below fixed end)
[ OK ] ohos_platform_abi                  __OHOS__=1 __aarch64__=1 sizeof(void*)=8 sizeof(btScalar)=4
[ OK ] ohos_precision_contract            BT_USE_DOUBLE_PRECISION=0 (package=float) genericPlatformFallback=1
---- total=7 passed=7 failed=0 skipped=0 ----
rc=0                                    # 日志: 37_test_package_bullet3_v2.log
```

| 指标 | 数值 |
|---|---|
| 用例总数 | 7 |
| 通过 | 7 |
| 失败 | 0 |
| 跳过 | 0 |
| 其中鸿蒙特有用例 | **2**（`ohos_platform_abi`、`ohos_precision_contract`） |

> 说明：`test_package` 不能替代上游测试统计；上游结果见第一、二节（A 面）。

---

## 三、原始日志索引

| 日志 | 内容 |
|---|---|
| `01_patch_dryrun.log` / `02_patch_apply.log` | 补丁 `0001` 的 dry-run 与应用（rc=0） |
| `03_cmake_max_configure.log` | 最大构建面 configure（rc=0，7 个 CTest） |
| `04_ctest_list.log` | `ctest -N` → Total Tests: 7 |
| `05_build_max_all.log` | 全量构建（首个错误在此：clsocket `unknown type name 'uint32'`，属 GUI demo 面） |
| `06_build_tests.log` | 7 个测试目标构建（首个 FAILED：`-lBussIK` 链接） |
| `07_reconfigure_demos.log` / `08_build_test_physicsclientserver.log` | 加入 `BUILD_BULLET2_DEMOS=ON` 后 BussIK 目标可见，链接成功 |
| `09_ctest_run.log` | 树外构建目录首次 ctest（3/7 → 定位数据路径根因） |
| `10_inSrc_configure.log` / `11_inSrc_build_tests.log` / `12_ctest_insrc_run.log` | 源码树内构建 + 正式 ctest（6/7） |
| `13_loopback_direct.log` / `15_shm_syscall_probe.log` | SIGSYS 定位与最小探针复现 |
| `14_gtest_*.log`（7 个） | 逐二进制 gtest 用例明细 |
| `37_test_package_bullet3_v2.log` | test_package 7/7 |
| `36_conan_create_bullet3_v2.log` | `conan create` 全流程（源码缓存命中 → 编译 → 打包 → test_package） |

---

**结论**：配方交付面（`conan create` + `test_package`）全部通过；上游套件 7 项中 6 项通过，
唯一失败为 OHOS 平台拦截 System V 共享内存所致，有最小探针复现证据。

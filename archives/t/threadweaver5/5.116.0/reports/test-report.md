# threadweaver5 5.116.0 测试报告（HarmonyOS PC / arm64）

- 日期: 2026-10-06
- 环境: OHOS PC (arm64, OHOS 6.0, clang 15, libc++), Conan 2.29.1 (OHOS 适配版),
  profile `ohos-aarch64`（host==build 原生轨）
- 源码: threadweaver-5.116.0.tar.xz
  sha256 `9723dc652df9a2df8b6b9909af5bf0de3b3eb3aaed260a6419df2b0ddbe8eae0`
  （本地实测，与官方 .sha256 sidecar 一致）
- 构建命令: `conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2`

## 上游测试（rule4 口径，ctest 注册数 N=7）

上游 `autotests/CMakeLists.txt` 注册 7 个 `ecm_add_test` 目标；`benchmarks/`
的 `add_test` 在上游被注释（构建但不注册）；`examples/` 为 demo 程序（无测试
注册）——均不计入 N。

```
100% tests passed, 0 tests failed out of 7
Total Test time (real) =   1.40 sec
```

| # | ctest 名 | 结果 | 耗时 |
|---|----------|------|------|
| 1 | ThreadWeaverJobTests | Passed | 0.71s |
| 2 | ThreadWeaverSequencesTests | Passed | 0.06s |
| 3 | ThreadWeaverQueueTests | Passed | 0.28s |
| 4 | ThreadWeaverDeleteTest | Passed | 0.14s |
| 5 | ThreadWeaverLifecycleTest | Passed | 0.05s |
| 6 | ThreadWeaverShutdownOnQApplicationQuitTest | Passed | 0.05s |
| 7 | ThreadWeaverQueueFactoryTest | Passed | 0.07s |

**通过率 7/7（100%），无豁免项。** 全部测试为无头 QCoreApplication/QTest
事件循环（库仅链 QtCore），无 GUI、无 D-Bus、无外部 fixture，OHOS PC runner
原生可跑。

## test_package（消费者验证，16/16 断言）

```
SUMMARY: 16 passed, 0 failed
```

覆盖的真实公开 API（R34）:
1. 全局 `stream()` 按序入队执行 Job + `Queue::instance()->finish()` / `isEmpty()`
2. `Sequence` 顺序执行与失败中止（失败作业后续不执行，结果 "abc" 非 "abcde"）
3. `Collection` 全量执行（顺序无关）
4. `make_job()` lambda + `enqueue()`（JobPointer 特化路径）
5. `QObjectDecorator::started` / `done` 信号各发射一次
6. `ResourceRestrictionPolicy(1)` 并发上限下双作业完成
7. Job 状态机 `Status_New` → `Status_Success` / `Status_Failed`

HarmonyOS 特有断言（R53）:
- `libKF5ThreadWeaver.so` 携带无版本 `DT_SONAME`（CMAKE_PLATFORM_NO_VERSIONED_SONAME）
- 携带 `DT_RUNPATH`（E537: CMAKE_BUILD_WITH_INSTALL_RPATH=ON，安装后 ELF 未被改写）
- 包内 ELF 携带 `.codesign` 段（binary-sign-tool 安装后重签名，OHOS 加载器要求）

```
info - libKF5ThreadWeaver.so = <pkg>/lib/libKF5ThreadWeaver.so
info - DT_SONAME = libKF5ThreadWeaver.so (RUNPATH=1 RPATH=0)
```

## 干净环境重跑（防"本地过 CI 挂"）

`conan remove "threadweaver5/*" -c` 清除缓存（recipe+全部二进制）后全量重建:
上游 7/7（100%）+ test_package 16/16 + `Signed 1 OHOS package ELF file(s)`
全部复现，RC=0。

## 打包产物

| 文件 | 说明 |
|------|------|
| `lib/libKF5ThreadWeaver.so` | 主库（无版本 DT_SONAME + RUNPATH + .codesign） |
| `include/KF5/ThreadWeaver/**` | 公开头（lowercase + CamelCase） |
| `lib/cmake/KF5ThreadWeaver/*` | CMake 包配置（KF5::ThreadWeaver） |
| `mkspecs/modules/qt_ThreadWeaver.pri` | qmake .pri |

纯库包（无 `bin/`），不建 `commands.json`（R38/PF8）。

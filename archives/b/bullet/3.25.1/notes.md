# bullet 3.25.1 适配笔记

## 背景(为什么需要 3.25.1 双精度变体)

适配 OpenMW 0.51.0 时,其 `CMakeLists.txt:445` 强制要求 Bullet 双精度
(`HAS_DOUBLE_PRECISION_BULLET`,即 `btScalar = double`,宏 `BT_USE_DOUBLE_PRECISION`)。
但 ohpcd 上 `bullet/3.25` 为单精度构建,无 double 变体,配方也未暴露精度开关。

按既定方案,库名仍为 `bullet`,新增 `precision` 选项,双精度以本地版本
`bullet/3.25.1` 发布(与已发布的单精度 3.25 区分)。

## 双精度机制

`btScalar.h` 通过 `#ifdef BT_USE_DOUBLE_PRECISION` 在 `double`/`float` 之间切换
`btScalar`。这是**编译期宏**,不是 CMake option。因此:
- 编译库时需注入 `-DBT_USE_DOUBLE_PRECISION`(本配方在 `generate()` 中通过
  `CMAKE_CXX_FLAGS` / `CMAKE_C_FLAGS` 注入)。
- 消费方(如 OpenMW、test_package)也必须用同一宏构建,否则 `btScalar` 定义不一致,
  会造成 ABI 不匹配。故 `package_info()` 在 `precision=double` 时回传
  `cpp_info.defines = ["BT_USE_DOUBLE_PRECISION"]`。

## 编译环境
- 构建系统: cmake
- 编译器: clang/clang++ 15.0.4
- 状态: local (本地适配验证,未提交)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载失败、gh-proxy 镜像被拒 | 上游 URL 不可达 | conandata 改用官方 codeload 源(与上游 3.25 同 tar,sha256 一致 `c45afb…`) |
| 2 | `get()` 报 BadZipFile | codeload URL 不以 `.tar.gz` 结尾,conan 无法识别包格式 | conandata `sources` 增加 `filename: bullet3-3.25.tar.gz` |
| 3 | CMake 配置失败 | CMakeLists.txt `cmake_minimum_required(2.4.3)` 与 CMake 4.x 不兼容 | 复用补丁 0001(提升至 3.5) |
| 4 | CMake 不认识 HarmonyOS | CMake 无 HarmonyOS platform module (E092) | `generate()` 设 CMAKE_SYSTEM_NAME=Linux, CMAKE_SYSTEM_PROCESSOR=aarch64 |
| 5 | `settings.os.version value not defined` | 默认 profile 只有 `os=OHOS` 未带 `os.version` | 用仓库标准 profile(见下),其含 `os.version=6.0` |
| 6 | `clang: invalid library name '-stdlib=libstdc++'` | 默认 profile 的 `compiler.libcxx=libstdc++11` 是错的;OHOS clang 用的是 libc++ | 改用 `compiler.libcxx=libc++`(CI profile 即如此) |

## 源码修改
- `patches/0001-CMakeLists.txt.patch`: 与 3.25 相同,提升 `cmake_minimum_required`。

## 依赖版本
无依赖。

## 验证(本地,真机 aarch64)

用仓库标准 OHOS profile(`ci/conan/profiles/ohos-aarch64`:os=OHOS, os.version=6.0,
arch=armv8, clang 15, libcxx=libc++, cppstd=17, build_type=Release)构建:

```bash
conan create . -pr:h=/path/to/build_in_harmonyos5/ci/conan/profiles/ohos-aarch64 \
                -pr:b=/path/to/build_in_harmonyos5/ci/conan/profiles/ohos-aarch64 \
                -o '&:precision=double'
```

三重确认:

1. **库为双精度编译**:6 个库目标(Collision/Dynamics/SoftBody/InverseDynamics/
   LinearMath/Bullet3Common)的 `flags.make` 均含 `CXX_FLAGS = -DBT_USE_DOUBLE_PRECISION`。
2. **消费侧同口径**:根配方 `package_info()` 在 precision=double 时回传
   `cpp_info.defines = ["BT_USE_DOUBLE_PRECISION"]`,经 CMakeDeps 生成
   `bullet_COMPILE_DEFINITIONS_RELEASE "BT_USE_DOUBLE_PRECISION"`,test_package 的
   test_bullet `CXX_DEFINES = -DBT_USE_DOUBLE_PRECISION`(btScalar 一致,无 ABI 错配)。
3. **测试通过**:test_bullet 真机运行 `100% tests passed, 0 tests failed`(物理模拟
   球体落地 y≈1.0)。

> 注意:在 HarmonyOS 真机上构建,`conan create` 会原生编译并运行 aarch64 二进制。
> 若在 CI 的泛化 profile 下缺 `os.version`,需显式带 `-s:h os.version=6.0`。

---
**编译结束**: (本地验证)
**最终状态**: local

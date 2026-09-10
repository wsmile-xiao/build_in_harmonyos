# zxing-cpp 2.3.0 适配笔记

## 当前基线和源码

- 任务基线：`c84a9cdc2e54d9ba49d350dab134a5da052743a1`，branch `feat/zxing-cpp-2.3.0`。
- 官方源码归档：`zxing-cpp` v2.3.0，SHA-256：`64e4139103fdbc57752698ee15b5f0b0f7af9a0331ecbdc492047e0772c417ba`。
- GitCode source fetch 曾连续失败；AtomGit 公共上游用于设备同步，且设备已成功 fetch 精确基线 SHA。

## 构建选择

上游 `core/CMakeLists.txt` 生成目标 `ZXing`，安装 `lib/libZXing.a`、`include/ZXing` 和 `lib/cmake/ZXing`。Conan 配方映射为 `ZXing::ZXing`，默认 `shared=False`。上游 `zxing.pc` 原本把绝对安装前缀写入 `libdir`/`includedir`；配方在 package 阶段改写为 `${pcfiledir}` 相对路径，保证 Conan package 可重定位。

设备的默认 Conan host profile 实测为 `compiler.cppstd=gnu14`，但上游 target 的 `target_compile_features` 要求 C++17。配方通过 `CMakeToolchain` 将实际编译标准提升到 C++17；没有把低于要求的 profile 直接判为无效，package ID 仍保留 profile 的原有维度。消费者测试也显式使用 C++17。

上游 `ZXING_C_API=ON` 会无条件进入 `wrappers/c/CMakeLists.txt` 并通过 `zxing_add_package_stb()` 获取 stb。设备首次配置因此因 FetchContent 子仓库的 Git ownership 检查失败；该入口不是核心 C++ 包的必需功能。正式包配置关闭 `ZXING_C_API`、examples、Python wrapper 和测试目标，仅构建核心 C++ library。

## 已完成的设备原生验证

- 设备：HarmonyOS aarch64，clang 15.0.4，CMake 4.1.2，Conan 2.29.1，Python 3.12.8。
- 核心 CMake 配置、构建、安装：通过；静态库和公共头文件均生成。
- 上游 UnitTest：开启 `ZXING_UNIT_TESTS=ON`，GoogleTest 从源码获取到任务私有目录；`[==========] Running 283 tests from 57 test suites`，`[  PASSED  ] 283 tests`，退出码 0。
- 核心构建日志中的两类 signedness warning 来自上游 `oned` writer 源码，不影响构建或测试；未改动上游源文件。

## Conan/W3 设备验证

- 采信轮按精确 reference `zxing-cpp/2.3.0@ohpcd/stable` 清理 Conan recipe、package 和残留 `p/` 分片；清理前没有其他 zxing-cpp 目标，并且设备验证必须绑定包含本节 pkg-config 修复的最终提交 SHA。
- `conan-verify` 使用 `ci/conan/profiles/ohos-aarch64`；中间候选 SHA `120bd8c9aca36fdbe2c075d5747cee170f3ae405` 已确认 G0/G1/G2/G3 的构建链路，G2 日志确认不是缓存命中：重新下载源码、运行 CMake configure/build、构建 `libZXing.a` 并运行 test_package。该中间轮不作为最终采信证据，最终轮需在最终 SHA 上重跑。
- 设备 package reference 的稳定字段为 recipe revision `3acb0726ddf1ee3b3ff66a3edf0e6e52` 和 package ID `21b17f8b2bc0e9511e276e3d57a23893067cefe5`；每轮临时 cache 目录和 package revision 详见对应的 task-private supplement，避免把一次性路径当作可复用基线。
- G4 人工补充核验：包内 36 个文件，包含 1 个 `lib/libZXing.a`、27 个公共头、4 个 CMake 配置文件、1 个 pkg-config 文件和 LICENSE；没有 `.so` 或可执行文件。
- L2 人工补充核验：test_package CMake consumer 编译链接成功，CTest `1/1` 通过；随后直接运行 `./test_zxing_cpp`，6/6 断言通过并返回 0。
- L4 人工补充核验：包只含静态 archive 和文本/头文件，没有适用 NX/PIE/RELRO 的 ELF 可执行或动态库；不把 N/A 写成动态安全结果。
- L5：这是 zxing-cpp 首个本地 package，清理前不存在可比较的旧 package；当前 library 与 CMake/pkg-config/LICENSE SHA-256 已记录在任务私有证据及 `reports/conan-verify-supplement.md`。
- 当前 `ohc-run.py conan-verify` 报告仍将 G4/L2/L4/L5 显示为“无法找到 package ID/跳过”，虽 G2 和 test_package 已真实执行；已按工作流留人工 supplement，不能把工具的 skip 行当作完整门禁证据。

## 待完成

- W4 独立审计、PR、CI 和 Review 仍须绑定最终提交 SHA 后执行。

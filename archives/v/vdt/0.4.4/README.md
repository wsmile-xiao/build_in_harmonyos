# vdt

**Vectorised math** 快速数学库（CERN 出品）。提供双/单精度快速近似实现的数学函数
（exp/log/sqrt/sin/cos/tan/atan 等），支持标量 `T(T)` 与数组 `void(unsigned,T*,T*)`
两种签名，可在自动向量化循环中使用，无第三方依赖。

## HarmonyOS PC (aarch64) 适配要点

- 版本：0.4.4（官方 tag v0.4.4，SHA-256 `8b1664b45ec82042152f89d171dd962aea9bb35ac53c8eebb35df1cb9c34e498`）
- 构建系统：CMake（configure 阶段需要 Python 运行 `src/signatures_generator.py` 生成 `src/vdtMath_signatures.cc`）
- 平台：aarch64 开启 NEON 向量路径；x86 专属 SSE/AVX/FMA 关闭（aarch64 上 `-msse` 为未知选项）
- 兼容：vdt 声明 `cmake_minimum_required 3.2`，CMake 4.x 需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
- 产物：`libvdt.so` + `include/vdt/*.h`（纯库，无 CLI，不需要 commands.json）
- 测试：上游 12 个独立单元测试（`progs/units/*_test.cpp`）随 `-DDIAG=ON` 构建，
  由 `conanfile.py` 的 `build()` 真实执行；test_package 含消费者验证
  （`consumer_probe`）与鸿蒙专项测试（`ohos_special_probe`）

## 与 0.4.6 / archives/c/cern 的关系

- `archives/v/vdt/0.4.6`（任务 #13676）与 `archives/c/cern/0.4.6` 是同一上游
  （dpiparo/vdt v0.4.6）的不同包名/版本适配；本目录为上游 **v0.4.4** tag，
  与 0.4.6 的源码差异仅顶层 `CMakeLists.txt` 一行（`VECT_OPT`：`-Ofast` → `-O3`）。
- 本目录按任务 #11636 绑定的库名与版本正式适配：`vdt` / `0.4.4`。

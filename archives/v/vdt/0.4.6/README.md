# vdt

**Vectorised math** 快速数学库（CERN 出品）。提供双/单精度快速近似实现的数学函数
（exp/log/sqrt/sin/cos/tan/atan 等），支持标量 `T(T)` 与数组 `void(unsigned,T*,T*)`
两种签名，可在自动向量化循环中使用，无第三方依赖。

## HarmonyOS PC (aarch64) 适配要点

- 版本：0.4.6（官方 tag v0.4.6，SHA-256 `1820feae446780763ec8bbb60a0dbcf3ae1ee548bdd01415b1fb905fd4f90c54`）
- 构建系统：CMake（configure 阶段需要 Python 运行 `signatures_generator.py` 生成签名代码）
- 平台：aarch64 开启 NEON 向量路径；x86 专属 SSE/AVX/FMA 关闭（aarch64 上 `-msse` 为未知选项）
- 兼容：vdt 声明 `cmake_minimum_required 3.2`，CMake 4.x 需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
- 产物：`libvdt.so` + `include/vdt/*.h`（纯库，无 CLI，不需要 commands.json）
- 测试：上游 12 个独立单元测试（progs/units/*_test.cpp）全量通过；
  test_package 含消费者验证（consumer_probe）与鸿蒙专项测试（ohos_special_probe）

## 与 archives/c/cern/0.4.6 的关系

仓库中 `archives/c/cern/0.4.6` 适配同一上游（dpiparo/vdt v0.4.6，同一 SHA-256），
包名按当时任务取 `cern`（Arch Linux 打包名 cern-vdt）。本目录按任务绑定库名 `vdt`
正式发布包名 `vdt`。两包同源同版本，本包为 cern 包的正式包名版本。
# OpenFAST

OpenFAST 是美国国家可再生能源实验室（NREL）支持的开放式风轮机整机仿真软件，用于陆上、固定底式与
浮式海上风电机组的非线性时域动态响应分析。它耦合气动（AeroDyn）、水动（HydroDyn）、伺服
（ServoDyn）、结构弹性（ElastoDyn/BeamDyn）等模块，支持负载分析、系统线性化与控制器设计。

- 上游仓库：https://github.com/OpenFAST/openfast
- 文档：https://openfast.readthedocs.io/
- 许可证：Apache-2.0

## HarmonyOS PC 适配

- 版本：5.0.0（tag v5.0.0，commit 2895884d2be01862173c88d70f86b358d2f1a50a）
- 构建系统：CMake，设备原生（os=OHOS arch=armv8）
- Fortran 工具链：`tool_requires flang-ohos/20.1.0`（LLVM Flang 20.1.0）
- BLAS/LAPACK：`openblas/0.3.34`
- 可选模块：全部保持上游默认 OFF，最小构建（openfast 可执行 + OpenFAST 库）
- 双精度：DOUBLE_PRECISION=ON（上游默认）

详见 `5.0.0/notes.md`。

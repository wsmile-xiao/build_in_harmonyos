# indicators

indicators — Activity Indicators for Modern C++：线程安全的进度条、进度旋转器与活动指示器，
single-header 与多头文件两种分发方式（`single_include/indicators/indicators.hpp` 与 `include/indicators/*.hpp`）。

- 官方仓库：https://github.com/p-ranav/indicators （默认分支 master）
- 许可证：MIT（主）+ BSD-3-Clause（内部携带的 termcolor 单头，见 LICENSE.termcolor）
- 适配版本：2.3.0（官方标签 `v2.3`，commit `26d39ad8fb438f5f50fb16427f554045d8431030`，2023-02-15 发布；
  官方 `CMakeLists.txt` 内 `project(indicators VERSION 2.3.0 ...)`，与任务版本 2.3.0 语义一致）
- 目录结构：`archives/i/indicators/2.3.0/`（conanfile.py + conandata.yml + test_package/ + manifest.yaml + notes.md）
# indicators 2.3.0 — 适配笔记

## 来源核验（R01 bootstrap）

- 官方仓库：https://github.com/p-ranav/indicators（GitHub 直连在本环境受限，经 gitcode
  镜像 https://gitcode.com/p-ranav/indicators 与官方 codeload 双源核验）
- 正式标签：`v2.3` → commit `26d39ad8fb438f5f50fb16427f554045d8431030`（"Bumped to version v2.3",
  2023-02-15T07:17:27-08:00），官方最新 release（2023-02-15T15:17:58Z）。
  标签全集 v1.0~v2.3，无 v2.3.0 独立标签；但官方 `CMakeLists.txt` 声明
  `project(indicators VERSION 2.3.0 ...)`，与本任务版本标识 2.3.0 语义一致 → 等价成立。
- 源码校验值：官方 v2.3 tarball SHA256 = `70da7a693ff7a6a283850ab6d62acf628eea17d386488af8918576d0760aef7b`
  （8970430 字节），与本机下载实测一致，且与 FreeBSD ports 归档
  （devel/indicators: Update 2.2 → 2.3, TIMESTAMP 1678439245）记载的 SHA256 逐字节一致。

## 技术要点

- header-only 库：`include/indicators/*.hpp`（16 个头）+ `single_include/indicators/indicators.hpp`（amalgamate 单头）。
- MIT（主 LICENSE）+ BSD-3-Clause（LICENSE.termcolor，携带的 termcolor 单头）。
- 上游自带 Conan 1.x 配方（`from conans import ...`）——按项目惯例 Conan 2.x 重写（见 conanfile.py）。
- CMake 安装产物：`include/indicators/*.hpp` + `indicatorsConfig.cmake`/`indicatorsConfigVersion.cmake`
  （export NAMESPACE `indicators::`）+ `indicators.pc`（pkgconfig）。
- 上游无独立 CTest 测试套件：`INDICATORS_DEMO`/`INDICATORS_SAMPLES` 默认 OFF，测试由
  test_package 消费者编译链接验证（首个 gap：全面上游验证需在后续阶段评估 demo/samples 编译）。

## Bootstrap 状态

- worktree：专用 `/storage/Users/currentUser/junshi_liu/worktrees/pc3-40-indicators-2.3.0`
- 分支：`feat/indicators-2.3.0`（从可审计 main `5292d3091f6c09c860a0071abb81229a481c656a` 创建）
- 待续：首轮 Adapt 本地验证（test_package 消费者编译 + 上游样例可编译性抽查），均在本 task_id 内完成；不 commit/push/PR。
---

**编译结束**: 2026-08-31 08:55
**最终状态**: built

# rocm-hipamd 5.7.1 适配笔记

## 编译环境
- 构建系统: header-only (无构建系统)
- 编译日期: 2026-09-02（初版）/ 2026-09-17（第 2 轮修订）
- 编译器: clang/clang++ 15
- 状态: built（PR 待合入，未 upload）

## 软件说明
ROCm HIP (Heterogeneous-Compute Interface for Portability) 5.7.1 版本。
此包为 header-only 包，提供 HIP 运行时 API 头文件、CMake 模块和辅助脚本。

源码来自 ROCm/HIP 仓库的 rocm-5.7.1 标签。
注意：在 ROCm 5.7.x 中，原 hipamd 仓库已合并到 HIP 仓库（此 tag 的 HIP 仓库
不含 hipamd/ 子目录与 CMakeLists.txt 构建系统，仅保留头文件、cmake 模块与
bin 辅助脚本；GPU 运行时库由 ROCm clr 仓库构建，不在本包范围内）。

## 包内容
- include/hip/*.h — HIP 运行时 API 头文件（23 个头文件）
- cmake/FindHIP.cmake + cmake/FindHIP/ — CMake 查找模块
- bin/ — 辅助脚本（hipcc_cmake_linker_helper、hipdemangleatp）
- hip-lang-config.cmake.in — CMake 配置模板（打包进 cmake/）
- VERSION — 版本信息文件
- licenses/LICENSE.txt — 上游 MIT 许可证

## 构建说明
此包为 header-only 包，无需编译。构建过程仅复制头文件和辅助文件到包目录。
实际 HIP 运行时库由 ROCm clr 仓库构建，不在本包范围内。

## 消费者使用说明
- 编译 HIP 主机侧代码时需定义 `__HIP_PLATFORM_AMD__=1`（HIP 上游平台守卫宏，
  library_types.h 等头文件缺省时 `#error`）
- `hip_runtime_api.h`、`driver_types.h` 等头文件传递依赖 `amd_detail/`（位于
  ROCm clr 仓库）与 `hip_version.h`（构建期生成），需配合后续 clr 运行时包使用
- FindHIP 模块位于 `${rocm-hipamd_ROOT}/cmake`，CMakeDeps 不会自动加入
  CMAKE_MODULE_PATH，需要时手动 `list(APPEND CMAKE_MODULE_PATH ...)`

## 上游测试清点（R51）
上游 `tests/` 目录存在，采用 HIT（HIP Integrated Tester）框架：
- `tests/src/` — 运行时 API / kernel / printf / ipc / p2p 等设备测试
  （22 个顶层子目录，递归共 42 个；test_common.cpp 公共入口）
- `tests/unit/` — 单元测试；`tests/hit/` — HIT 解析器
- 清点证据：`tar tzf rocm-5.7.1.tar.gz | grep '^hip-rocm-5.7.1/tests/'`

可运行性结论：**均不可在 OHOS PC 上运行**，具体技术原因：
1. 上游 README 要求先完成 HIP 运行时完整 cmake 构建+安装（`make build_tests`
   依赖已安装的 libamdhip64 运行时），该运行时由 ROCm clr 仓库构建，
   不在本 header-only 包范围内；
2. 测试主体为设备代码（HIT BUILD 行以 hipcc 编译 .cu/.cpp 设备内核），
   需要 AMD GPU 执行环境，OHOS PC 无 AMD GPU；
3. 本包 L1 测试改为覆盖包的实际内容：可独立编译头文件的编译+公共 API
   符号断言（宏/枚举/类型），并对包产物完整性（头文件/cmake 模块/bin 脚本/
   VERSION/许可证）做存在性校验。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | GitHub 下载超时 | 网络限制 | 使用 ghfast.top 镜像下载（本地），conandata 保持官方 URL |
| 2 | 构建系统检测错误 | 空的 configure 文件导致误判为 autotools | 手动改为 header-only 包 |
| 3 | 无 CMakeLists.txt | ROCm 5.7.x 中构建系统移至 clr 仓库 | 本包仅提供头文件和 CMake 模块 |
| 4 | AI 检视 P1：空壳测试 | test 仅 include 头文件即 return 0，未引用符号 | 重写测试：断言 hip_common.h 宏、library_types.h 枚举/类型（hipDataType 等）+ 包产物完整性校验（hip_runtime_api.h 等需 amd_detail 的头文件以存在性校验覆盖） |
| 5 | 分支混入无关提交 | 前序会话在任务分支误提交 ngspice notes 回退与 libquvi-scripts 变更 | 第 2 轮基于最新 main 重建分支，PR 仅含 rocm-hipamd/5.7.1（W2 原子性） |
| 6 | CI #38128 checkout-pr 失败 | Worker 下载 PR diff 网络超时（基础设施抖动） | 修复推送后评论 /rebuild 重触发 |

## 修订记录
- 2026-09-02 初版适配（8 文件）
- 2026-09-17 第 2 轮：测试加固（P1 闭环）、新增 LICENSE 打包、
  manifest 状态修正为 built（PR 未合入未 upload）、上游测试清点（R51）
---

**编译结束**: 2026-09-17 12:46
**最终状态**: built

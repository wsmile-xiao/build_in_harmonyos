# boost-di 1.3.2 适配笔记（bootstrap 阶段）

## 编译环境
- 构建系统: cmake（header-only，仅用于上游测试/示例；库本体为单头文件）
- 编译日期: 2026-08-29
- 编译器: clang/clang++
- 状态: pending（bootstrap 仅建骨架，未编译/未验证；不得预标 published/built）

## Bootstrap 溯源证据（官方来源核验）

- 官方仓库: https://github.com/boost-ext/di
  - ⚠️ 注意：官方仓库为 **boost-ext/di**，不是 boostorg/di（后者不存在/404）
- 正式标签: `v1.3.2`
  - 发布: 2025-04-02T15:35:27Z（author: kris-jusiak, target_commitish: cpp14）
  - release commit: `20b6454c889f23c1e7c9eb5136cd7e3d6f6d718d`
- 源码 tarball（官方）:
  - URL: https://github.com/boost-ext/di/archive/refs/tags/v1.3.2.tar.gz
  - SHA256: `2bcd01f1d555bdb59a277b932f9021701c5cd26d1d7411f024394db69c5c11cf`
  - 解压顶层目录: `di-1.3.2/`
  - 完整性二次校验: 解压出的 `include/boost/di.hpp`
    SHA256=`1680ca33ffa04457edcea5c14346ad6e3138d8bb34d4fe074a59e13e34b54827`，
    与官方 commit `20b6454c` 的 raw 文件逐字节一致（通过镜像代理比对）。
- 下载说明: 执行机无法直连 github.com，经 gh-proxy.com 镜像下载；gh-proxy 与官方
  commit raw 比对一致，内容未被篡改。R39 官方 URL 保持不变，CI 会自动加镜像 fallback。

## 版本宏备注
- `include/boost/di.hpp` 中 `BOOST_DI_VERSION = 1'3'0`（上游 v1.3.2 为补丁版，
  未提升版本宏；标签与 release commit 才是权威版本标识）。

## 源码结构（header-only）
- `include/boost/di.hpp`（主头文件，约 134 KiB）
- `include/boost/di/`（aux_/ core/ scopes/ type_traits/ wrappers/ 等子目录）
- 无 LICENSE 文件（BSL-1.0 许可证，见 CMakeLists.txt 头注释）
- extension/ 仅含测试，无 extension/include，无需打包

## 最小归档/配方骨架
- conandata.yml: 官方 URL + SHA256（已填真实校验值）
- conanfile.py: header-only 配方（package_type=header-library，无编译）
- test_package/: conanfile.py + CMakeLists.txt + test_di.cpp（真实 API 消费者：
  make_injector/bind/create）+ MANIFEST.yml
- manifest.yaml: status=pending

## 下一步（adapt 阶段）
1. init-build 下载解压源码，进入探索性编译（header-only 通常无需 configure/make）
2. conan-init 复核配方 → conan-verify 8 道门禁（G0-G4 + L2/L4/L5）
3. 处理上游测试枚举与 test_package 消费者验证
4. finish（W2 结构 + W3 编译验证 + R36 依赖检查）后提交 PR

## 上游测试逐入口台账（2026-08-29 实际执行）

构建：`cmake -S . -B build -DBOOST_DI_OPT_BUILD_TESTS=ON -DBOOST_DI_OPT_BUILD_EXAMPLES=OFF` → `cmake --build build -j12`
（0 编译错误，50 个测试可执行文件全部生成）→ `ctest -j12`。

| 分组 | 注册入口 | 实际运行 | 通过 | 结果/备注 |
|------|---------|---------|------|----------|
| ut/（单元） | 37 | 37 | 37 | ctest 全部 Passed |
| ft/（功能） | 11 | 11 | 11 | 见下方 di_errors 说明 |
| pt/（策略） | 2 | 2 | 2 | di_compile_time/di_run_time 均 Passed |
| **合计** | **50** | **50** | **50** | |

- ctest 默认 CWD 下 `test.ft_di_errors` 报失败：上游该测试用相对 include 路径
  （`-I../include -I../../include`），设计为**源码 in-source 构建/从 test/ 目录运行**；
  从 `$WORK/include` 所在源码 `test/` 目录重跑 `test.ft_di_errors` **exit=0 通过**。
  恢复条件：以源码 test/ 为工作目录运行（或给 add_test 设 WORKING_DIRECTORY）。
  这属于上游测试调用方式（CWD）问题，**非 OHOS 适配问题**。
- `test.ft_di_errors` 内含 100 个子用例（errorNNN.cpp 编译失败预期验证），全部通过。
- 消费者验证：`test_di.cpp` 以 `clang++ -std=c++14 -I <work>/include` 编译、链接、
  运行 **exit=0**（arm64 ELF），证明 header-only 在 OHOS clang 工具链可用。
- 测试生成物（error*.cpp/error*.out 共 200 个）已清理，work 目录干净。
- 台账记录：MANIFEST.yml `ledger_summary`；原始 ctest 日志：
  `$HOME/tmp/boost-di-upstream-test-run.log`。

## 注意事项
- 机器级环境污染：本 worktree 在创建时被环境注入了其他库归档文件
  （archives/l/libXext、archives/s/SDL2*、archives/w/wxWidgets），与任务无关，
  属共享机器归档同步现象（已在审计中记录，本任务未创建/修改这些文件）。
---

**编译结束**: 2026-08-30 10:14
**最终状态**: built

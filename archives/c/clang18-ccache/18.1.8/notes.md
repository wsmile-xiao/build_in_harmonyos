# clang18-ccache 18.1.8 适配笔记

## 编译环境
- 构建系统: cmake (project(ccache LANGUAGES C CXX), C++20)
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, aarch64-unknown-linux-ohos)
- 状态: built（conan create 全绿）

## 包版本与源码映射
- 任务头版本: 18.1.8（clang 18.1.8 工具链配对命名）
- 上游源码: ccache/ccache 官方 tag v4.14（2026-08-23 发布，ccache 最近稳定版）
  - URL: https://github.com/ccache/ccache/archive/refs/tags/v4.14.tar.gz
  - SHA-256: 5b107d2b5604cf3db7bc64b359544b914b1df2035667ab3cee9b737484aa299a
  - （gh-proxy 与 codeload.github.com 双源下载实测 SHA-256 一致；ccache 无
    18.1.8 版本号，任务头 18.1.8 系 clang 工具链配对命名，实际源码用官方 v4.14）

## 编译步骤
1. 源码: ccache v4.14 官方 tarball（SHA-256 已核验）
2. 构建系统: CMake, DEPS=DOWNLOAD（FetchContent 管第三方依赖）
3. 预下载 FetchContent 依赖: hiredis 1.4.1 / xxhash 0.8.3 / zstd 1.5.7，
   通过 FETCHCONTENT_SOURCE_DIR_* 指向本地（规避构建期 GitHub 不可达）
4. 配置: cmake -DDEPS=DOWNLOAD -DREDIS_STORAGE_BACKEND=ON -DHTTP_STORAGE_BACKEND=ON
   -DENABLE_TESTING=ON -DCMAKE_CXX_STANDARD=20（clang 15.0.4, ohos-aarch64 profile）
5. 编译: cmake --build（ccache_framework + ccache 可执行 + unittest）
6. 验证: ccache --version -> "ccache version 4.14"

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | std::ranges::all_of/any_of/equal 编译失败 | OHOS libcxx-ohos (LLVM 15.0.4) 未实现 ranges 算法 | 0001-0004 补丁: 迭代器版 std::all_of/std::any_of/std::equal（见 knowledge/drafts/DRAFT-clang18-ccache-18.1.8-ohos-libcxx-ranges-algorithms） |
| 2 | FetchContent xxhash/zstd 下载失败 | 构建期 GitHub 不可达 | 预下载依赖并设置 FETCHCONTENT_SOURCE_DIR_* |
| 3 | unittest 5 例失败（hardlink/fifo/fallocate） | HMDFS 文件系统不支持硬链接/FIFO/fallocate | 平台限制（E079/E446），候选挂载点核验后仍复现，如实计入台账 |
| 4 | conan create 直连 github 超时 | 网络对 github.com 直连不可达 | 本地 tarball 预置 + E017 ghfast.top 镜像注入（conan-verify 自动），conandata 保持官方 URL（R39/PF7 合规） |

## 上游测试
- unittest（doctest 2.5.3）: 源码声明 279 TEST_CASE / 注册 243 / 执行 243
  （238 通过, 5 失败=HMDFS 平台限制, 5 跳过）
- ctest 集成套件: 55 注册 / 51 通过 / 4 失败（均 HMDFS 平台/环境语义） / 26 跳过（条件缺失）
- 双口径: 238/279 (85.3%)；当前配置可执行集合 238/243 (97.9%)
  （详见 reports/test-report.md）

## R02 返工（2026-09-21）
- 目标: 用户要求上游测试零跳过、全量通过；同 worktree/分支/executor 内恢复全部失败/跳过/未实例化条目
- 候选挂载点系统核验: 全部可写挂载点逐项实测（mkdir/chmod 700/stat/link/mkfifo/fallocate），
  唯一合格候选 /data/storage/el2/base/haps/entry/files（drwx------ 700 保留，mkfifo/fallocate 可用）
- 恢复成果: 合格挂载点设 TMPDIR/TMP/TEMP 复跑 unittest → 243 例 240 通过（fallocate/mkfifo 用例恢复，+2）；
  残余 3 例失败全部 link(2)/create_hard_link（设备全挂载点硬链接 Permission denied，E079 家族）
- 5 例跳过: doctest::skip 运行时条件（AVX2 CPU 硬件缺失 + /U 路径），上游显式逻辑
- 36 例未实例化: #ifdef _WIN32 互斥分支（26）+ doctest::skip(avx2)（4）+ 禁用标记——均有明确上游排除条件
- ctest 26 条件跳过: CUDA cuobjdump/nvcc、redis-server、HIP runtime、script --return、clang15
  不支持 -fdiagnostics-format=text/-finput-charset/-fdiagnostics-set-output=sarif 参数——逐项实测核验为
  真实外部工具/服务/编译器能力缺失；test.base/test.config/test.remote_file 在合格挂载点复跑仍复现首错
- 全量通过率: 240/279 = 86.0%（R01 85.3%）；执行集合 240/243 = 98.8%
- 恢复台账: reports/test-recovery-ledger-r02.md

## 消费者/鸿蒙专项
- 消费者用例: 包内 ccache 包装 clang 编译 OHOS aarch64 目标 hello.c，
  二次编译缓存命中（Direct hit），产物 ELF64 AArch64 运行输出正确
- test_package: ccache --version + --show-stats 运行成功

## 知识
- 候选台账与七轴查重: reports/knowledge-candidate-ledger.md
- C1 new_draft: knowledge/drafts/DRAFT-clang18-ccache-18.1.8-ohos-libcxx-ranges-algorithms.{kv,md}
  （similar_to DRAFT-332 openrct2 libcpp15 兼容、clang16-ccache-4.14 分支 E900 草案）
- C2/C3 reuse_existing（E079/E446）---

**编译结束**: 2026-09-21 16:10
**最终状态**: built
---

**编译结束**: 2026-09-25 14:38
**最终状态**: built

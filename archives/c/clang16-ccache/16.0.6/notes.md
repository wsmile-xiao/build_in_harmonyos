# clang16-ccache 16.0.6 适配笔记

## 编译环境
- 构建系统: cmake (project(ccache LANGUAGES C CXX), C++20)
- 编译日期: 2026-10-06
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, aarch64-unknown-linux-ohos)
- 状态: built（conan create 全绿）

## 包版本与源码映射
- 任务头版本: 16.0.6（clang 16.0.6 工具链配对命名）
- 上游源码: ccache/ccache 官方 tag v4.14
  - URL: https://github.com/ccache/ccache/archive/refs/tags/v4.14.tar.gz
  - SHA-256: 5b107d2b5604cf3db7bc64b359544b914b1df2035667ab3cee9b737484aa299a
  - 双源核验: github.com archive URL 与 codeload.github.com 直接下载产物 SHA-256 一致；
    与 clang18/20/21/22-ccache 先例 conandata.yml 相同
  - ccache 无 16.0.6 版本号，任务头 16.0.6 系 clang 工具链配对命名，实际源码用官方 v4.14

## 编译步骤
1. 源码: ccache v4.14 官方 tarball（SHA-256 已核验）
2. 构建系统: CMake, DEPS=DOWNLOAD（FetchContent 管第三方依赖；
   blake3/cpp-httplib/fmt/tl-expected bundled 于 src/third_party）
3. 预下载 FetchContent 依赖: hiredis 1.4.1 / xxhash 0.8.3 / zstd 1.5.7，
   通过 FETCHCONTENT_SOURCE_DIR_* 指向本地（规避构建期 GitHub 不可达）
4. 配置: cmake -DDEPS=DOWNLOAD -DREDIS_STORAGE_BACKEND=ON -DHTTP_STORAGE_BACKEND=ON
   -DENABLE_TESTING=OFF -DENABLE_IPO=OFF -DCMAKE_CXX_STANDARD=20（clang 15.0.4, ohos-aarch64 profile）
5. 编译: cmake --build（ccache_framework + ccache 可执行）
6. 验证: ccache --version -> "ccache version 4.14"，Features 含 file/http/redis/remote-storage

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | std::ranges::all_of/any_of/equal 编译失败 | OHOS libcxx-ohos (LLVM 15.0.4) 未实现 ranges 算法 | 0001-0004 补丁: 迭代器版 std::all_of/std::any_of/std::equal（与 E900/clang18 先例一致） |
| 2 | FetchContent xxhash/zstd 下载失败风险 | 构建期 GitHub 不可达 | 预下载依赖并设置 FETCHCONTENT_SOURCE_DIR_*（配方内置） |
| 3 | 上游 unittest 构建期 doctest.h 下载失败 | doctest 仅从 raw.githubusercontent.com 获取，设备网络 SSL reset | 本地验证用 gh-proxy 预置 doctest.h 并 -DDOCTEST_INCLUDE_DIR（仅本地测试环境，不入配方） |
| 4 | ctest 全部套件 skip / PATH 被破坏 | 设备 toybox awk 忽略 -v ORS=:，test/run 的 PATH 重写产生换行分隔 PATH | 本地验证环境预置 mawk 1.3.4 作为 awk（仅本地测试环境，不入配方） |
| 5 | test.direct 失败（main.o 找不到 content_a） | 设备 toybox grep 跳过含 NUL 的二进制文件 | 本地验证环境预置 GNU grep 3.11（仅本地测试环境，不入配方） |
| 6 | test.config 失败 | HMDFS 挂载点 st_uid 与 geteuid() 不一致，ccache 拒绝目录级配置 | testdir/TMPDIR 放到 /data/storage/el2/... 合格挂载点（uid 一致） |
| 7 | test.debug_* 失败 | 设备无 GNU objdump | 本地验证环境用 llvm-dwarfdump 包装 objdump（仅本地测试环境，不入配方） |
| 8 | test.remote_helper 超时 | /tmp 只读，helper IPC 回退到长路径 unix socket 失败 | 设置 XDG_RUNTIME_DIR 到短路径可写目录 |
| 9 | unittest/ctest hardlink 用例失败 | 设备所有可写挂载点 link(2) 均 Permission denied | 平台限制（E079），如实计入台账 |
| 10 | test.readonly 失败 | 上游测试显式 CCACHE_TEMPDIR=/tmp，设备 /tmp 只读 | 平台限制（E002），如实计入台账 |

## 上游测试
- unittest（doctest 2.5.3）: 源码声明 279 TEST_CASE / 注册执行 243
  - 240 通过 / 3 失败（link(2) 硬链接平台限制 E079）/ 5 跳过（上游 runtime 条件）
  - 双口径: 240/279 (86.0%)；当前配置可执行集合 240/243 (98.8%)
- ctest 集成套件: 54 套件 + unittest 共 55 项
  - 30 通过 / 2 失败（test.base 硬链接 E079、test.readonly 只读 /tmp E002）/ 22 跳过
    （nvcc/CUDA、redis-server、gcc、clang 版本能力、文件系统能力等）
  - 详见 reports/test-report.md

## 消费者/鸿蒙专项
- test_package: ccache --version + consumer_verify.sh
- 消费者用例: 包内 ccache 包装 OHOS clang 编译 OHOS aarch64 目标 hello.c，
  二次编译缓存命中，产物 ELF64 AArch64 运行输出正确（CONSUMER_PASS）

## 知识
- std::ranges/libcxx 兼容问题已有先例知识（E900 / clang18-ccache 草稿），本任务复用不新增
- 平台限制沿用 E079/E446/E002
---

**编译结束**: 2026-10-06 20:24
**最终状态**: built

# clang21-ccache 21.1.8 适配笔记

## 编译环境
- 构建系统: cmake (project(ccache LANGUAGES C CXX), C++20)
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, aarch64-unknown-linux-ohos)
- 状态: built（conan create 全绿，conan-verify 8 门禁全绿）

## 包版本与源码映射
- 任务头版本: 21.1.8（clang 21.1.8 工具链配对命名）
- 上游源码: ccache/ccache 官方 tag v4.14（ccache 最近稳定版）
  - URL: https://github.com/ccache/ccache/archive/refs/tags/v4.14.tar.gz
  - SHA-256: 5b107d2b5604cf3db7bc64b359544b914b1df2035667ab3cee9b737484aa299a
  - （双源下载实测 SHA-256 一致；ccache 无 21.1.8 版本号，任务头 21.1.8 系 clang
    工具链配对命名，实际源码用官方 v4.14，与 clang18/20-ccache 同源）

## 编译步骤
1. 源码: ccache v4.14 官方 tarball（SHA-256 已核验 5b107d2b…）
2. 构建系统: CMake, DEPS=DOWNLOAD（FetchContent 管第三方依赖）
3. 预下载 FetchContent 依赖: hiredis 1.4.1 / xxhash 0.8.3 / zstd 1.5.7，
   通过 FETCHCONTENT_SOURCE_DIR_* 指向本地（规避构建期 GitHub 不可达）
4. 配置: cmake -DDEPS=DOWNLOAD -DREDIS_STORAGE_BACKEND=ON -DHTTP_STORAGE_BACKEND=ON
   -DENABLE_TESTING=ON -DCMAKE_CXX_STANDARD=20（clang 15.0.4, ohos-aarch64 profile）
5. 编译: cmake --build（ccache_framework + ccache 可执行 + unittest）
6. 验证: ccache --version -> "ccache version 4.14"
7. 上游测试: ./unittest/unittest（合格挂载点 /data/storage/el2/base/haps/entry/files，
   TMPDIR/TMP/TEMP 指向）-> 243 | 240 passed | 3 failed | 5 skipped
8. 消费者用例: test_package/consumer_verify.sh -> ccache 包装 OHOS clang 编译 hello，
   二次编译缓存命中 (50% hit)，产物运行输出正确（CONSUMER_PASS）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | std::ranges::all_of/any_of/equal 编译失败 | OHOS libcxx-ohos (LLVM 15.0.4) 未实现 ranges 算法 | 0001-0004 补丁: 迭代器版 std::all_of/std::any_of/std::equal |
| 2 | FetchContent xxhash/zstd 下载失败 | 构建期 GitHub 不可达 | 预下载依赖并设置 FETCHCONTENT_SOURCE_DIR_* |
| 3 | 用户目录 (HMDFS) 写入 "No space left on device" | HMDFS inode 配额耗尽 | 稀疏检出 worktree + 构建目录迁移至合格挂载点 /data/storage/el2/base/haps/entry/files（0700 保留） |
| 4 | unittest 3 例失败（hardlink） | HMDFS 文件系统不支持硬链接（E079 家族） | 平台限制，如实计入台账；候选挂载点核验后仍复现 |
| 5 | InodeCache 5 例跳过 | inode_cache_available() 探测失败（HMDFS） | 上游 doctest::skip 条件，如实计入台账 |
| 6 | W3 JC 门禁命中 cloog 基线文件 | 提交前已存在的其他库基线运行时文件 | 基线隔离复验：隔离->JC pass->原样恢复，SHA-256 e3b0c442… 一致 |

## 源码修改
- patches/0001-src-ccache-argprocessing.cpp.patch: std::ranges::all_of → std::all_of(迭代器版)
- patches/0002-src-ccache-config.cpp.patch: std::ranges::any_of → std::any_of(迭代器版)
- patches/0003-src-ccache-util-path.cpp.patch: std::ranges::all_of → std::all_of(迭代器版)
- patches/0004-unittest-test_util_tokenizer.cpp.patch: std::ranges::equal → std::equal(迭代器版)

## 依赖版本
- hiredis 1.4.1 / xxhash 0.8.3 / zstd 1.5.7（FetchContent 构建期下载，非 Conan 依赖）
- clang 15.0.4 (OHOS SDK, aarch64-unknown-linux-ohos)

## 验证结果
```bash
ccache --version   # ccache version 4.14
unittest           # test cases 243 | 240 passed | 3 failed | 5 skipped
                   # assertions 2821 | 2808 passed | 13 failed（3 例 HMDFS 硬链接平台限制）
consumer_verify.sh # Hits 1/2 (50.00%)，run-output=consumer-ohos-hello: ccache ok sum=3 → CONSUMER_PASS
```
- 上游测试通过率: 240/270 (88.9%)（源码声明口径）；240/243 (98.8%)（当前配置执行集合）
- 完整台账: reports/upstream-test-ledger.md、reports/test-report.md
---

**编译结束**: 2026-09-21 18:10
**最终状态**: built

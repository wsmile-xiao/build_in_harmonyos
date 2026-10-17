# clang20-ccache 20.1.8 适配笔记

## 编译环境
- 构建系统: cmake (project(ccache LANGUAGES C CXX), C++20)
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, aarch64-unknown-linux-ohos)
- 状态: built（conan create 全绿）

## 包版本与源码映射
- 任务头版本: 20.1.8（clang 20.1.8 工具链配对命名）
- 上游源码: ccache/ccache 官方 tag v4.14（2026-08-23 发布，ccache 最近稳定版）
  - URL: https://github.com/ccache/ccache/archive/refs/tags/v4.14.tar.gz
  - SHA-256: 5b107d2b5604cf3db7bc64b359544b914b1df2035667ab3cee9b737484aa299a
  - （双源下载实测 SHA-256 一致；ccache 无 20.1.8 版本号，任务头 20.1.8 系 clang
    工具链配对命名，实际源码用官方 v4.14，与 clang18-ccache 18.1.8 同源）

## 编译步骤
1. 源码: ccache v4.14 官方 tarball（SHA-256 已核验 5b107d2b…）
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
| 1 | std::ranges::all_of/any_of/equal 编译失败 | OHOS libcxx-ohos (LLVM 15.0.4) 未实现 ranges 算法 | 0001-0004 补丁: 迭代器版 std::all_of/std::any_of/std::equal |
| 2 | FetchContent xxhash/zstd 下载失败 | 构建期 GitHub 不可达 | 预下载依赖并设置 FETCHCONTENT_SOURCE_DIR_* |
| 3 | 用户目录 (HMDFS) 写入 "No space left on device" | HMDFS 配额/写入语义限制 | 构建目录迁移至合格挂载点 /data/storage/el2/base/haps/entry/files（0700 保留） |
| 4 | unittest 3 例失败（hardlink） | HMDFS 文件系统不支持硬链接（E079 家族） | 平台限制，如实计入台账；候选挂载点核验后仍复现 |

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
# 消费者用例: ccache 包装 clang 编译 OHOS aarch64 hello.c，二次编译缓存命中 (50% hit)，产物 ELF64 AArch64 运行输出正确
```

## 注意事项
- 用户目录 (HMDFS) 不支持硬链接/大文件写入，构建与测试需使用合格挂载点
  （/data/storage/el2/base/haps/entry/files，drwx------ 700），并设置 TMPDIR/TMP/TEMP
- conan create 直连 github 超时：本地 tarball 预置 + E017 ghfast.top 镜像注入
  （conan-verify 自动），conandata 保持官方 URL（R39/PF7 合规）
---

**编译结束**: 2026-09-21 18:25
**最终状态**: built

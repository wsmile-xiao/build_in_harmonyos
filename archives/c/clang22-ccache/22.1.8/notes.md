# clang22-ccache 22.1.8 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, aarch64-unknown-linux-ohos)
- 状态: built

## 来源说明（双组件，已澄清）
- 主程序 ccache 主体：官方 tag **v4.14**（ccache 仓库无 22.1.8 版本；r02 已实测 v22.1.8.tar.gz HTTP 404、v4.12.1 200、tags 最新 v4.14）。
- 配套组件 clang：llvm-project @ **llvmorg-22.1.8**（工具链配对命名，作为配套组件接入，不单独交付）。
- 归档: https://github.com/ccache/ccache/archive/refs/tags/v4.14.tar.gz
- SHA-256: 5b107d2b5604cf3db7bc64b359544b914b1df2035667ab3cee9b737484aa299a（双源交叉核验，与 clang18/20/21-ccache 同源）

## 编译步骤
1. 源码: v4.14.tar.gz（官方 archive URL）
2. 构建系统: CMake (ccache 自带 CMakeLists.txt)
3. 依赖管理: DEPS=DOWNLOAD (FetchContent 自动下载 blake3, fmt, hiredis, xxhash, zstd 等)
4. 存储后端: file, http, redis 全部启用 (无裁剪)
5. 测试: ENABLE_TESTING=OFF (包构建), 上游 unittest/doctest 适配阶段单独运行
6. C++20: CMAKE_CXX_STANDARD=20 (ccache 4.14 要求)

## 依赖说明
ccache 通过 CMake FetchContent 管理所有第三方依赖，不需要预先发布 conan 包:
- Hiredis 1.4.1 (DOWNLOADED, 预下载)
- Xxhash 0.8.3 (DOWNLOADED, 预下载)
- Zstd 1.5.7 (DOWNLOADED, 预下载)
- 其余 (blake3, fmt, cpphttplib, nonstd-span, tl-expected) BUNDLED

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | std::ranges::all_of/any_of/equal 编译失败 | OHOS libcxx-ohos (LLVM 15.0.4) 未实现 ranges 算法 | 0001-0004 补丁: 迭代器版 std::all_of/std::any_of/std::equal（与 clang18/20/21-ccache 同族补丁） |
| 2 | FetchContent xxhash/zstd 下载失败 | 构建期 GitHub 不可达 | 预下载依赖并设置 FETCHCONTENT_SOURCE_DIR_* |
| 3 | 版本显示 unknown | git clone 创建的 tarball 缺少 git archive 格式标记 | 使用 GitHub 官方 archive URL (conandata.yml) |

## 消费者用例
- test_package/consumer_verify.sh -> ccache 包装 OHOS clang 编译 hello.c，
  验证首次 miss、二次 cache hit、链接产物运行输出 "consumer-ohos-hello: ccache ok"。

## 同族先例（已验证路径）
- clang18-ccache 18.1.8 (PR #11718)：ccache v4.14 + clang 18.1.8，conan create (ohos-aarch64) exit 0，
  unittest/doctest 243 用例 240 通过 3 失败 5 跳过，W3 本地 CI finish_success。
- clang20-ccache 20.1.8 / clang21-ccache 21.1.8：同源 v4.14，同 4 补丁。

**最终状态**: built
---

**编译结束**: 2026-09-22 14:21
**最终状态**: built

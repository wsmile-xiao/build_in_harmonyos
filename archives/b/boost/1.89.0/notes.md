# boost 1.89.0 适配笔记

## 编译环境
- 构建系统: custom（clang++ 直编 Boost.Test 静态库 + 内嵌上游 ts-suite 真实运行，绕过 b2）
- 编译日期: 2026-09-30
- 编译器: clang/clang++ 15.0.4 (Target: aarch64-unknown-linux-ohos, /data/service/hnp/bin)
- 状态: built

## 编译步骤

1. 源码: `boost_1_89_0.tar.bz2`
   (SHA256 `85a33fa22621b4f314f8e85e1a5e2a9363d22e4f4992925d4bb3bc631b5a0c7a`)
   下载地址 `https://archives.boost.io/release/1.89.0/source/boost_1_89_0.tar.bz2`。
2. b2 不可用: 上游 `bootstrap.sh` 工具链白名单无 OHOS
   (`grep -ci ohos bootstrap.sh` → 0)，沿用本仓库 1.90.0 已验证方案：
   clang++ 直编 `libs/test/src` 的 19 个 Boost.Test 源文件
   （与上游 `libs/test/build/CMakeLists.txt` 的 `BOOST_UTF_SRC` 清单逐项一致）。
3. 包内库 `libboost_unit_test_framework.a`，编译参数
   `-std=gnu++14 -O2 -DNDEBUG -DBOOST_TEST_ALTERNATIVE_INIT_API`，llvm-ar rcs 打包。
   消费方契约（与 1.90.0 逐字一致，`libs/test/impl/unit_test_main.ipp`
   的 main() 两版本相同）：库提供 main()，消费方定义 `bool init_unit_test()`。
4. 上游测试（规则 5）：build() 内另编一个默认 init API 的测试专用库
   （与上游 CMake `boost_test_framework` 目标一致：全局 `-DBOOST_TEST_NO_LIB`，
   无 `BOOST_TEST_ALTERNATIVE_INIT_API`），再编译并真实运行
   `libs/test/test` 下官方 ts-suite：7 个 suite 共 73 个单文件测试 +
   datasets 12-TU 单可执行 = 74 个可执行，与上游
   `libs/test/test/CMakeLists.txt` 的 `bt-unittest-*` 测试集合逐一对应。
   - 测试编译标准 `-std=c++17`（R04 先例：1.90.0 实测上游 CMake 强加
     `-std=c++11` 导致 fp-multiprecision 系列 72 用例编译失败，
     Boost.Math/Multiprecision 头需要 C++14+ 类型）。
   - 运行环境经 `clang++ -print-file-name=libc++_shared.so` 自省注入 SDK
     libc++ 目录到 LD_LIBRARY_PATH（防 rc=127，1.85.0 先例）。
   - 逐条结果写入 `build_folder/upstream-tests-report.txt`。
   - `test-timeout-fail` / `test-timeout-suite-fail` 按上游 Jamfile.v2 L185/L187
     的 `run-fail` 标注计为预期失败（exit≠0 记 pass），其余用例 exit 0 记 pass。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | b2 构建系统不兼容 OHOS（E068/E099） | bootstrap.sh toolset 白名单无 OHOS | clang++ 直编 Boost.Test 19 源 + 头文件打包（沿用 1.90.0 方案） |
| 2 | 上游 CMake 对非 MSVC 强加 -std=c++11，fp-multiprecision 系列编译失败（R04，1.90.0 实测） | Boost.Math/Multiprecision 头使用 C++14+ 类型 | 内嵌 runner 显式 -std=c++17 |
| 3 | 干净 conan 环境运行测试可执行 rc=127 | libc++_shared.so 不在默认搜索路径 | -print-file-name 自省注入 LD_LIBRARY_PATH（1.85.0 先例） |
| 4 | test-timeout-fail 系列用例按设计失败 | 用例本身验证超时机制（上游 Jamfile 标注 run-fail） | runner 按预期失败语义判定，报告中同时给出原始退出码 |

## 源码修改

无补丁。1.84/1.85 的 0001 补丁（pthread_setcancelstate）不需要：
19 个 Boost.Test 源文件均不 include `sp_thread_sleep.hpp`（已逐文件核验）。

## 依赖版本

- 无强制第三方依赖（零 `self.requires`）。
- 可选 iostreams 条件依赖（zlib/1.3.1、bzip2/1.0.8、liblzma/5.8.1、zstd/1.5.7）
  本配方不启用（不编译 iostreams 库）。
- 工具链: clang 15.0.4 / llvm-ar（/data/service/hnp/bin）。

## 验证结果

{构建后回填：conan create / conan-verify / 上游 ts-suite 74 用例统计}

## 注意事项

- 包内库 main() 走 `BOOST_TEST_ALTERNATIVE_INIT_API`：消费方必须提供
  `bool init_unit_test()`（注册用例并返回 true），见 `test_package/test.cpp`。
- `header_only` 选项：仅装头文件、不产库（默认 `header_only=False`）。
- 上游 Jamfile 中 timeout 系列（L184-L187）因 `cxx11_hdr_thread/chrono`
  要求被注释禁用；上游 CMake 路径仍会构建它们，本 runner 同样构建并按
  run-fail 语义记录实际结果。
---

**编译结束**: 2026-10-03 21:48
**最终状态**: built

# utfcpp20 0.3 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMake ≥3.16，C++20）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4（OHOS 适配版 conan 2.29.1 + ci/conan/profiles/ohos-aarch64）
- 状态: built
- worktree: ~/qzy/utfcpp20 分支 feat/utfcpp20-0.3（基线 upstream/main caa4529859）

## 任务与 W0/W0b
- 任务号 #5895（开源鸿蒙PC专项积分赛-依赖），认领人 wanderlust_0823，无同名同版本重复任务，upstream/main 归档树无 utfcpp20 目录（utfcpp/utf8cpp 为不同软件包）。
- W0: 库本身零依赖（源码树无第三方依赖目录），preflight 无缺失依赖。测试框架 nemtrif/ftest tag 0.3 未发布到制品仓：`conan download ftest/0.3 -r=ohpcd` 期间制品仓对该请求报 `error:system acceleration policy not enabled`（同窗口 frozen/1.1.1、doctest/2.4.12 已发布包同样报错，robin-map/1.4.1、zlib/1.3.1 成功，属按请求抖动）；`ftest/*` 通配查询明确返回 0 条记录，判定未发布。
- W0b: 无同软件历史归档。语言预检（R47）被误报触发 env_unsupported，证据见下文"遇到的问题"；真实主体语言 cpp 与任务声明一致，构建系统 cmake，按误报处置继续适配（先例：tinydng/tinyvdb/hashchop/smashtable 同族）。

## 编译步骤
1. `ohc-run.py init-build utfcpp20 0.3 --url=https://github.com/nemtrif/utfcpp20/archive/refs/tags/v0.3.tar.gz`（SHA256 4f9b164185b626d71beac3aa4e4d6d1297d8fd562547022e611dd8c18173ad77）
2. `ohc-run.py lang-preflight`（误报取证后继续）
3. conan-init 首稿为 Autotools 模板，按上游实际构建系统重写为 CMake 配方
4. 修改源码 work 树门控 tests → `refresh-patch --auto` 生成 patches/0001-CMakeLists.txt.patch（+9/-2）
5. `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`：rc=0，库编译 + test_package 编译运行全部通过
6. 上游套件真机复现：官方 ftest 0.3 源码 + `FETCHCONTENT_SOURCE_DIR_FTEST` 配置原始上游树（utfcpp20-0.3.orig），ctest 2/2 通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 mixed → 自动写 env_unsupported 终态 | lang_detect 源码统计把 doc/html 下 22 个 doxygen 生成 js（jquery.js、search/*.js）计为 nodejs 源文件（28 文件中 nodejs:22 vs cpp:6，"主体占比 79%"），与 manifest=cpp 冲突判 mixed；真实源码 6 个文件全部为 C++ | 证据：js 文件路径全部位于 doc/html/（文档资产非源码）；manifest=CMakeLists.txt project( → cpp，构建系统=cmake。按主体判 cpp 继续适配，全门禁闭环后以 result --force 覆盖误判终态 |
| 2 | 上游 tests/ 无条件 FetchContent 拉取 nemtrif/ftest，CI 无网络必失败 | ftest 未发布到制品仓，不能作为 Conan 测试依赖接入，也不允许 FetchContent 联网回源 | 补丁把 tests 门控为 UTF20_BUILD_TESTS 选项（默认 OFF），生产构建零外部依赖；上游套件真机以 FETCHCONTENT_SOURCE_DIR_FTEST 指向官方 ftest 源码单独运行（不改上游测试源码） |
| 3 | 上游 CMake 无 install() 规则 | 上游仅 add_library，未提供安装导出 | package() 用 conan copy 收构建树 *.a/*.so，显式拷贝 include/ 头文件与 LICENSE；cpp_info.libs=["utfcpp20"] |

## 源码修改
- patches/0001-CMakeLists.txt.patch（strip: 1）：顶层 CMakeLists.txt 的 `enable_testing()/add_subdirectory(tests)` 门控进 `if(UTF20_BUILD_TESTS)`，新增 option 默认 OFF。未修改任何测试源码与断言。

## 依赖版本
- 无运行时/编译依赖（零依赖包）。
- 上游测试框架 nemtrif/ftest tag 0.3 仅用于真机套件复现，不进入配方依赖图。

## 验证结果
- 上游测试（R51 三步法）：
  - 静态清点：tests/utfcpp20.test.cpp 11 个 `TEST(` + tests/core.test.cpp 5 个 `TEST(` = **16**（ftest 框架注册入口）
  - 真机实际执行：ctest 2/2 套件通过，ftest 明细 utfcpp20test 11/11 PASSED + coretest 5/5 PASSED = **16/16，0 失败 0 跳过**
  - 日志：设备 ~/tmp/uc2/utfcpp20/ctest_run.log（ctest）与 upstream-build/tests 明细输出
- test_package 消费者测试：test_utfcpp20 编译链接安装后库并调用 utfcpp::append_to_utf8/append_to_utf16/utf8_to_16/utf16_to_8/u8_iterator 与异常拒绝，**9 项断言全部通过**（含正反例）。
- conan create / conan-verify / finish：见 reports/ 与 .ci-result.json。

## 注意事项
- CI 环境不执行上游套件（ftest 未发布、无网络回源），生产验证以消费者测试覆盖；解除条件：ftest/0.3 发布到制品仓后，按仓库 skiparray 先例（upstream_tests 选项门控 requires）接入 CI。
- lang-preflight 误报的 result.json 曾被工具自动写入共享路径 ~/ohpcd-ai-worker-result.json（status=env_unsupported, draft:false）；本任务终态将覆盖该文件。
- OHOS clang 15 + libc++ 对 char8_t/u8string/std::u8string_view 支持完整，未发现 C++20 标准库缺口；库未使用 concepts/ranges/coroutines。
---

**编译结束**: 2026-09-06 11:40
**最终状态**: built

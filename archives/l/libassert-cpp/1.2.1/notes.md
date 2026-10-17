# libassert-cpp 1.2.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMake，输出 `assert` 目标：include/assert.hpp + src/assert.cpp）
- 编译日期: 2026-08-30
- 编译器: clang/clang++ 15.0.4 (OHOS SDK 26.0.0.18 sysroot, aarch64-linux-ohos)
- 状态: built（bootstrap + 首轮 adapt，conan create 含 test_package 消费者测试通过 1/1）

## 官方来源核验（Bootstrap gate）
- 官方仓库: https://github.com/jeremy-rifkin/libassert
- 正式标签: v1.2.1（codeload 官方 release tarball，根目录 libassert-1.2.1，CMakeLists VERSION 1.2.1 一致）
- 源码校验值: sha256 `58538368751d59f2fc756046eaa4cc926b994ba930f1889d770106c9a1db3425`
- 本机 github.com:443 直连不可达；经 codeload.github.com 官方 tarball 通道核验，未用镜像替身

## 编译步骤
1. `git worktree add -b feat/libassert-cpp-1.2.1 <wt> main` 从可审计 main(5292d309) 建专用 worktree
2. `ohc-run.py init-archive libassert-cpp 1.2.1 <url> cmake` 生成骨架，补齐 conanfile.py / conandata.yml / test_package
3. `conan create . --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<same>`
4. 迭代修复到 conan create 全绿（含 test_package 消费者构建+运行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `get() got an unexpected keyword argument '1.2.1'` | conandata.yml 为版本键结构，source() 直接展开全部 sources | `get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)` |
| 2 | cpptrace 编译 `windows.h not found` | 上游 FetchContent 拉 cpptrace v0.2.1；OHOS 未被 CMake 识别为 UNIX，自动配置误选 dbghelp/winapi 后端 | 配方显式指定 `CPPTRACE_UNWIND_WITH_EXECINFO=ON`、`CPPTRACE_GET_SYMBOLS_WITH_NOTHING=ON`、`CPPTRACE_DEMANGLE_WITH_CXXABI=ON`（OHOS sysroot 有 execinfo.h + libunwind.a） |
| 3 | test_package 运行报 `libcpptrace.so` 符号缺失 | libassert.so 动态链接了 FetchContent 构建树里的 libcpptrace.so，未打包 | `CPPTRACE_STATIC=ON` + `CMAKE_POSITION_INDEPENDENT_CODE=ON`，cpptrace 并入 libassert.so |
| 4 | test_package 编译期 `assert.hpp not found` | 上游把 assert.hpp 安装在 `include/assert/assert/` 并以此为 INSTALL_INTERFACE | `cpp_info.includedirs = ["include/assert/assert"]`（内部 `#include "../third_party/magic_enum.hpp"` 同一包内可解析） |

## 源码修改
无补丁（未修改上游源码；配方内配置项解决平台差异）。patches/ 未创建。

## 依赖版本
- cpptrace v0.2.1（上游 FetchContent 内嵌；静态并入）
- magic_enum（上游 third_party 内嵌）
- 无外部 Conan 依赖

## 验证结果
```bash
conan create . --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<same>
# exit 0；test_package: 1/1 Passed (test_libassert_cpp 链接 assert::assert 并运行 ASSERT 宏)
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（cpptrace 静态化 + OHOS 后端固定 + includedirs 对齐安装布局） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/ | 消费者验证（CMakeLists / conanfile.py / test.cpp / MANIFEST.yml） |
| manifest.yaml | 版本级清单（built） |
| notes.md | 本文档 |

## 注意事项
- 未 commit/push/PR/发布远端制品（任务边界禁止远端写操作，analysis_approved_remote_ci=false）
- 上游完整测试套件（tests/ 目录，ctest 体系）尚未在 OHOS 上全量运行，为未完成项；当前以 test_package 消费者验证为准
- 后续可用 `ASSERT_BUILD_TESTS=ON` 探索上游 tests/basic 等用例的 OHOS 适配

---

# R02 返工记录（2026-08-31，upstream tests + local closure）

## 上游测试入口识别（tests/，由主 CMakeLists 内联注册）
| 入口 | 发现规则 | 数量 |
|------|---------|------|
| integration | `ASSERT_BUILD_TESTS=ON` 时 `add_executable(integration)` + `add_test(integration COMMAND python3 run-tests.py <bin> <build_type> <compiler_id> <cxx_std>)`，expected 文件匹配 `tests/integration/expected/{compiler}.txt` | 1 |
| unit | 遍历 `tests/unit/*.cpp`，每文件 `add_executable(<name>)` + `add_test(COMMAND <name>)` | 7 |
| basic | 独立 `ASSERT_BUILD_BASIC_TEST=ON` 开关，不注册 add_test | 0（未启用） |

## 实际运行（OHOS aarch64 clang 15，默认 cppstd=17 编译）
- 配置: `cmake -DASSERT_BUILD_TESTS=ON -DFETCHCONTENT_SOURCE_DIR_CPPTRACE=<本地 vendored cpptrace v0.2.1>`（github.com git 协议不可达）
- 命令: `cmake --build . -j20`（exit 0）→ `ctest --output-on-failure`（LD_LIBRARY_PATH=build 目录）
- 修复前: 8 项中 3 项崩溃（integration / disambiguation / tokens_and_highlighting），根因 `std::regex_error: invalid back reference`
- 修复后: **7/8 Passed，1 Failed**（integration 输出比对失败，非崩溃）

## 库内首个真实问题与修复（R02 门禁）
| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | 3 个上游测试运行时抛 `regex_error: The expression contained an invalid back reference` | OHOS libc++ std::regex 不支持 lookahead 断言内反向引用；上游 `raw_string_literal` 正则使用 tempered-dot `(?:(?!\)\2\").)*` | patch `patches/0001-fix-raw-string-literal-regex-libcxx.patch`：改为 lazy 匹配 `\([\s\S]*?\)\2"`（反向引用只出现在普通位置）。已在 8 种合法 raw-string token 形态上实证等价（plain/u8/L/分隔符/嵌套括号/引号/换行） |
| 2 | conan-verify 干净构建 git clone cpptrace 失败 | github.com git 协议不可达 | 配方 vendored cpptrace v0.2.1 官方 tarball（codeload，sha256 `3184f404c61b6b8ba6fe7c64fc40d1c3d6d87df59bcacf1845d846101bc22f9a`），`FETCHCONTENT_SOURCE_DIR_CPPTRACE` 指向本地源；libassert 源 URL 改用官方 codeload 端点（同 tag 同 sha256） |
| 3 | codeload URL 无扩展名被 conan get() 误按 zip | conan get 从 URL 推断格式 | 显式 `filename="*.tar.gz"` 参数 |

## integration 失败归属（非崩溃，输出比对基线差异）
- 现象: 18x/36 tokens vs expected 186；堆栈帧 `at :?` 空符号；`icdiff`/`diff -y` 工具缺失
- 归属: OHOS 无 addr2line/libdwarf 符号化后端（cpptrace `GET_SYMBOLS_WITH_NOTHING`），且上游 expected/clang.txt 为 libstdc++/glibc Linux 全符号输出；属平台基线/输出比对差异，非库内代码缺陷。已用 assert.cpp 平台行为实测 + 5 个完整 unit 测试通过佐证库功能正常。

## 门禁结论（R02）
- conan create 干净构建: PASS（exit 0，test_package 1/1，含 0001 补丁 + vendored cpptrace）日志 sha256 `a37586ea4799f15bc1bbedda01031dbcd08cee5575cdf64fb7f68ff40781fca6`
- conan-verify: G0/G1/G2/G3/G4 全 PASS，报告判定"配方验证通过"
- W3 本地 CI 等价（conan create）: PASS
- 完整 finish 未运行：其 gen_summary 会重写仓库根级 SUMMARY.md（允许范围外共享框架文件），已在最终审计前隔离

## R02 原子性审计
- staged: 空；unstaged: 仅 `archives/l/libXext/*` 两处（会话开始前既有修改，本次未触碰）
- untracked: 仅 `archives/l/libassert-cpp/1.2.1/` 的 11 个源文件（conanfile.py / conandata.yml / manifest.yaml / notes.md / patches/0001 / reports/conan-create.log + conan-verify-report.md / test_package 4 文件）
- 工具残留（`.conan-verified`、`conandata.yml.ghfast-bak`）已清理；build/、__pycache__ 由 .gitignore 过滤
- 零污染: 未改其他库、共享框架、Skill、控制器；无 commit/push/PR/远端 CI
---

**编译结束**: 2026-08-31 18:27
**最终状态**: built

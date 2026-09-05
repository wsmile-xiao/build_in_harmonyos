# tinyspline 0.6.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMake，非 autotools；conan-init 误判为 autotools 已手工修正配方模板）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++（OHOS SDK sysroot）
- 状态: built

## 编译步骤

```bash
# 上游 CMake 配置（测试开启、示例与文档关闭以减少绑定依赖）
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DTINYSPLINE_BUILD_EXAMPLES=OFF -DTINYSPLINE_BUILD_DOCS=OFF \
  -DTINYSPLINE_BUILD_TESTS=ON -DCMAKE_C_FLAGS="-Wno-error=long-long"
cmake --build build -j2
cmake --install build --prefix $TEST_PREFIX
ctest --output-on-failure   # 2/2 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 github 超时 | urllib 直连 github 抖动 | curl + ghfast.top 镜像预置 tarball，sha256 校验一致 |
| 2 | lang-preflight 判为 go → env_unsupported | manifest 扫描命中 examples/go、test/go 的 go.mod（绑定示例），优先级高于顶层 CMakeLists.txt | 人工核验主体语言为 C(39 .c)/C++(3)，c↔cpp 兼容族继续；误判记录于最终报告 |
| 3 | 编译错误 -Werror,-Wlong-long | OHOS sysroot math.h isinf 宏用 long long，上游 -std=c89 -Werror | CMAKE_C_FLAGS=-Wno-error=long-long（E063 精准类别禁用） |
| 4 | conan create test_package 报 Library 'tinysplinecxx' not found | GNUInstallDirs 选 lib64，CMakeDeps 查 lib | cache_variables[CMAKE_INSTALL_LIBDIR]=lib + package_info.libdirs 兼容 |
| 5 | test_package test.c 编译错 | TS_END_TRY 在 TRY 块内提前使用 + 使用了不存在的 ts_bspline_evaluate | 按上游 quickstart 模式重写：TS_CATCH/TS_FINALLY 一次闭合，ts_bspline_eval |
| 6 | W3 JC junk 拦截 4 个其他库基线文件 | embree/flatcv/libmorton/goaccess 运行时状态文件已提交进 main 基线（full 模式 ls-files 扫到） | JUNK_PR_DIFF 仅含本库 PR 文件（CI prdiff 同语义）隔离复验，审计记录不含本库 diff |

## 源码修改

无补丁（patches/ 空）。适配均在 conanfile.py 配方层完成（编译标志、libdir、选项）。

## 依赖版本

无外部依赖（纯 C/C++ 库，仅在生成语言绑定时可选的 SWIG 未使用，TINYSPLINE_ENABLE_* 全部默认 OFF）。

## 验证结果

```bash
# 上游测试（Step 2 实测）
ctest --test-dir build            # 2/2 passed (tinyspline_tests, tinysplinecxx_tests)
# test_package 消费者测试（conan create 内）
ctest --test-dir .../test_package/build/clang-15-armv8-17-release  # 1/1 passed
# W3 本地 CI 模拟（finish step 5/10）
bash ci/conan/build_and_test.sh tinyspline/0.6.0  # 通过（JC prdiff 隔离基线）
# Conan 配方验证
ohc-run.py conan-verify tinyspline 0.6.0          # G0-G4 ALL PASS
```

## 注意事项

- tinyspline 是 C 库（tinyspline.c/parson.c）+ C++ 接口（tinysplinecxx.cxx），package_info 同时导出 libtinyspline 与 libtinysplinecxx。
- test_package 使用 C 接口即可满足 R34 实质依赖验证；TS_TRY 宏族必须按上游模式一次闭合。
- 上游 0.6.0 官方 release tag 为 v0.6.0（commit 5f0e8fad34e86771cfae3dac4beef5f1858d5610）。---

**编译结束**: 2026-09-03 10:29
**最终状态**: built
---

**编译结束**: 2026-09-03 10:33
**最终状态**: built

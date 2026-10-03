# HdrHistogram_c 0.11.8 适配笔记（包名 hdr-histogram）

## 编译环境
- 构建系统: cmake (上游 CMakeLists，conan CMakeToolchain)
- 编译日期: 2026-10-02
- 编译器: clang 15 (OHOS SDK 26.0.0.18)
- 目标平台: HarmonyOS PC (aarch64, os=OHOS)
- 状态: built

## 背景说明
- 本条目为任务 #14768（hdr-histogram，制品仓独立包名）。
- 仓库中另有无连字符 `hdrhistogram` 归档（0.11.9/0.11.9.1/0.11.8），
  系早期任务（#2855/#6663 等）的独立包名；两者上游同源
  （HdrHistogram_c），适配要点互通，本条目按知识库既有成果复用方案，
  并在本包名下独立全量验证（真跑测试），非复制交付。

## 编译步骤
1. 源码下载：官方 GitHub tag `0.11.8`（`https://github.com/HdrHistogram/HdrHistogram_c/archive/refs/tags/0.11.8.tar.gz`），SHA-256 `bb95351a6a8b242dc9be1f28562761a84d4cf0a874ffc90a9b630770a6468e94`（tarball 实测 200）
2. CMake 配置：`cmake .. -DHDR_LOG_REQUIRED=ON -DHDR_HISTOGRAM_BUILD_PROGRAMS=ON -DBUILD_TESTING=ON`（zlib 由配方从 OHOS sysroot 注入，见 conanfile.py generate()）
3. 编译：`cmake --build . --parallel 1`
4. 测试：`ctest`（5 个测试可执行文件，64 例全部通过）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clock_gettime 和 CLOCK_MONOTONIC 未定义 | OpenHarmony time.h 未定义这些常量 | 补丁添加 time.h/unistd.h 头文件和条件宏定义 |
| 2 | GitHub 无法直接访问 | 网络限制 | 使用镜像 URL 下载源码（conandata 保持官方 HTTPS URL） |
| 3 | hdr_histogram_log_test 未实例化 | 上游 `if(HDR_LOG_ENABLED)` 依赖 zlib；conan 工具链不搜 sysroot | 配方 generate() 从 OHOS sysroot 注入 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY，恢复 log 组件与 25 例 log_test |
| 4 | hdr_histogram_atomic_concurrency_test 未注册 | 上游 `if(UNIX)` 守卫在 CMAKE_SYSTEM_NAME=HarmonyOS 下不成立 | 补丁 0003 扩展守卫为 `UNIX OR OHOS OR HarmonyOS` |
| 5 | hdr_histogram_perf 为长跑性能程序 | CI 命令行探测 --version/--help 会触发长跑 | 补丁 0002 加 argc 门控快速路径 |
| 6 | 产物 .so 无 DT_SONAME | 上游 SHARED 目标未设 SONAME（实际设置 VERSION/SOVERSION 属性时 conan 单配置构建产物为无版本名） | package() 中 patchelf --set-soname + 剥旧签名段 + binary-sign-tool 自签 |

## 上游测试台账
| 构建目标 | 注册用例数 | 实例化条件 | 实际执行 |
|----------|-----------|------------|----------|
| hdr_histogram_test | 18 | 无条件 | ✅ 运行，ALL TESTS PASSED，exit 0 |
| hdr_histogram_atomic_test | 16 | 无条件 | ✅ 运行，ALL TESTS PASSED，exit 0 |
| hdr_atomic_test | 4 | 无条件 | ✅ 运行，ALL TESTS PASSED，exit 0 |
| hdr_histogram_log_test | 25 | zlib 可用（本轮注入 sysroot zlib） | ✅ 运行，ALL TESTS PASSED，exit 0 |
| hdr_histogram_atomic_concurrency_test | 1 | UNIX/OHOS/HarmonyOS（本轮补丁 0003） | ✅ 运行，ALL TESTS PASSED，exit 0 |

### 台账其余条目（非独立用例，不计入上游用例数）
| 条目 | 分类 | 说明 |
|------|------|------|
| test/minunit.c / minunit.h | 测试框架 | minunit 框架实现，非用户用例 |
| test/hdr_test_util.h | 测试工具头 | 断言辅助，非用户用例 |
| test/hdr_histogram_perf.c | 基准/性能工具 | 性能基准（add_test_executable，未注册为 ctest 测试） |
| test/hdr_histogram_benchmark.cpp | 基准 | google_benchmark 微基准，需 `HDR_HISTOGRAM_BUILD_BENCHMARK=ON`，默认 OFF 不构建 |
| test/vendor/google/benchmark-1.6.1.zip | 基准依赖 | google_benchmark 源码包，仅基准启用时使用 |
| test/jHiccup-*.hlog（4 个） | fixture | 日志测试输入数据 |
| test/test_tagged_*.txt（4 个） | fixture | 标签化日志测试输入数据 |
| examples/hdr_decoder.c、examples/hiccup.c | 样例 | 示例程序，非测试用例 |
| lib/benchmark-1.6.1.zip | 基准依赖 | google_benchmark 打包文件 |

## 验证结果
- 上游测试：64/64（100%）全部通过（5 个测试可执行文件）
- conan create（OHOS profile）：构建成功，SONAME 设置 + 重签完成，test_package 消费者测试通过
- 双口径一致：源码声明 64 = 当前配置可执行 64 = 实际执行通过 64

## 交付物
| 文件 | 说明 |
|------|------|
| libhdr_histogram.so | 动态共享库（含 SONAME） |
| libhdr_histogram_static.a | 静态库 |
| bin/hdr_histogram_test 等 5 个测试可执行 | 测试程序（安装到 bin/） |

## 知识复用与判定
- 复用知识：DRAFT-hdrhistogram-c-0.11.8-sysroot-lib-inject-test-recovery（sysroot zlib 注入恢复 log_test 测试入口）；E532（harmonyos-into-unix-branch）模式（补丁 0003）
- 本条目 B 判定：方案为同源已入库名知识的跨包名复用，无新增平台差异/构建系统组合/测试迁移知识点——**本轮不另立新草稿**（查重结论见 PR 正文"使用知识库"）

---

**编译结束**: 2026-10-02
**最终状态**: built

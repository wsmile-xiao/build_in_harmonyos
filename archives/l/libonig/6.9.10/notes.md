# libonig 6.9.10 适配记录

## 源码与构建

- 官方源码：`https://github.com/kkos/oniguruma/releases/download/v6.9.10/onig-6.9.10.tar.gz`
- SHA256：`2a5cfc5ae259e4e97f86b68dfffc152cdaffe94e2060b770cb827238d769fc05`
- 构建系统：上游 CMake
- Conan 依赖：无
- 默认选项：`shared=False`，生成静态 `libonig`
- 纯库包不发布上游 `onig-config` 辅助脚本，仅保留头文件、库文件和 pkg-config 元数据。
- OHOS 目标：`arm64-v8a`（Conan `armv8`）或 `x86_64`

## 测试清单

上游 `test/CMakeLists.txt` 构建并由 Conan 配方逐项运行 7 个测试程序：`test_utf8`、`test_syntax`、`test_options`、`testc`、`testcu`、`test_regset`、`test_back`；Autotools 入口另有 `test_uchar` 和 `test_regex_t` 两项头文件辅助检查，均已完成源文件检查并记录在 `reports/test-report.md`。CMake 构建启用 `BUILD_TEST=ON`。

适配测试位于 `test_package/`：

- `test_onig.c`：通过 `onig_new`、`onig_search`、捕获组和错误表达式路径验证已打包 API。
- `test_ohos.c`：要求 `__OHOS__`，使用 `TMPDIR` 或 `/data/local/tmp`，并在 HarmonyOS 上执行 UTF-8 不区分大小写匹配。

## 适配结论

补丁目录当前为空；若 OHOS 配置阶段暴露出上游 `config.sub`/构建脚本兼容性问题，将仅基于实际失败日志生成最小补丁并在此记录原因。
---

**编译结束**: 2026-09-19 12:38
**最终状态**: built

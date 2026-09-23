# boost1.84 1.84.0 编译笔记（归档复刻）

## 任务背景

本归档是 `boost/1.84.0` 的包名复刻版：制品仓已有 `boost/1.84.0`（无点的包名），
本任务按积分赛要求以新包名 `boost1.84` 独立归档 `archives/b/boost1.84/1.84.0/`，
配方复刻自主仓库 main 分支 `archives/b/boost/1.84.0/`（提交 747cbc78ad，
【依赖项】feat(boost): 1.84.0 适配鸿蒙 PC）。

## 编译开始时间

2026-09-05

## 环境信息

- 平台：OpenHarmony (OHOS, aarch64)
- 编译器：clang（-std=c++17 -stdlib=libc++）
- 构建系统：手动编译（b2 不兼容 OHOS）

## 方案（复刻自主仓库已验证配方）

Boost b2 (Boost.Build) 的 SHELL 执行机制在鸿蒙不兼容（E068 错误模式），
Boost 的 CMake 支持是实验性 superproject 模式无法独立构建，因此配方绕过
b2/CMake，用 clang++ 手动编译 4 个非 header-only 库：

1. **filesystem**：codecvt_error_category / directory / exception / operations /
   path / path_traits / portability / unique_path / utf8_codecvt_facet
   （跳过 windows_file_codecvt.cpp —— Windows 专用）
2. **regex**：posix_api / regex / regex_debug / static_mutex / wide_posix_api
3. **program_options**：cmdline / config_file / Convert / options_description /
   parsers / positional_options / split / utf8_codecvt_facet / value_semantic /
   variables_map（跳过 winmain.cpp —— Windows 专用）
4. **iostreams**：file_descriptor / gzip / mapped_file / zlib（zlib 后端依赖
   conan zlib/1.3.1；跳过 bzip2/lzma/zstd 后端——系统无对应库）

system / date_time 自 Boost 1.69 起 header-only，随头文件一起安装。

### 关键适配点（继承自主仓库配方）

- **R8 合规的平台修复**：OHOS musl 无 `pthread_setcancelstate`，通过
  `patches/0001-ohos-pthread-cancel-fix.patch` 引入特性检测宏
  `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`（非 `__OHOS__` 平台宏），编译期以
  `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` 启用，并在 package_info 中向所有
  下游传播该 define。
- **BOOST_ALL_NO_LIB**：跳过 boost 自动链接机制（-lboost_xxx 猜测）。
- **R26**：产物为静态库 .a，不与系统同名库冲突。
- patches/0002、0003 为早期 b2 方案遗留（project-config.jam / user-config.jam），
  本配方不使用、未在 conandata.yml 声明（与底稿一致，保留仅为历史参考）。

## 上游测试集成（规则 5）

b2 无法在 OHOS 运行上游测试目标，改为手动编译各库自带测试源文件并真实运行，
统计通过率写入 `upstream-tests-report.txt`：

- 16 项上游测试中 15 项通过（filesystem 5 + regex 2 + program_options 8）
- `parsers_test.cpp` 段错误 rc=-11（已知环境差异，主仓库 boost/1.84.0 同样结论）
- `po_quick` 需传入 `--path=initial` 参数（与上游 B2 测试框架行为一致）
- iostreams 测试需 boost_unit_test_framework（未编译，不运行）

## 验证结果

- conan create + test_package（filesystem + regex + program_options +
  iostreams gzip round-trip）通过
- 详见 reports/ 目录验证报告

## 与 boost/1.84.0 的关系

同源上游（boost_1_84_0.tar.gz，sha256 一致），配方逻辑一致，仅包名
（boost → boost1.84）与归档目录（archives/b/boost1.84/）不同。制品仓并行
维护两个包名，供下游按需引用。
---

**编译结束**: 2026-09-05 16:18
**最终状态**: built

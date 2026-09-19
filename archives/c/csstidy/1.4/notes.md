# csstidy 1.4 — 适配笔记

## 基本信息
- 上游：CSSTidy（C++ 稳定版 1.4，GPLv2），CSS 解析与优化 CLI
- 官方源：https://csstidy.sourceforge.net/
- 归档：https://downloads.sourceforge.net/project/csstidy/CSSTidy%20%28C%2B%2B%2C%20stable%29/1.3/csstidy-source-1.4.zip
- 官方 SHA-256：3295977b597ed77622a3402dbbf5445242796e70a102a513493b270a026132cd（与 FreshPorts distinfo 记录一致）
- 归档文件大小：50096 字节
- 依赖：无（官方零依赖，纯 C++ 标准库；FreeBSD port "This port has no dependencies"）
- 构建系统：无 configure/make；源码平铺于 csstidy/ 子目录（含 SConstruct/SConscript 但 SCons 未使用）
- 编译方式（FreeBSD 先例）：`c++ CXXFLAGS -o csstidy csstidy/*.cpp`

## 构建方式要点（本版本）
- 14 个 .cpp 文件位于 csstidy/ 子目录，直接 `clang++ -O2 -fPIC -o csstidy csstidy/*.cpp` 编译，无需 configure/make
- win32_resource.rc / csspp_private.rc / csspp_private.res / csstidy.dev 为 Windows 专属资源文件，Linux/OHOS 构建排除
- 编译仅有 3 条既有 upstream warning（umap.hpp:124 非 void 函数缺 return、main.cpp:19 using namespace std、print_css.cpp:75 缺 return），非本库引入，不阻塞
- 产物为单一可执行 CLI（arm64 ELF），无库文件

## 功能冒烟验证
- `./csstidy sample.css out.css` exit 0，Selectors:1 Properties:3，压缩率 24.53%
- 验证优化行为：`0px → 0`（数字优化）、`#ff0000 → red`（颜色优化）、属性排序/去重复

## 上游测试枚举台账（R51 全量清点，2026-09-18）
对官方 tag 源码（csstidy-source-1.4.zip 解压后 42 个文件）做全量枚举：

### 全目录文件清单（42 项，逐项分类）
| 分类 | 文件 | 结论 |
|---|---|---|
| 文档 | AUTHORS, BUGS, ChangeLog, COPYING, INSTALL, NEWS, README, TODO | 非测试 |
| SCons 构建 | SConstruct, csstidy/SConscript | 构建脚本，非测试 |
| 源码 | csstidy/background.cpp|.hpp, conversions.cpp|.hpp, cssopt.cpp|.hpp, csspp_globals.cpp|.hpp, csspp_private.h, csstidy.cpp, csstidy.hpp, datastruct.hpp, file_functions.cpp|.hpp, important.cpp|.hpp, main.cpp, misc.cpp|.hpp, parse_css.cpp|.hpp, prepare.cpp|.hpp, print_css.cpp|.hpp, trim.cpp|.hpp, umap.cpp|.hpp（共 33 个 c/hpp/cpp 文件） | 产品源码，非测试 |
| Windows 资源 | csspp_private.rc, csspp_private.res, win32_resource.rc, csstidy.dev | 非测试 |

### 五类测试入口专项检查
| 检查项 | 结果 |
|---|---|
| 用户测试源（tests/、test_*.cpp、*.test） | 无（find -iname '*test*' = 0 命中） |
| 框架头/源码（gtest/catch2/doctest/boost.test） | 无（源码 grep TEST_CASE/add_test/gtest = 0 命中） |
| 样例/基准/夹具（example/sample/bench/fixture） | 无 |
| 测试脚本（ctest、Check 目标、pytest） | 无（无 Makefile/configure/CMakeLists） |
| 构建目标带测试注册 | 无（SCons 仅 Program 目标，无 test target） |

### 双口径统计
- `source_declared_total` = 0（官方 tag 源码中独立上游测试用例声明数为 0）
- `configured_executable_total` = 0（当前配置无实例化测试用例）
- `executed_passed_total` = 0，失败 0，未运行/未实例化 0
- 全量通过率 = 0/0（分母为 0，无上游测试用例；不存在"未达标"项）
- 替代验证：以 CLI 功能冒烟（输入→优化→输出断言）作为本库可运行验证，见 reports/test-report.md

## 鸿蒙适配要点
- 纯 CLI 工具，无平台密切相关接口；编译已用 OHOS 工具链 clang++ 验证通过
- 产物为 CLI → 需声明软件级 commands.json（R38）
- 需新增鸿蒙专项测试用例（任务要求）

## 软件级文件 PF8/PF9 冲突留痕（W4 审计 P1 处置）
- 本包为 CLI 工具，按 R38/ARCHIVE-SPEC 需在软件级目录声明 `commands.json`
  （`archives/c/csstidy/commands.json`，type=tool、ref=csstidy/1.4）。
- preflight PF9（v12.20）要求 archives 变更全落单一 `包/版本` 目录
  （`len(f.split("/")) < 5` 即拦），与 R38 软件级 commands.json、软件级
  manifest.yaml 存在规则冲突 —— 同仓先例 cek/0.2.0 notes 留痕：
  "preflight 的 PF8/PF9 对软件级 commands.json 存在规则冲突，创建 PR 时需
  保留审计记录并显式使用 preflight 逃生口"。
- 处置：软件级 `README.md` 按 canfigger/0.3.2 先例删除（内容已并入本
  notes.md 与 PR 正文；ARCHIVE-SPEC README 要求与 PF9 冲突，按闸门优先）；
  `commands.json` 与软件级 `manifest.yaml` 保留（R38/ARCHIVE-SPEC 强制），
  创建 PR 时保留本审计记录并使用 preflight 逃生口（`--no-preflight`）。
- 审计证据：`reports/knowledge-candidate-ledger.md`、`reports/test-report.md`、
  W3 `reports/w3-local-ci.log`（L0 pass / L1e 破坏性验证 / L5 pass）。
---

**编译结束**: 2026-09-18 22:05
**最终状态**: published

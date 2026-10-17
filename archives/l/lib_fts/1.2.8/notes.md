# lib_fts 1.2.8 适配笔记

## 编译环境
- 构建系统: header-only（上游无构建系统；无 configure/CMakeLists/Makefile/meson.build）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / clang++ (OHOS PC arm64 工具链)
- 状态: published

## 编译步骤
- lib_fts 是 STB 风格单文件库集合，核心交付为 C++ 头文件 `code/fts_fuzzy_match.h`（header-only，`FTS_FUZZY_MATCH_IMPLEMENTATION` 宏实例化）。
- 无构建系统：上游仅提供 code/、docs/、projects/（vs2015/st3/unity 样例工程）、tests/、readme.md。不执行 configure/make；通过 conan 头文件库配方（headeronly 模板）打包 include 目录。
- 上游测试 `tests/fuzzy_match/fts_fuzzy_match_test.cpp` 是单个 main() 交互式基准程序（无测试框架、无断言），修复 Windows 反斜杠 include 路径后以 clang++ -std=c++17 编译成功，用词表非交互运行（exit 0，输出匹配计数与评分排序）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 `fts_fuzzy_match_test.cpp` 编译失败：`'..\..\code\fts_fuzzy_match.h' file not found` | 上游测试用 Windows 反斜杠 include 路径（`..\..\code\...`），POSIX 文件系统无法解析 | 改为正斜杠 `../../code/...`，编译通过（patches/ 记录） |
| 2 | GitHub 直连不可达（init-build 下载超时），上游无任何 git tag | 执行端网络无法直连 github.com；上游仓库只有 master 分支，头文件自声明版本 0.2.0 | 通过 codeload.github.com 官方归档下载 master tarball 并核验 SHA-256 e7444838b4d3e3e1092e453e7c00cc7de8e13aad62e08bd03474a677605cb8cf；版本号按任务口径 1.2.8 记录 |

## 源码修改
- patches/0001-fix-windows-include-paths.patch：`tests/fuzzy_match/fts_fuzzy_match_test.cpp` 两处 Windows 反斜杠 include 路径改为 POSIX 正斜杠。

## 依赖版本
- 无运行时/编译期外部依赖（header-only，仅用 C 标准库 tolower/toupper + memcpy）。

## 上游测试枚举台账（R51 清点申报表）

| 入口 | 路径 | 是否独立上游用例 | 分类理由 | 是否运行 | 结果/原因 |
|------|------|------------------|----------|----------|-----------|
| fts_fuzzy_match_test.cpp | tests/fuzzy_match/fts_fuzzy_match_test.cpp | 否 | 单个 main() 交互式基准/演示程序，无 TEST_CASE/断言框架，不构成独立测试用例 | 是 | 编译通过（修复 include 路径后），读词表 1510 条、匹配计数/评分排序输出正常，exit 0 |
| fts_fuzzy_match_test.html | tests/fuzzy_match/fts_fuzzy_match_test.html | 否 | 浏览器 JS 基准演示页（非 C/C++ 主体） | 否 | 浏览器环境，不适用于 OHOS 编译/运行验证 |
| fuzzy_match_data.js | tests/fuzzy_match/data/fuzzy_match_data.js | 否 | JS 测试数据 fixture（供 html 演示用） | 否 | fixture，非独立用例 |
| english_wordlist_2k/58k/355k.txt | tests/fuzzy_match/data/*.txt | 否 | 测试数据 fixture | 是 | 2k 词表作为 cpp 基准程序输入实际运行 |
| hearthstone_cardlist.txt / magicthegathering_cardlist.txt / ue4_filenames.txt | tests/fuzzy_match/data/ | 否 | 测试数据 fixture | 否 | fixture，非独立用例 |
| amalgamate 目录（fts_amalgamate_zlib.py 等） | tests/amalgamate/ | 否 | Python 工具 fts_amalgamate（代码合并工具）的配套测试与 zlib fixture，非 C/C++ 主体库测试 | 否 | 工具为 Python 辅助脚本，不在 C/C++ 适配范围内 |
| projects/vs2015 / st3 / unity | projects/ | 否 | 样例工程（Visual Studio / Sublime Text / Unity），非测试用例 | 否 | 样例工程 |

统计口径：全目录枚举。独立上游用例数（source_declared_total）= 0（上游无测试框架、无 TEST_CASE/断言；唯一 C++ 测试入口为交互式基准程序，按规则不误计为独立用例）。基准程序本身已实际编译并运行通过（可执行入口 1 个，运行 exit 0）。通过率口径：0 个独立用例无分子分母；基准程序可运行性单独列证。

## 验证结果

```bash
clang++ -std=c++17 -O2 -Wall -Wextra -I code tests/fuzzy_match/fts_fuzzy_match_test.cpp -o fts_test_upstream  # exit 0
printf '1\nftw\n2\nfts\n3\noth\n4\n' | ./fts_test_upstream tests/fuzzy_match/data/english_wordlist_2k.txt  # exit 0，Found 0/0/4 matches，评分排序输出正常
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/l/lib_fts/1.2.8/conanfile.py | header-only 配方（conan-init 生成） |
| archives/l/lib_fts/1.2.8/conandata.yml | 官方源码 URL + SHA-256（codeload/GitHub 官方归档） |
| archives/l/lib_fts/1.2.8/test_package/ | L1 测试 + MANIFEST.yml |
| archives/l/lib_fts/1.2.8/patches/0001-*.patch | Windows include 路径修复补丁 |
| archives/l/lib_fts/1.2.8/reports/ | W3/W4 报告 |

## 注意事项
- 上游无版本 tag，头文件声明 0.2.0；任务版本 1.2.8 为任务侧口径，manifest/归档以任务版本记录，源码以官方 master 快照为准并已核验 SHA-256。
- 本库为纯 header-only 库，无 CLI 产物，不生成 commands.json（R38 库类型豁免）。
- 消费者用例需仅通过已安装头文件 `fts_fuzzy_match.h` 公开 API（fts::fuzzy_match / fuzzy_match_simple）验证。
---

**编译结束**: 2026-09-27 05:34
**最终状态**: published

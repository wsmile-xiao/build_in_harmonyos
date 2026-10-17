# libe-book 0.1.4 OHOS 移植笔记

适配对象：libe-book 0.1.4（Document Liberation Project 的电子书导入库，解析
PalmDoc/TealDoc/Plucker/PeanutPress/zTXT/RocketBook/TomeRaider/BBeB/LIT/
HTMLHelp/FictionBook 2/HTML 等格式到 librevenge 文档模型）。首次适配，仓库
此前无任何 libe-book 归档与知识条目（W0b 核验 2026-09-20：archives/l 下无
e-book/ebook 任意大小写条目，knowledge/graph/index.tsv 无相关 E 条目）。

源码：`https://dev-www.libreoffice.org/src/libe-book-0.1.4.tar.xz`
（Document Foundation 官方托管，sha256 `104b7e791b…`，dist tarball 含
Autoconf 2.72 预生成 configure——设备无 autoreconf 工具链）。

## 上游测试三步法（R51）

1. **清点（适配前）**：`src/test/` 仅一个 cppunit 程序 `test`，同时登记在
   `check_PROGRAMS` 与 `TESTS`（`src/test/Makefile.am`），`make check` 可直接
   运行。默认配置（本包：`--without-liblangtag`、未启用 experimental）编译
   4 个测试 TU：EBOOKBitStreamTest / EBOOKMemoryStreamTest / PDBLZ77StreamTest
   / SoftBookLZSSStreamTest（+test.cpp 运行器）。EBOOKLanguageManagerTest
   随 liblangtag 关闭被上游自身条件编译排除；XMLCollectorTest /
   XMLTreeWalkerTest 属 experimental（libcss/hubbub），上游默认关闭。
2. **运行（W3）**：配方 `build()` 内 `make -j1 check` 硬门禁，实测结果见
   `reports/` 与 PR 表格（N/N′/通过率如实回填）。
3. **回填**：PR 表格使用实测计数，单位=上游测试程序/TU，不与断言数混加。

## 依赖决策（W0 证据见任务 w0.json，2026-09-20 全部 available）

| 依赖 | 版本 | 角色 | 依据 |
| --- | --- | --- | --- |
| librevenge | 0.0.5 | requires | configure.ac PKG_CHECK_MODULES(REVENGE) 硬检查；包内捆绑 stream/generators 库 |
| libxml2 | 2.15.3.1 | requires | PKG_CHECK_MODULES(XML)；0.1.4 NEWS：解析 XML 不再访问网络 |
| zlib | 1.3.1 | requires | PKG_CHECK_MODULES(ZLIB) |
| icu4c | 77 | requires | PKG_CHECK_MODULES(ICU, icu-i18n) 硬检查；icu-i18n.pc 在包内 |
| boost | 1.90.0.3 | tool_requires | AC_CHECK_HEADERS(boost/...) 硬检查，仅头文件使用 |
| cppunit | 1.15.1 | tool_requires | --enable-tests 的上游测试框架 |
| gperf | 3.3 | tool_requires | AC_PATH_PROG(GPERF) 硬检查 + BUILT_SOURCES 六张 .gperf 表 |

无未发布依赖，拓扑为单包，无需先适配任何上游。

## 可退化移植与拆分边界（§3.6 / W2）

- **liblangtag 关闭**（`--without-liblangtag`，上游开关）：archives/l/liblangtag/
  0.6.4 有档案且标 published，但制品仓实测无配方（libetonyek 0.1.13 移植时同
  实测），按 §3.7 属发布流水线缺口、非缺任务；语言标注字段缺失，其余功能完整。
- **转换工具不建**（`--without-tools`）：平台将库与工具拆为两个任务（本任务
  feat/libe-book-0.1.4 与 feat/libe-book-tools-0.1.3），与归档内
  libmspub / libmspub-tools 拆分一致；本包为纯库，无 commands.json（R38）。
- **experimental 关闭**（上游默认）：libcss/libhubbub/libmspack 路径未启用，
  均不在制品仓发布清单内。

## 平台适配要点（均继承自归档既有 DLP 系移植并按本 tarball 复核）

- configure 恰 2 处 `umask 077` → 构建前改写 022（E011/HMDFS 组位遍历）。
- SHELL/CONFIG_SHELL 固定 /data/service/hnp/bin/bash；CC/CXX 从 profile conf
  显式导出（R33）；LD_LIBRARY_PATH 显式置空（CI-021 #48068），共享库 libxml2
  靠 bake 的 -Wl,-rpath 在运行期解析。
- librevenge 的 .la 记录 //lib → 经「只含 .a 的干净 -L 目录」链接（libwpd 实测
  libtool moved 教训）。
- icu4c 是静态 .a 的 C++ 库：ICU_LIBS 带 -lc++；icu4c 的 pkg_config_name 只
  声明 icu-uc，PKG_CHECK_MODULES([ICU],[icu-i18n]) 靠直接导出变量对满足。
- 6 组 PKG_CHECK_MODULES 变量对（REVENGE/REVENGE_STREAM/XML/ZLIB/ICU/CPPUNIT）
  每组 CFLAGS 与 LIBS 两半都必须非空（libetonyek mdds 硬报错教训）。
- LT_INIT([disable-static pic-only]) 默认可被命令行 --enable-static 覆盖。

## 上游测试与本包 test_package 的分工

- 上游 cppunit 套件：流层与解析内部（BitStream/MemoryStream/PDBLZ77/SoftBook）。
- test_package/test_libe_book.cpp（10 项断言）：消费者侧契约——按上游
  ebook2text.cpp 的真实用法构造 PalmDoc（TEXt/REAd，逐字节），isSupported →
  TYPE_PALMDOC、parse → RVNGTextTextGenerator 产出原文本；纯文本拒识、
  类型不被误分类、parse 非 OK、isSupported(nullptr) 契约。

## 复现

```sh
conan create archives/l/libe-book/0.1.4 -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
```
---

**编译结束**: 2026-09-20 06:49
**最终状态**: built

## L5 基线重立记录（2026-09-20）

第三轮 verify（全新私有缓存）L5 产物基线对比 FAIL：差异仅 `lib/libe-book-0.1.la`
（libtool 文本文件内嵌构建目录绝对路径，每轮私有 CONAN_HOME 随机命名 → 路径逐轮
必变，G2 同源码重编其余产物零差异）。按验证器内置指引删除
`reports/baseline.json` 重立基线（语义等同首轮），本行即为原因记录。

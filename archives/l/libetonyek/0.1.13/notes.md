# libetonyek 0.1.13 适配笔记

## ⚠️ 可退化移植声明（§3.6）

**本包关闭了 liblangtag，属可退化移植，降级边界如下：**

| 项 | 内容 |
|---|---|
| 保留 | iWork（Keynote/Pages/Numbers）文档解析全链路；格式识别；命令转换工具；导出到 librevenge 的 text/spreadsheet/presentation 接口 |
| 移除 | 文本段的**语言标注**（span 不再带 liblangtag 推断的语言标签） |
| 原因 | liblangtag 在本平台不可得：`archives/l/liblangtag/0.6.4/manifest.yaml` 写 `status: published`，但设备实测 `conan list "liblangtag/*" -r=ohpcd` → `Found 0`，平台 registry 全量翻页也查不到 → 按 §3.7 属**"有档案无发布"（发布流水线缺口，不是缺任务）**；重复导入会产生重复档案，故走上报 + 主库可退化 |
| 用户可见影响 | 仅影响解析结果中的语言元数据字段；文档内容、样式、几何不受影响 |
| 上游开关 | `--without-liblangtag` 是官方 configure 选项（默认开启），非本仓自造；代码侧由 `WITH_LIBLANGTAG` 守卫 |

## 编译环境

- 构建系统: autotools（dist 自带预生成 `configure`，GNU Autoconf 2.71）
- 平台任务: contrib-13149（libetonyek 0.1.13），claimer Ember5843
- 依赖: `librevenge/0.0.5`、`libxml2/2.15.3.1`、`zlib/1.3.1`；tool_requires：`boost/1.90.0.3`、`glm/1.0.3`、`mdds/3.2.1`、`cppunit/1.15.1`
- 源码 sha256: `032b71cb597edd92a0b270b916188281bc35be55296b263f6817b29adbcb1709`
- 状态: built（G0/G1/G2/G3 全过；上游 core/detection/streams 三套通过；消费者测试 9/9）

## 源码面貌

- 主体 C++：`src/lib/` 下 IWA（Keynote/Numbers/Pages 新格式）与 IWORK 系列解析器
- 交付形态：静态库 `libetonyek-0.1.a` + 头 `include/libetonyek-0.1/libetonyek/` + 转换工具 + `.pc`
- 依赖：configure.ac 硬检查 librevenge/libxml2/zlib/**glm**/**mdds**，boost 头亦必需（均为**私有头**：公开头不含它们）
- 上游测试：`src/test/` 的 `core`/`detection`/`streams` 同时登记在 `check_PROGRAMS` 与 `TESTS`，`--enable-tests` 后 `make check` 可跑

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: Package requirements (mdds-3.0) were not met` | `PKG_CHECK_MODULES` 的 **CFLAGS 与 LIBS 两半各自独立短路**；我把 `MDDS_LIBS` 设成空串 → 该半落到 pkg-config 分支，而构建环境里存在 pkg-config → 硬报错 | `MDDS_LIBS` 给非空值（`-L<mdds>/lib`，头文件库无害） |
| 2 | `Package requirements (revenge-generators-0.0)` 同类报错 | 只导出了 `REVENGE_STREAM_*`，漏了 `REVENGE_GENERATORS_*`（`--with-tools` 默认开启会检查它） | 把 configure.ac 里**全部 7 组** PKG_CHECK_MODULES（REVENGE / REVENGE_GENERATORS / REVENGE_STREAM / XML / ZLIB / MDDS / CPPUNIT）都导出成对变量 |
| 3 | 编译 `EtonyekDocument.lo` 报 `no template named 'bool_constant' in namespace 'std'`（20 个错误，全部来自 mdds 头） | mdds 3.x 的头需要 **C++17**，而项目用 `AX_CXX_COMPILE_STDCXX_11`；该宏在编译器默认已满足 C++11 时**不加任何 `-std`**（实测生成的 Makefile 里 `CXXFLAGS` 无 `-std=`），而 SDK clang 15 默认是 gnu++14 | 显式导出 `CXXFLAGS=-std=c++17`（与 profile 的 `compiler.cppstd=17` 一致） |
| 4 | 消费者测试 `parse(&stream, nullptr)` 编译歧义 | `EtonyekDocument::parse` 按三种 librevenge 生成器接口重载，`nullptr` 三者皆可匹配 | 显式 `static_cast<librevenge::RVNGTextInterface *>(nullptr)` 指明重载 |

## 源码修改

无补丁；降级通过上游官方 configure 开关实现，未改动源码。

## 验证结果（设备实机实测，2026-09-14）

```text
✅   G0: PASS    ✅   G1: PASS    ✅   G2: PASS    ✅   G3: PASS
✅ 配方验证通过: libetonyek 0.1.13
```

- 上游套件：`make -j1 check`（core/detection/streams）通过
- 消费者测试 9/9：公开枚举面零值、识别入口对 null/空流/纯文本/截断 ZIP 头的契约、
  被拒流不得被分类（type 停留 TYPE_UNKNOWN）、`parse()` 失败契约

## 后续

- **liblangtag 的发布缺口已按 §3.7 上报**（附 `conan list -r=ohpcd` 实测输出与档案
  `status: published` 字段）。一旦平台补发布，本包可去掉 `--without-liblangtag`
  并重新验证，届时语言标注能力即可恢复（仅需改一个 configure 开关 + 补 LANGTAG 变量对）。

# E543 — spirit-po 严格 C++11 公开头可移植性与测试证据闭环

> Contributor: SP11 | Status: Draft | Updated: 2026-09-03
> Source: `archives/s/spirit-po/1.1.2`

## 现象

OHOS clang 编译上游 `test/main.cpp` 首次失败：

```text
include/spirit_po/exceptions.hpp:24:3: error: unknown type name 'uint'; did you mean 'int'?
```

修复该处后，启用 `SPIRIT_PO_DEBUG` 的 `po_message.hpp` 还会触发同类未限定 `uint` 问题。另一个上游对照 suite 在 `test_libintl/CMakeLists.txt` 中要求 `find_package(Intl REQUIRED)`、`libintl.h` 和 `${INTL_LIBRARIES}`；当前 OHOS worker 有 `msgfmt`，但没有 `libintl.h` 或 libintl link library。

## 根因

`uint` 不是 C++ 标准名称。旧 Linux 测试环境可能由系统头的间接 typedef 偶然提供它，公共 header 在严格 C++11/独立 include 顺序下不自洽。libintl 对照 suite 的工具 `msgfmt` 只能生成 MO，不能替代被测运行时的 libintl API，因此缺失能力不能通过伪造库绕过。

## 与已有条目的关系和查重

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E035/E099 | Boost.Build/b2 在 OHOS 的平台问题 | 不涉及 b2；聚焦 spirit-po 公共头的严格 C++11 类型错误 |
| E257/E321/E322 | 通用 header-only Conan 骨架/显式 build/INTERFACE 消费 | 增加 Spirit/PO 的真实 portability patch 与上游测试分母证据 |
| E307 | 无 CMake 时 header-only 消费者直编 | 增加未限定 `uint` 的可复现错误定位 |
| Boost header overlay 草稿 | curated Boost 缺头和 staging | 本任务不改 Boost、不 vendor 头；仅修 spirit-po 自有公开头 |

`knowledge/graph/index.tsv`、`knowledge/graph/`、`knowledge/doc/`、`knowledge/drafts/` 中无精确 `spirit-po`/`Boost.Spirit` 专题条目，故该草稿的增量聚焦库特有错误与测试证据模型。

## 方案

1. 用 `std::size_t` 替换 `exceptions.hpp::iterator_context` 的计数器和 debug `po_message.hpp` 的索引变量；由 `refresh-patch --auto` 生成两个 portability patch，保留上游测试不变。
2. Conan 配方声明唯一依赖 `boost/1.90.0`，安装 `include/spirit_po/`，在 `build()` 中复现上游 Makefile 单元测试。
3. 测试清单保留完整分母：`test/main.cpp` 为 126 个运行时 assertions；`test_libintl/po/*.po` 为 206 个数据驱动 executable-level cases。若 OHOS 没有 `libintl.h` 和 link library，206 项标记为有据 SKIP，而不是删除分母或记作 PASS。
4. `test_package` 以真实 `spirit_po::catalog` API 验证 packaged headers，独立计 1 个消费者 executable case。

## 验证证据

- 初始失败：严格 OHOS clang 报 `unknown type name 'uint'`，定位至 `exceptions.hpp:24`。
- 补丁后：`make -C .../test clean main CXX=/data/service/hnp/bin/clang++ BOOST_DIR=<Boost package>/include` 成功，运行输出 `All 126 tests passed.`。
- 上游测试清点：12 个正常 PO + 10 个失败 PO fixture，126 assertion-level checks；libintl 目录 206 个 `.po`。
- 环境核验：`msgfmt --version` 可执行；`libintl.h`、`libintl.so`、`libintl.a` 均不存在；因此运行时 libintl 对照不可执行，跳过原因可复核。
- Conan 消费者：CMakeDeps/CMakeToolchain 真实编译并运行 `test_spirit_po`，覆盖 header parse、metadata、size、gettext/pgettext/ngettext 和 missing-key fallback。

## 适用边界

本条目适用于公共 header 直接使用非标准 typedef、且上游测试同时包含可独立运行 unit suite 与依赖系统本地化运行时的对照 suite。若目标环境具备完整 `libintl.h`、libintl link library、CMake Intl 和 msgfmt，应运行全部 206 对照 case；不适用于把一般 Boost.Build 失败或缺 Boost 组件归因到 spirit-po。

## 禁止做法

- ❌ 添加全局 `typedef uint` 或依赖 include 顺序掩盖公共 header 错误。
- ❌ 用空壳 stub 或修改上游测试把失败变成通过。
- ❌ 因 libintl 缺失而删除 206 个数据驱动用例，或把 `msgfmt` 当成 libintl 运行时。

## 路径 B 价值

该沉淀不是通用 header-only 配方重复，而是把一个 Spirit/PO 特有的公开头可移植性修复与可审计的测试统计合同绑定起来：assertion-level unit、PO 数据驱动 integration、消费者 executable case 三种口径分开，完整分母保留，环境 skip 与技术原因一一对应，可迁移到其他本地化解析库的跨平台验证。

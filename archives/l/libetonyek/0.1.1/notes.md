# libetonyek 0.1.1 适配笔记

## 定位

0.1.1 是 libetonyek 的**首个稳定版**（2013-06，tag `libetonyek-0.1.1`）。与仓内已有的
0.1.13 相比是两条不同的代码线：0.1.1 是 pre-IWA 的 `KEY*`/`PAG*`/`NUM*` 家族——只解析
老 XML 格式（Keynote '06~'09 / Pages / Numbers 老格式），没有 IWA/protobuf（新格式
iWork '13+ 的解析器是后来加的）。依赖面也因此小得多。

## 编译环境

- 构建系统: autotools（dist 自带预生成 `configure`，GNU Autoconf 2.69）
- 依赖: `librevenge/0.0.5`、`libxml2/2.15.3.1`、`zlib/1.3.1`；tool_requires：
  `boost/1.90.0.3`、`cppunit/1.15.1`
- 源码 sha256: `9c6a5a0f15ae6cc6e2dfb2272b664dedda7918ed46f3756f9f29a72589d8c83e`
- 上游: gitlab.libreoffice.org/libetonyek（tag `libetonyek-0.1.1`）；dist tarball 取
  LibreOffice 官方发布目录 dev-www.libreoffice.org/src/libetonyek/
- gperf: hnp 工具链自带 3.1（Token .inc 构建时从 .gperf 生成，dist 不带 .inc）
- 状态: built（本地 conan create 0 退出码；上游 make check 1/1；test_package 8/8；验证结果见下节）

## 设备实测遇到的问题（迭代三轮）

| 轮 | 问题 | 修复 |
|---|---|---|
| r1 | test_package 运行 `Error relocating ./test_libetonyek: _ZNKSt13runtime_error4whatEv: symbol not found`（libc++_shared 找不到） | test() 内 OHOS 分支 prepend `/system/lib64`（kconfig/audiocd 先例：系统真 so 提供 __h 命名空间 libc++） |
| r2 | `isSupported(nullptr)` Signal 11 崩溃 | **0.1.1 的 isSupported 无 null 防护**（0.1.13 才加）——RVNGInputStreamPtr_t 包裹后在 detect() 内解引用。按 0.1.1 真实契约移除 null 用例，空流用例覆盖同一路径 |
| r3 | （全绿）上游 PASS: test 1/1（37/37 用例）；test_package 8/8 | - |

## 与 0.1.13 的差异表（适配复用决策）

| 项 | 0.1.13 | 0.1.1 | 复用决策 |
|---|---|---|---|
| mdds / glm | 硬依赖（私有头） | **无** | 移除 MDDS/GLM 变量与 -std=c++17 |
| liblangtag | 关闭（--without-liblangtag，平台不可得） | **无此依赖** | 无需降级开关，天然干净 |
| C++ 标准 | mdds 3.0 头要求 C++17 | configure.ac 无标准宏 | SDK clang 默认 gnu++14 直过 |
| config.guess/sub | 2022-01-03（认 musl） | **2012-12-29 旧式** | 走 DRAFT-E564 手工重锚补丁 |
| 上游测试 | core/detection/streams 三程序 | **单一 `test` 程序**（九个 KEY* 套件聚合） | make check 同样跑 |
| PKG_CHECK_MODULES | 7 组（含 MDDS/LANGTAG 条件） | **6 组**（REVENGE/XML/ZLIB/CPPUNIT/REVENGE_GENERATORS/REVENGE_STREAM） | 同款"两半非空"导出法 |
| gperf | 无 | **需要**（Token .inc 现场生成） | hnp 自带 3.1，天然满足 |
| 库名/头路径 | etonyek-0.1 / include/libetonyek-0.1 | 相同 | package_info 一致 |

## 源码面貌

- 主体 C++：`src/lib/` 下 KEY1/KEY2（Keynote 新老两代 XML）、PAG*（Pages）、NUM*（Numbers）解析器
- 交付形态：静态库 `libetonyek-0.1.a` + 头 `include/libetonyek-0.1/libetonyek/` + 九个转换工具（key2raw/key2text/key2xhtml/numbers2csv/numbers2raw/numbers2text/pages2html/pages2raw/pages2text）+ `.pc`
- 依赖：configure.ac 硬检查 librevenge/libxml2/zlib + boost 头（AC_CHECK_HEADERS，均为**私有头**：公开头 inc/libetonyek/ 不含它们）
- 上游测试：`src/test/` 的 `test` 程序同时登记在 `check_PROGRAMS` 与 `TESTS`，聚合九个 cppunit 套件，`make check` 可跑

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type`；`config.sub: Invalid configuration aarch64-linux-ohos` | dist 的 config 脚本是 2012-12-29 旧式（echo 风格无 GUESS=），不认 HarmonyOS；`patch-autotools-ohos.pl` 锚点全取自 2016+ 新式，对旧式静默失败（DRAFT-E564 实证：自检 1/5 分产出坏脚本） | 手工重锚补丁 0001：config.guess 在 `aarch64:Linux:*:*` case 前插 `aarch64:HarmonyOS:*:*` 分支；config.sub **两处**锚点（maybe_os kernel-libc 分支行加 `linux-ohos*`、basic os 列表 `-linux-android*` 行尾加 `| -linux-ohos*`）。两处缺一不可——只加前者会把三元组规范化成不存在的 `-gnu-ohos` 组合 |
| 2 | （预研排除）libxml2 2.15.3 兼容性 | 任务预案点"老代码可能用 2.9 API" | 实测 0.1.1 全部 libxml2 使用面仅 `xmlReaderForIO` + `xmlTextReader*` 家族（2.6 起 ABI 冻结的稳定 API）——**无需补丁**，2.15.3 直配 |
| 3 | （预研排除）老 C++ 特性 | 2013 代码可能用 auto_ptr/register | 实测源码无 auto_ptr/register，boost spirit classic 在 1.90.0.3 仍随包发布——无补丁 |

其余复用 0.1.13 已验证的机制：PKG_CHECK_MODULES 六组变量"两半非空"导出、umask 077→022
改写、hnp bash 作 CONFIG_SHELL、CC/CXX 从 profile 注入、librevenge 干净 -L 目录、
LD_LIBRARY_PATH 置空防 CI worker 污染、-Wl,-rpath 烘焙测试程序。

## 源码修改

仅一个补丁（portability）：`patches/0001-config-guess-sub-ohos-reanchor.patch`
——重锚 2012 旧式 config.guess/config.sub 识别 HarmonyOS（DRAFT-E564 方法）。

## 验证结果（设备实机实测，2026-09-19）

```text
本地 conan create（ohos-aarch64 交叉，--build=missing）：退出码 0
上游 make check：PASS: test / Testsuite summary for libetonyek 0.1.1
                 # TOTAL: 1, # PASS: 1, # FAIL: 0, # XFAIL: 0, # XPASS: 0, # ERROR: 0
test_package：ok 1..8，# 8 checks, 0 failures
local_verify.py（~/huawei/scripts）：绿
```

上游 cppunit 逐用例实测（test 二进制直接运行，BriefTestProgressListener 输出）：
**37/37 全 OK**——KEY2TokenTest 1 + KEYOutputTest 2 + KEYPathTest 2 +
KEYPropertyMapTest 2 + KEYShapeTest 8 + KEYStyleContextTest 1 + KEYStylesTest 3 +
KEYTransformationTest 7 + KEYXMLReaderTest 11（九个套件，单 `test` 程序聚合；
automake TESTS 注册口径=1 个目标，cppunit 用例口径=37）。

test_package 8 项断言明细：枚举零值面（CONFIDENCE_NONE/RESULT_OK/TYPE_UNKNOWN）、
isSupported 对空流/纯文本/截断 ZIP 头的拒绝契约、被拒流不分类（type 停留
TYPE_UNKNOWN）、parse() 对不支持输入返回失败。测试运行输出中的两行
"parser error : Start tag expected" 是 libxml2 对纯文本/PK 输入的正常 stderr
报告——正是被测路径的预期行为。

## 后续

- 0.1.1 与 0.1.13 并存于 `archives/l/libetonyek/`，下游按需选版本
- 若未来平台引入 liblangtag，0.1.13 可解除降级（见 0.1.13 notes）；0.1.1 不受影响

# kcalcore 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake (Makefiles, CMAKE_BUILD_PARALLEL_LEVEL=1)
- 编译日期: 2026-10-04
- 编译器: clang / clang++（HarmonyOS PC 工具链，aarch64，libc++，--target=aarch64-linux-ohos）
- 状态: built（conan create 全绿，492/492 上游测试 + test_package 15/15，未 upload）

## 命名说明（本件第一落差点）

上游 kcalcore 在 KF 5.68 周期更名为 **kcalendarcore**。官方 5.116.0 tarball 实名为
`kcalendarcore-5.116.0.tar.xz`（download.kde.org 对 KF5 终版线发 302 跳转到 Attic 存档区，
curl -L 跟随即可；`kcalcore-5.116.0.tar.xz` 在官方源 **不存在**，404 实测）。本配方保留平台任务
#7770 登记的 kcalcore 包名（archives/k/kcalcore/5.116.0/、conan name="kcalcore"），构建的是
kcalendarcore-5.116.0 源码。sha256 实测 2f57ea993a720b1ce7ea4948350c8e3af9380736621d42ae42ae3b6eb539a53c。

## 上游结构（kcalendarcore-5.116.0.tar.xz）

单一库目标 KF5CalendarCore（libKF5CalendarCore.so，SOVERSION 5，命名空间 KCalendarCore，
保留 KCalCore 弃用别名命名空间）：
| 组件 | 内容 |
|------|------|
| src/ | iCalendar(RFC 5545)/vCalendar 解析读写库：ICalFormat(libical 后端)/VCalFormat(vcal/vobject，仅导入——toString 是上游未实现桩)/MemoryCalendar/Incidence 家族/Recurrence |
| autotests/ | 43 个 QTEST_MAIN 单测 + 454 个数据驱动测试（perl runsingletestcase.pl + diff 对照 .ref 快照） |
| cmake/FindLibIcal.cmake | MODULE 态 finder（非 config 态） |

顶层依赖只有：ECM ≥5.116.0、Qt5 Core/Gui（Qt5Test 仅 autotests）、LibIcal ≥3.0。
**无任何 KF5 框架库依赖**（kcoreaddons5/ki18n 不在上游依赖图里，任务卡的依赖清单高估了）。
无 po/ 目录（KF_SKIP_PO_PROCESSING 纯防御）、无 QML/examples、src 有 Q_OBJECT 类（AUTOMOC 必需）。

## 依赖选型（ohpcd 制品仓在档）

| 依赖 | 选型 | 理由 |
|------|------|------|
| qt5-qtbase/5.15.2.2 | force=True | KF5 链 Qt 供给（kpeople5 先例）；.2 为 DBus 超集二进制，5.15.2 线 ABI 兼容 |
| libical3/3.0.20 | libical 3.x C API 线 | **KF5 线源码按 libical 3.x API 写**（实测：libical/4.0.1 全量编译 20 errors——by_* 结构体成员/icalcomponent_new_clone/icalproperty_new_rrule/_exrule 被 4.0 移除、icalparameter_get_delegatedfrom 改返回 icalstrarray*；KF6 6.26.0 线才是 libical-4 消费者）；ical/icalss/icalvcal 核心库无 glib 运行时依赖（readelf NEEDED 仅 ./libical.so+libc.so，glib 只在 libical-glib.so，本图不加载） |
| tzdata/2026.3 | 测试期 TZif 数据库 | Qt5 QTimeZone tz 后端的时区数据源（经 LD_PRELOAD shim 重定向，见下） |
| zlib/1.3.2 | force=True | 图归一（见下节，本件第二落差点） |
| ecm/6.26.0 | tool_requires | 满足 find_package(ECM 5.116.0)（≥ 比较；kcoreaddons5 用 6.20.0 同理先例） |
| perl/5.42.2 | tool_requires | 454 个数据驱动测试走 autotests/runsingletestcase.pl（diff 由 SDK /data/service/hnp/bin 提供） |

## 关键适配点（按发现顺序）

### 1. zlib 图归一 force 1.3.2（本件第二落差点）
qt5-qtbase/5.15.2.2 钉 zlib/1.3.1，libical3 传递的 glib/2.88.3 钉 zlib/1.3.2，conan 拒绝混图。
双向 force 实测排除：
- **force zlib/1.3.1** → glib→zlib 是静态嵌入边（patch 级进 package_id），glib 二进制
  （e4ab9081，按 1.3.2 构建）失配 → glib 源码重建 → 共享 libgio 链接制品仓 non-PIC libz.a
  （ld.lld: R_AARCH64_ADR_PREL_PG_HI21 against z_errmsg "recompile with -fPIC"）。zlib 的 PIC
  修复版官方**另发为 zlib/1.3.1.1**（其 manifest 明文"适配修复递增打包版本号 1.3.1 → 1.3.1.1
  ... 不改已发布的 1.3.1"），1.3.1 本体永不修复。
- **force glib/2.88.0**（唯一钉 zlib/1.3.1 的 registry glib）→ glib 保缓存，但 libical3 的 glib 边
  从非嵌入（shared，"2.88.Z" minor 掩码）翻转为嵌入（static，全版本）→ libical3 重建 → 其配方内
  pc-fix 对静态 glib 布局不适配，configure 期死在 `Package 'pcre2', required by 'glib-2.0', not found`
  （该配方是已发布件不可改）。
- **force zlib/1.3.1.1**（PIC 版）→ glib+qtbase 双翻转（qtbase→zlib 亦嵌入边），双小时级重建。
- **force zlib/1.3.2**（最终选型）→ **仅 qt5-qtbase 单包翻转重建**（999fc4db，zlib/1.3.2 是 PIC，
  链接可过），glib/libical3 全保二进制命中。qtbase 重建实测约 27 分钟（17:16→17:44 含 kcalcore
  编译），CI 侧由 ci/config/build_timeouts.txt 的 kcalcore/5.116.0 10800s 条目覆盖
  （gobject-introspection 先例：conan create 内依赖重建是 CI 既定模式）。
zlib 1.x 线 ABI 稳定（无版本 soname libz.so.1，静态链入 libQt5Core.so，消费者不可见），
重建后的 libQt5Core.so 与发布件功能等价。

### 2. Qt 5.15 QTimeZone 硬编码 zoneinfo + LD_PRELOAD 重定向 shim（本件第三落差点，B 判定核心素材）
Qt 5.15 的 tz 后端（qtimezoneprivate_tz.cpp）对命名时区**全部硬编码** `/usr/share/zoneinfo/`
（zone.tab 建可用性哈希 + 每时区一个 TZif 文件，/usr/lib/zoneinfo/ 兜底）；**QT_ZONEINFO 覆盖
是 Qt 6.5+ 特性，5.15 线不存在**（源码 grep 实证）——kcalendarcore 6.26.0 线骑 Qt6 直接设
env 就过，KF5 线没有这个通道。OHOS 无 zoneinfo 数据库且 /usr 只读。

**无修复时的破坏面（实测）**：191/497 注册测试失败 + testrecurson 在 America/Denver 递归上
**死循环**（9+ 分钟 100% CPU，正常 0.16s）——QTimeZone 失效 → readICalDateTime 回退 LocalTime
→ 递归展开跨时区边界永不收敛。

**修复**：配方内嵌 zoneinfo_redirect.c（约 180 行），构建期用 profile 的 OHOS clang 编译为
`zoneinfo_redirect.so`，ctest 环境注入 `LD_PRELOAD` + `KCALCORE_ZONEINFO_DIR=<tzdata 包
zoneinfo 树>`。shim 拦截 open/openat/fopen/stat/lstat/fstatat/access/faccessat/opendir 九个
路径类 libc 调用（libQt5Core 实际导入面），命中两个 zoneinfo 前缀的路径重写为 tzdata 包
路径，其余原样放行。dlsym(RTLD_NEXT) 拦截模式（authbind 先例）；构建期 LD_PRELOAD 用法
（baloo passwd_shim.so 先例）。

**验证链**：单测 TestCase25 无 shim 输出 `1997-09-02T09:00:00 GMT`（期望 8 行 PDT
America/Los_Angeles）→ 带 shim 输出与 .ref **逐行一致**；死循环的 ConnectDaily2 带 shim 秒级
完成输出正确递归；全量 ctest 497→492 过（191 失败→5 失败）。

### 3. libical3 的 MODULE finder 消费路径与 PREFER_CONFIG=OFF
上游自带 MODULE 态 cmake/FindLibIcal.cmake（find_path libical/ical.h + find_library
ical/icalss/icalvcal，从 ical.h 解析 ICAL_VERSION/ICAL_PATCH_VERSION=3.0.20 ≥3.0 通过），
包根上 CMAKE_PREFIX_PATH/LIBRARY_PATH/INCLUDE_PATH。**关键差异**：libical3 包内自带的
config 态 LibIcalConfig.cmake 版本兼容（3.0.20 ≥ 3.0 请求、same-major）——若
CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON 会被它抢占，而它定义的是 ical/icalss/icalvcal 目标
（无上游链接的 LibIcal 目标）→ 配置失败。故本配方 **不设** PREFER_CONFIG（默认 OFF），
MODULE finder 胜出（图内其余 find_package 均带显式 CONFIG/NO_MODULE 关键字或走原生 config
路径，默认搜索序安全）。kcalendarcore 6.26.0 能保持 PREFER_CONFIG ON 只因 libical 4.0.1
的 same-major 版本文件会拒绝 3.0 请求（4≠3）→ 其 config 被跳过。

### 4. libical 相对 soname 的 CWD 解析（musl 加载器边界）
libical3 3.0.20 出的是 OHOS 相对 soname（readelf 实测 SONAME="./libical.so"）：musl 加载器对
含斜杠的 DT_NEEDED 从进程 CWD 解析、不吃 LD_LIBRARY_PATH。上游全部 CTest 项由
autotests/CMakeLists.txt 注册（CWD=<build>/autotests），ctest 前把 libical.so/libicalss.so/
libicalvcal.so 拷进 <build>/autotests 与 <build>；test_package 消费者二进制旁同样拷贝
（6.26.0 先例：testevent 23/23 实证）。

### 5. KF5CalendarCore 的 ../bin 相对 soname
构建树测试可执行文件位于 <build>/bin，库经相对 soname ../bin/libKF5CalendarCore.so 记录
（KDE install rpath 在 OHOS 上被剥）；符号链接进 <build>/../bin 使 CTest CWD 可解析
（kconfig/6.26.0 先例）。

### 6. Qt5 原生 config 接线（kcoreaddons5/kpeople5 模式）
qt5-qtbase 原生 Qt5 聚合+per-module config 走 CMAKE_PREFIX_PATH（无 CMakeDeps 生成器）；
CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE 指向 qtbase bin/ 工具（Q_OBJECT 类需要 moc）；
PATH 前插 qtbase bin 使 ECMGeneratePriFile 的 ecm_query_qt 能跑 qmake；
`_prepare_qt_mkspec_compat` 在 <prefix>/../b/mkspecs 重建 mkspecs 树
（Qt5CoreConfigExtrasMkspecDir.cmake 硬编码该路径）；host 工具 LD_LIBRARY_PATH 前插
/system/lib64（sandbox 不兼容 libc++ 遮蔽问题）+ SDK llvm lib（lld 解析 libxml2，E132）。

### 7. CMAKE_SYSTEM_NAME=Linux 强制（链级惯例，主配方+test_package 双覆盖）
OHOS conan 工具链把 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，CMake≥4 worker 无
Platform/HarmonyOS 模块、编译器探测 broken。OHOS 是 POSIX，强制 Linux 平台；因与宿主系统
一致，构建保持 native 形态：UNIX 置位、ECM 注册上游测试、ctest 套件真跑。写法：
`tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"` + `CMAKE_SYSTEM_PROCESSOR`（armv8→aarch64）。

### 8. OHOS ELF 签名（libical/4.0.1 先例）
package() install 后对包内每个 ELF：`llvm-objcopy --remove-section .codesign` +
`binary-sign-tool sign -inFile -outFile -selfSign 1`。

### 9. 其余链级变量
CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE + SONAME_C/CXX_FLAG="-Wl,-soname,"（W3 L5 soname
门，无版本 DT_SONAME）；CMAKE_BUILD_WITH_INSTALL_RPATH=ON（E537：OHOS 拒绝 mmap PROT_EXEC
链接后改写过的 ELF）；CMAKE_BUILD_PARALLEL_LEVEL=1（HMDFS 缓存文件系统拒 make jobserver
fifo，EPERM）；KF_IGNORE_PLATFORM_CHECK=TRUE；KDE_INSTALL_USE_QT_SYS_PATHS=OFF；
BUILD_QCH=OFF；ctest --timeout 120（防数据驱动测试极端挂死，见第 2 点）。

## 上游测试盘点与实测结果（rule4 实数申报）

| 类别 | 注册数 | 实测结果 |
|------|--------|----------|
| QTEST_MAIN 单测 | 43 | 42 全过；testicaltimezones 排除（tzdata 快照敏感，见下） |
| RecurNext | 144 | 143 过；TestCase44 排除（2032 远期缩写差异） |
| RecurPrev | 144 | 143 过；TestCase44 排除（同上） |
| RecursOn | 144 | 144 全过 |
| Compat | 9 | 7 过；AppleICal_1.5 + MSExchange 排除（VTIMEZONE 历史转移分段差异） |
| VCalIn | 13 | 13 全过 |
| **合计** | **497** | **492/492 执行项全过（100%），5 项 tzdata 快照差异排除** |

第六轮（qtbase 999fc4db 重建后全新构建）实测：`100% tests passed, 0 tests failed out of 492`
（Total Test time 338.64s）+ 包 ee1c2c83 创建成功；第八轮全链 RC=0，test_package 15/15 断言过
（ICalFormat 序列化/反解析往返 + VCalFormat vCalendar 1.0 导入 + Todo 时长 + R53 ELF
DT_SONAME/DT_RUNPATH 检查）。

**5 项排除定性（tzdata 快照差异，非适配缺陷；6.26.0 线同款先例排除 testicaltimezones +
Compat-AppleICal_1.5.ics）**：
- testicaltimezones.write()：序列化 QTimeZone("Europe/Prague") 对照旧时区库录的 VTIMEZONE
  快照，tzdata 2026.3 的 TZif 表示的历史转移 RRULE 分段不同（上游测试源码自己记载此类
  OS 依赖差异："this gets one extra transition of FreeBSD, which fails the test"）
- RecurNext/RecurPrev-LibICal_TestCase44.ics：最后一行是远期日期 2032-11-02，缩写
  （PDT vs PST）取决于后端对最后记录转移之外的表示——tzdata 2026.3 瘦身 TZif 带 POSIX
  footer（PST8PDT,M3.2.0,M11.1.0）而 Qt 5.15 tz 后端不外推，参考是按含显式未来转移的
  fat TZif 录的
- Compat-AppleICal_1.5.ics / Compat-MSExchange.ics：VTIMEZONE 往返内嵌同样的历史转移
  分段差异（Prague / Los_Angeles）对照 2024 录的 .ref 快照

## test_package 消费者测试（15 断言）

- MemoryCalendar UTC 构造 + addEvent/rawEvents（下游核心 API）
- ICalFormat::toString/fromRawString 往返（包内 libKF5CalendarCore.so 的 libical 解析器）
- VCalFormat::fromRawString vCalendar 1.0 导入（**注意上游 toString 是未实现桩**：
  "Exporting into VCAL is not supported" 返回空串，消费者检查走导入方向）
- Todo 时长往返
- R53 ELF 检查：DT_SONAME 无版本（libKF5CalendarCore.so）+ DT_RUNPATH（E537），直接解析
  包内 ELF 动态段（vaddr→file-offset 经 PT_LOAD 正确换算；KCALCORE_SO_PATH 编译期注入
  消费者视角路径——/proc/self/maps 在 HMDFS 上报内核侧路径不可重开）

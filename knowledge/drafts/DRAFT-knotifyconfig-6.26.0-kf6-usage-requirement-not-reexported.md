# `find_package` 说 found，编译却说 `'KConfig' file not found`：KF6 的 include 目录只跟着**那个** imported target 走

> Draft: DRAFT-knotifyconfig-6.26.0-kf6-usage-requirement-not-reexported
> Stem: `knotifyconfig-6.26.0-kf6-usage-requirement-not-reexported` —— 与本文件同名的 `.kv` 成对

## 基本信息

- **ID**: DRAFT-knotifyconfig-6.26.0-kf6-usage-requirement-not-reexported
- **严重度**: 3
- **类别**: build-system, cmake, kde, portability, dependency-graph
- **触发工具**: conan | cmake | clang
- **阶段**: compilation

## 错误特征

```text
-- Found KF6Config: ... (found version "6.26.0")
...
/storage/.../b/src/knotifyconfigelement.cpp:10:10: fatal error: 'KConfig' file not found
#include <KConfig>
         ^~~~~~~~~
/storage/.../b/src/knotifyeventlist.cpp:12:10: fatal error: 'KConfig' file not found
#include <KConfig>
         ^~~~~~~~~
make[2]: *** [src/CMakeFiles/KF6NotifyConfig.dir/...] Error 1
```

两个特征同时出现，指向完全不同的诊断方向：

1. **`find_package` 明确报 found**，所以不是"依赖没发布""`CMAKE_PREFIX_PATH` 写错""package id 不匹配"；
2. 报的是**转发头**（`KConfig` / `KConfigGroup`，无扩展名、无子目录），不是 `kconfigcore/kconfig.h` 这类真身。

## 根因分析

### KF6 的转发头装在 `include/KF6/<Module>/`，只有对应 target 带它

kconfig 上游 `src/core/CMakeLists.txt`：

```cmake
target_include_directories(KF6ConfigCore
    INTERFACE "$<INSTALL_INTERFACE:${KDE_INSTALL_INCLUDEDIR_KF}/KConfig;${KDE_INSTALL_INCLUDEDIR_KF}/KConfigCore>"
)
...
ecm_generate_headers(KConfigCore_HEADERS
  HEADER_NAMES KAuthorized KConfig KConfigBase KConfigGroup ...
)
install(FILES ${KConfigCore_HEADERS} DESTINATION ${KDE_INSTALL_INCLUDEDIR_KF}/KConfigCore)
```

即：**文件落在 `<prefix>/include/KF6/KConfigCore/`，而把这个目录写进
`INTERFACE_INCLUDE_DIRECTORIES` 的只有 `KF6::ConfigCore` 这一个 imported target。**
（注意 `INTERFACE` 里两个目录都列了：`/KConfig` 与 `/KConfigCore`；真正含
`KConfig` 的是后者。）

### 上游没链 `KF6::ConfigCore`，它在 KDE CI 里靠**传递**拿到

上游 `src/CMakeLists.txt` 是：

```cmake
target_link_libraries(KF6NotifyConfig
        PUBLIC  Qt6::Widgets
        PRIVATE KF6::I18n
                KF6::KIOWidgets     # KUrlRequester
)
```

它在 KDE CI 上能编过，是因为 `KF6::KIOWidgets` 公开链着
`KF6::ConfigCore`（kio 自己用 KConfig），usage requirement 一路传到
`KF6NotifyConfig` 的编译命令行。**这是一条隐式依赖，上游并没有显式声明
"我需要 ConfigCore"。**

ohpcd 上 kio 以 **KIOCORE_ONLY** 形态发布，而 `KF6::KIOCore` 的导出里
**没有**重新导出 `KF6::ConfigCore`，这条传递链就断了：`FOUND KF6Config`
为真（顶层 `find_package(KF6Config REQUIRED)` 确实跑到了），
`KF6::ConfigCore` 也确实存在、也确实带着正确的 include 目录 ——
但它**不在** `KF6NotifyConfig` 的链接接口里，于是编译命令行上没有
`include/KF6/KConfigCore`。

### 为什么"改 `KF6::KIOWidgets` → `KF6::KIOCore`"之后就炸

同一个 PR 的另一处适配（kio 只发 KIOCORE_ONLY，`KF6::KIOWidgets` 不存在，
见同目录 `DRAFT-knotifyconfig-6.26.0-ui-customwidget-kiowidgets-swap`）
把 `KF6::KIOWidgets` 换成了 `KF6::KIOCore`。上游那条"顺带捎来 ConfigCore"
的隐式路径正是挂在被换掉的那个目标上的：

```
上游：KF6NotifyConfig → KF6::KIOWidgets → … → KF6::ConfigCore  (include/KF6/KConfigCore 到齐)
ohpcd：KF6NotifyConfig → KF6::KIOCore   → ✗                     (什么都不捎)
```

**"换掉缺失的目标"与"丢掉它顺带提供的 usage requirement"是同一个动作的两面。**

`ecm_generate_headers` 生成的转发头还有一个易混点：它只在
**安装了**（不是构建树里）才位于 `include/KF6/KConfigCore/`；`kconfig` 包的
`test_package` 恰好是最小反例 ——

```cmake
find_package(KF6Config REQUIRED)
target_link_libraries(test_kconfig KF6::ConfigCore)
```

`#include <KConfig>` 编译通过。**同一个 `find_package`，链了 ConfigCore 就过、
没链就不过** —— 这直接把变量锁定在"链接接口"上，而不是包、版本或路径。

## 解决方案

**主方案**: link-the-target-that-owns-the-header

`#include <X>` 就必须链接**提供 X 的 target**，不要依赖上游的隐式传递。
本包的补丁（`0005-src-CMakeLists.txt-link-KF6-ConfigCore.patch`）：

```cmake
target_link_libraries(KF6NotifyConfig
        PUBLIC  Qt6::Widgets
        PRIVATE KF6::ConfigCore     # <KConfig>/<KConfigGroup> 的 include 目录只由它带
                KF6::I18n
                KF6::KIOCore
)
```

判据：编译命令行里出现 `<kconfig>/include/KF6/KConfigCore`。

### 判据：不是"包在不在"，而是"usage requirement 传没传到"

| 现象 | 结论 |
|---|---|
| `find_package` 报 **not found** | 依赖/包名/版本/`CMAKE_PREFIX_PATH` 问题 |
| `find_package` 报 **found**，但编译缺**转发头** | **usage requirement 没传播** —— 去补 `target_link_libraries` |
| 缺的是**真身**头（`kconfigcore/kconfig.h`） | 反过来，include 目录**有**但包内容不对（安装/裁剪问题） |

三种情形的修法完全不同；把第 2 种当成第 1 种去翻 CMake 变量，是最常见的空转。

### 受影响范围

一切"上游把某个 KF6 模块当**传递**依赖用、而 ohpcd 上那条传递链被裁掉"的
KDE 适配。它比"某个 target 不存在"（configure 期就报）隐蔽得多：
**configure 全绿、make 到一半才炸**。同族的显式链接受损写法见
`archives/b/baloo/6.28.0/patches/0001-CMakeLists.txt.patch`
（显式写全 `KF6::CoreAddons KF6::ConfigCore KF6::DBusAddons KF6::I18n`）。

## 反面写法

**不要**用"把所有依赖的 `include` 与 `include/KF6/*` 灌进
`CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES`"来糊过去。那是给**已经退化成裸
`-l`** 的消费者准备的兜底手法（`archives/a/alkimia/8.2.1`、
`archives/k/knewstuff/6.26.0` 的 R05 include/link fallback：它们的
`target_link_libraries` 已被改写为裸库名，usage requirement 本来就不存在）。
对仍然是 target-based 的工程这么干，等于把"这个目标用了哪个模块"的语义
抹平：以后换 baseline、多版本共存、或者审计真实依赖时会全部失真。
**能补一行 `target_link_libraries` 就不要去动全局 include 路径。**

## 验证

```sh
conan create archives/k/knotifyconfig/6.26.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 补丁能否落在正确的位置（0002 先改同一 hunk，0005 必须在其后）
patch -p1 --dry-run < archives/k/knotifyconfig/6.26.0/patches/0005-src-CMakeLists.txt-link-KF6-ConfigCore.patch
```

## 关联条目

- `DRAFT-knotifyconfig-6.26.0-ui-customwidget-kiowidgets-swap`：同一 PR 的
  另一半。那条讲 `.ui`/源码层面的控件降级，本条讲**它顺带引起的 CMake
  usage requirement 丢失**；两条合起来才是"KIOWidgets → KIOCore"的完整代价。
- `DRAFT-kf6-top-level-component-negotiation`：`find_package(KF6 COMPONENTS …)`
  的组件协商；本条是"组件找到了、target 也在，但没链进本目标"的下一层。

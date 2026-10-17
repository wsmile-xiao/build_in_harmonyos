# 把 .ui 里的 KIOWidgets 控件换成 Qt 原生控件：只改 `<widget class>` 不够

> Draft: DRAFT-knotifyconfig-6.26.0-ui-customwidget-kiowidgets-swap
> Stem: `knotifyconfig-6.26.0-ui-customwidget-kiowidgets-swap` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-knotifyconfig-6.26.0-ui-customwidget-kiowidgets-swap
- **严重度**: 2
- **类别**: build-system, cmake, kde, portability, testing
- **触发工具**: conan | cmake | uic | clang
- **阶段**: configuration | codegen | compilation

## 错误特征

三个断点，**一个比一个深**，第三个才在编译期报出来：

```
# ① configure 期
Target "KF6NotifyConfig" links to:
    KF6::KIOWidgets
  but the target was not found.

# ② uic 代码生成期（改完 <widget class> 之后）
fatal error: 'kurlrequester.h' file not found

# ③ 源码编译期
error: no member named 'setStartDir' in 'QLineEdit'
error: no member named 'setMimeTypeFilters' in 'QLineEdit'
error: no member named 'setUrl' in 'QLineEdit'
```

第 ② 条最阴：它在 configure **通过之后**才炸，报的是"缺头文件"，
很容易被当成 include 路径或 `CMAKE_PREFIX_PATH` 问题，去翻 CMake 变量，
而真正的残留在一份 `.ui` 文件里。

## 根因分析

### 前提：KIOCORE_ONLY 的 kio 没有 KIOWidgets

ohpcd 的 kio 以 KIOCORE_ONLY 形态发布——`KF6::KIOWidgets` / `KIOGui` /
`KIOFileWidgets` 都不构建（solid / kbookmarks / kjobwidgets /
kiconthemes 6.26 未发布）。另有一个容易踩的点：**连
`KF6KIOCoreConfig.cmake` 都不存在**，`KF6::KIOCore` 是在
`KF6KIOTargets.cmake` 里导出的（来自上游
`install(TARGETS KF6KIOCore EXPORT KF6KIOTargets ...)`），所以只有
`find_package(KF6KIO)` **之后**它才可见。

knotifyconfig 的通知配置部件里，声音输入框用的是 `KUrlRequester`
（文件/URL 选择器），它属于 `KF6::KIOWidgets`，在这个基线上不存在。

### 断点 ①：链接目标消失

`src/CMakeLists.txt` 里 `target_link_libraries(... PRIVATE KF6::KIOWidgets)`
直接找不到目标。

### 断点 ②：`<customwidgets>` 不会被 `<widget class>` 的改动带走

`.ui` 文件里，KDE 控件由两部分声明：

```xml
<!-- 使用点 -->
<widget class="KUrlRequester" name="Sound_select"> ... </widget>

<!-- 声明点（在文件末尾，与使用点物理分离） -->
<customwidgets>
 <customwidget>
  <class>KUrlRequester</class>
  <extends>QWidget</extends>
  <header>kurlrequester.h</header>   <!-- ← uic 生成 #include 就来自这里 -->
  <container>1</container>
 </customwidget>
</customwidgets>
```

uic 是**按 `<customwidgets>` 的内容**生成 `#include <...>` 的，与
`<widget class>` 那一行改没改无关。所以只把使用点改成
`<widget class="QLineEdit">`，声明点原封不动，uic 照样吐
`#include <kurlrequester.h>` —— 一个已经没有任何使用者的
`<customwidget>` 声明，就是这份告警的全部来源。

判据不是"还有别的控件在用这个类吗"，而是"这个 `<customwidget>` 还有
引用吗"；本例中 `KUrlRequester` 是 `<customwidgets>` 块的唯一成员，
所以整块要一起消失。

### 断点 ③：控件专有 API

| 上游调用（KUrlRequester） | 语义 | QLineEdit 上的处置 |
|---|---|---|
| `setStartDir(QUrl::fromLocalFile(soundDirs.last()))` | 给文件对话框播一个起始目录 | 删除（没有文件对话框） |
| `setMimeTypeFilters({audio/x-vorbis+ogg, audio/x-wav})` | 过滤可选文件类型 | 删除（同上） |
| `setUrl(QUrl(readEntry("Sound", true)))` | 回填 | 改写为 `setText(readEntry("Sound", true))` |
| `text()`（`save()` 里读取） | 取值 | **不用改** |

注意两处**不需要**动的地方，误伤会引入额外风险：

- `connect(m_ui.Sound_select, SIGNAL(textChanged(QString)), ...)` ——
  `KUrlRequester::textChanged(QString)` 与 `QLineEdit::textChanged(QString)`
  **同名同签名**（前者本就转发给内部 line edit），替换后 connect 一行都不用动。
- `slotPlay()` 里的 `m_ui.Sound_select->text()` —— 上游本来就只用
  `text()`，源码注释写得很清楚：*"don't use .url() here, .notifyrc files
  have predefined \"static\" entries with no path"*。也就是说
  `.notifyrc` 里 `Sound=bell.ogg` 这种裸声音名与绝对路径存在同一个字段，
  `text()` 返回的是原始字符串，换成 `QLineEdit` **不改变落盘格式**。

## 解决方案

**主方案**: three-pass-ui-widget-substitution-checklist

把一个 `.ui` 里的 KDE widgets 控件降级成 Qt 原生控件，三关都要过：

| 关 | 做什么 | 判据 |
|----|--------|------|
| 1. 链接 | `KF6::KIOWidgets` → `KF6::KIOCore` | configure 通过 |
| 2. 生成 | 改 `<widget class>`，**并删掉 `<customwidgets>` 里的对应声明** | `grep -c "<customwidget>" src/*.ui` 为 0 |
| 3. 源码 | 删除/改写控件专有 API；先核信号与取值语义是否等价 | 编译通过 |

**关于第 1 关的一个反直觉点**：不要因为"反正没用到 KIO 的 widgets"
就把 `find_package(KF6KIO)` 和整个 KIO 依赖删掉。保留 KIO 只换
`KF6::KIOWidgets → KF6::KIOCore`，依赖图与上游差异最小，而且已有大量
同款先例（audiocd、baloo 6.28.0、libkomparediff2、kgoldrunner）。
反过来"顺手删依赖"会连带改变 `find_dependency()` 链，收益小风险大。

**验收不能停在"编译过了"。** 控件降级的典型故障是**静默丢值**：
少了一条 `setText`，界面照样打开、`save()` 照样成功，只是配置项被写空。
所以 `test_package` 要跑一次真实的读-改-存往返：

1. 种子 `$XDG_CONFIG_HOME/<app>.notifyrc`：
   `[Event/test-event] Action=Sound|Popup / Sound=bell.ogg`；
2. `setApplication` → `selectEvent` → 改一项 → `save()`；
3. 读回文件断言：被改的那项确实变了、**没被改的 `Sound=bell.ogg`
   原样保留**、同组其它键（`Name`）未被破坏。

第 3 步的中间那条就是这次的回归闸门：`setConfigElement()` 的 `setText`
丢了，`text()` 是空串，落盘 `Sound` 就被写空；`save()` 里把 `text()`
换成别的东西，同样在这里炸。本项目 `test_package/test_knotifyconfig.cpp`
即按此写（9 条行为断言，外加用 `changed(bool)` 信号断言
`disableAllSounds()` 确实发出 `changed(true)`——证明事件表里真的解析出了
带 Sound 的 `test-event`，否则整个往返会因为"什么也没选中"而空转通过）。

## 验证

```sh
conan create archives/k/knotifyconfig/6.26.0 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing

# 生成关的自查（改完 .ui 后应无输出）
grep -n "<customwidget>" archives/k/knotifyconfig/6.26.0/patches/0003-*.patch
```

OHOS 制品侧另由 `test_package/test_knotifyconfig_elf.py` 覆盖
（11 条断言，仅结构化读 ELF 头与节表）：`libKF6NotifyConfig.so*` 恰有一个
实体文件、`.so` / `.so.6` 软链齐全、ELF64 / 小端 / `ET_DYN` /
`EM_AARCH64`、节表含 `.text` 与 `.codesign`。

## 关联条目

- 与 `libktorrent-26.04.0-kde-kiowidgets-to-kiocore-trim` 互补：那条讲
  **减少 KIOWidgets 的 API 用量**（源码层面砍 widgets 级调用），本条讲
  **把 .ui 里的 widgets 级控件整体换掉**（代码生成层面），两者常同时出现
  在同一批 KF6 适配里。
- 与 `opencsg-1.8.2-ohos-cmake-missing-platform-soname`、
  `DRAFT-libharu-2.3.0-missing-dt-soname` 同属"原生 OHOS 构建落在 CMake
  Generic 平台模块"的问题族（knotifyconfig 亦需手工设
  `CMAKE_SHARED_LIBRARY_SONAME_{CXX,C}_FLAG`，此处不重复展开）。

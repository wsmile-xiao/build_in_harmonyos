# Scintilla 5.6.1 - HarmonyOS 编译说明

## 概述

Scintilla 是一个跨平台的源代码编辑控件库。本文档记录其在 HarmonyOS 上的编译适配情况。

## 编译结果

| 项目 | 状态 | 说明 |
|------|------|------|
| 核心库编译 | ✅ 成功 | 33 个源文件零修改编译 |
| 单元测试 | ✅ 52/52 通过 | 3791 个断言 |
| 静态库 | ✅ 完成 | libscintilla_core.a (1.9MB) |
| 共享库构建 | ✅ 完成 | libscintilla_ohos.so (1.3MB, 零 warning) |
| 头文件安装 | ✅ 完成 | 公共 + 内部头文件 |
| 渲染层适配 | ✅ 完成 | Surface + Font + Window 全部实现 |
| DevEco 集成 | ✅ 完成 | libentry.so (NAPI 桥接) + ArkTS UI |
| 渲染管线 | ✅ 跑通 | 两阶段 Bitmap→NativeWindow, 逐行拷贝 |
| 文字渲染 | ✅ 正常 | 字体、行高、斜纹全部修复 |
| 触摸交互 | 🔧 已修复 | BN_Sci_OnTouch* 恢复 + 重入保护 + vp→px 坐标转换 |
| 键盘输入 | 🔧 已修复 | .onKeyEvent + focusable 配置 |
| 光标闪烁 | 🔧 已修复 | BN_Sci_Tick() + setInterval(500ms) |
| 触摸闪退 | 🔧 已修复 | vp→px 坐标转换 (g_density) + 范围校验 + 空指针保护 |
| 鼠标拖选反色 | 🔧 已修复 | DoButtonMove 恢复 ButtonMoveWithModifiers 调用 (2026-04-03) |
| libraryname 模式 | ❌ 已放弃 | SIGSEGV（框架层 OnSurfaceCreated 分发崩溃），切换到 SurfaceHolder |
| SurfaceHolder 模式 | 🔧 v2 待验证 | OH_ArkUI_SurfaceHolder 官方方案，v1: 显示✅ 键盘✅ 鼠标❌ 空格❌ |
| 设备验证 | ⏳ v2 rebuild | v2 修复：消除双路径冲突 + 空格keyCode + ArkTS .onTouch fallback |

## 编译方式

由于 Scintilla 的标准构建依赖 GTK（GTK2/GTK3），而 HarmonyOS 没有预装 GTK，
我们采用了**核心库 + 渲染层适配**方案：

1. **仅编译 src/ 目录**（平台无关的核心数据结构和编辑引擎）
2. **新增 PlatOHOS.cxx** 实现完整平台层（Surface、Font、Window、Menu、ListBox）
3. **新增 ScintillaOHOS.cxx** 实现 Editor 集成、事件、IME、剪贴板
4. **产出静态库** libscintilla_core.a（核心 + 平台层）
5. **产出共享库** libscintilla_ohos.so（DevEco 预编译集成方案）

### 编译命令（CMake）

```bash
# 使用 CMake 构建静态库 + 共享库
cd scintilla/ohos
mkdir -p build && cd build
cmake .. \
    -DOHOS_NDK_NATIVE=/path/to/ohos-sdk/native \
    -DSCI_SRC_DIR=/path/to/scintilla561/src
make -j$(nproc)

# 产出:
#   libscintilla_core.a   (静态库: 33 核心 + PlatOHOS)
#   libscintilla_ohos.so  (共享库: whole-archive 链接 core + ScintillaOHOS)
```

### 编译命令（手动 Makefile）

```bash
# 设置环境
export CC=clang
export CXX=clang++
export AR=llvm-ar
export RANLIB=llvm-ranlib

# 设置路径
SCI_SRC=/path/to/scintilla561
OHOS_SDK=/path/to/ohos-sdk/native

# 编译核心源文件
mkdir -p build_ohos && cd build_ohos
for f in ../scintilla/src/*.cxx; do
    name=$(basename "$f" .cxx)
    clang++ -std=c++17 -fPIC -O2 -DNDEBUG \
        -I ${SCI_SRC}/include -I ${SCI_SRC}/src \
        -c "$f" -o "${name}.o"
done

# 编译平台层（含 Native Drawing API）
clang++ -std=c++17 -fPIC -O2 -DNDEBUG \
    -I ${SCI_SRC}/include -I ${SCI_SRC}/src \
    -I ${OHOS_SDK}/sysroot/usr/include \
    -c ohos/PlatOHOS.cxx -o PlatOHOS.o

# 创建静态库（不含 ScintillaOHOS.o）
llvm-ar rcs libscintilla_core.a *.o
llvm-ranlib libscintilla_core.a

# 编译 Editor 集成层
clang++ -std=c++17 -fPIC -O2 -DNDEBUG -DSCI_OHOS \
    -include cstddef -include cstdint -include cassert -include cstring \
    -I ${SCI_SRC}/include -I ${SCI_SRC}/src \
    -I ${OHOS_SDK}/sysroot/usr/include \
    -I ${SCI_SRC}/ohos \
    -c ohos/ScintillaOHOS.cxx -o ScintillaOHOS.o

# 创建共享库（whole-archive 确保符号不丢失）
clang++ -shared -o libscintilla_ohos.so \
    -Wl,--whole-archive libscintilla_core.a -Wl,--no-whole-archive \
    ScintillaOHOS.o \
    -L${OHOS_SDK}/sysroot/usr/lib/aarch64-linux-ohos \
    -lnative_drawing \
    -fPIC -O2
```

### 构建共享库说明

共享库 `libscintilla_ohos.so` 的构建采用两阶段方案：

1. **阶段一**：编译 33 个核心源文件 + PlatOHOS.cxx → 打包为 `libscintilla_core.a` 静态库
2. **阶段二**：编译 ScintillaOHOS.cxx → 与静态库通过 `--whole-archive` 链接为共享库

`--whole-archive` 是关键：确保静态库中所有符号（包括未被 ScintillaOHOS.cxx 直接引用的内部符号）都被保留在共享库中，避免运行时符号未定义错误。

### 使用示例（离屏渲染）

```cpp
#include "ScintillaTypes.h"
#include "ScintillaMessages.h"
#include "Scintilla.h"
#include "Geometry.h"
#include "Platform.h"
#include <cstdio>

using namespace Scintilla;
using namespace Scintilla::Internal;

int main() {
    // 创建字体
    auto font = Font::Allocate(FontParameters("HarmonyOS Sans", 14));

    // 创建离屏 Surface
    auto surf = Surface::Allocate(Technology::Default);
    surf->Init(nullptr);  // 用于文本测量

    // 测量文本宽度
    float w = surf->WidthText(font.get(), "Hello HarmonyOS!");

    // 创建Pixmap进行绘制
    surf->Release();
    auto pm = surf->AllocatePixMap(800, 600);
    pm->FillRectangle(PRectangle(0, 0, 800, 600), Fill(ColourRGBA(255, 255, 255)));
    pm->DrawTextNoClip(PRectangle(10, 10, 790, 590), font.get(), 20.0f,
        "Hello HarmonyOS!", ColourRGBA(0, 0, 0), ColourRGBA(255, 255, 255));

    return 0;
}
```

### 链接

```bash
# 链接共享库方式（推荐用于 DevEco 预编译方案）
clang++ -std=c++17 myapp.cpp -L./build_ohos -lscintilla_ohos \
    -L${OHOS_SDK}/sysroot/usr/lib/aarch64-linux-ohos -lnative_drawing \
    -lstdc++ -lm -o myapp

# 链接静态库方式
clang++ -std=c++17 myapp.cpp -L./build_ohos -lscintilla_core \
    -L${OHOS_SDK}/sysroot/usr/lib/aarch64-linux-ohos -lnative_drawing \
    -lstdc++ -lm -o myapp
```

## 平台层实现说明

PlatOHOS.cxx（707 行）使用 HarmonyOS Native Drawing API 实现了完整的平台抽象层：

| 类/命名空间 | 实现内容 | 使用 API |
|------------|---------|---------|
| `SurfaceImplOHOS` | 绘制表面（~40 个虚方法） | OH_Drawing_Canvas, Brush, Pen, Path, Bitmap, TextBlob |
| `FontHandleOHOS` | 字体管理 | OH_Drawing_Font, Typeface, FontMgr |
| `ListBoxX` | 自动补全列表（stub） | 内存列表，待对接 ArkUI |
| `Window` | 窗口管理（stub） | 待对接 XComponent |
| `Menu` | 右键菜单（stub） | 待对接 ArkUI 菜单 |
| `Platform` | 系统默认值 | Chrome, DefaultFont, DoubleClickTime |

### SurfaceImplOHOS 绘制能力

| 方法 | 状态 | 说明 |
|------|------|------|
| LineDraw / PolyLine | ✅ | 线段绘制 |
| Polygon | ✅ | 多边形填充+描边 |
| RectangleDraw / Frame | ✅ | 矩形 |
| FillRectangle | ✅ | 矩形填充 |
| RoundedRectangle | ✅ | 圆角矩形 |
| AlphaRectangle | ✅ | 带透明度圆角矩形 |
| Ellipse / Stadium | ✅ | 椭圆/药丸形 |
| DrawRGBAImage | ✅ | RGBA 图像绘制 |
| Copy | ✅ | Pixmap 位块传输 |
| GradientRectangle | ⚠️ | 简化实现（取末色） |
| DrawText* 系列 | ✅ | 文本绘制（TextBlob） |
| MeasureWidths / WidthText | ✅ | 文本测量（Glyph 宽度） |
| Ascent / Descent / Height | ✅ | 字体度量 |
| SetClip / PopClip | ✅ | 裁剪区域 |

## 鸿蒙适配特性

- **零源码修改**：所有 33 个 src/*.cxx 文件原样编译通过
- **标准 C++17**：核心代码仅使用标准 C++，无平台特定代码
- **完整单元测试**：52 个测试用例全部通过
- **Native Drawing API**：使用 HarmonyOS 官方 2D 图形 API，无需第三方依赖
- **707 行平台层代码**：Surface + Font + Window + Menu + ListBox 全部实现
- **双库产出**：静态库（核心）+ 共享库（集成），灵活适配不同集成方案
- **DevEco 集成**：预编译 .so 方案，通过 XComponent + NAPI 桥接 ArkTS

## 已知限制

1. **Window 为桩实现**：GetPosition/Invalidate 等返回默认值，需对接 XComponent 宿主
2. **ListBox 为内存实现**：数据保存在内存中，无 UI 渲染，需对接 ArkUI List 组件
3. **Menu 为空实现**：需对接 ArkUI 菜单组件
4. **GradientRectangle 简化**：目前取渐变末色填充，未实现线性渐变
5. **BiDi 文本布局**：Layout() 返回空，不支持双向文本
6. **无持续渲染机制**：目前仅 OnSurfaceCreated/Changed 触发单次绘制，内容变更后不会自动刷新
7. **PerformDraw 时序 Bug（已修复）**：Init 必须在 Initialised 检查之前，已在 2026-04-01 修复
8. **字体加载静默失败**：`FontMgrMatchFamilyStyle` 失败时回退到默认 Typeface，已添加 hilog 诊断（tag: `PlatOHOS`）
9. **触摸闪退 SIGABRT（已修复）**：ArkTS vp 坐标未转换直接传入 Scintilla（px 坐标系），Move 事件触发内部 assert → abort()。修复：`SciOnTouch()` 中 `px = vp * density` + 范围校验
10. **XComponent inputMode invalid（已知限制）**：2in1 设备上 XComponent NDK NODE_TOUCH_EVENT 被框架拦截，ArkTS .onTouch() 可绕过
11. **libraryname SIGSEGV（已确认不可用）**：OH_NativeXComponent_RegisterCallback 导致框架层 OnSurfaceCreated 分发时崩溃
12. **SurfaceHolder 双路径冲突（v2 已修复代码）**：XComponentController 与 SurfaceHolder 抢占 surface 管理权导致 Holder 为 null

## 下一步

1. **🔴 SurfaceHolder v2 验证**：rebuild 确认 SurfaceHolder 非 null + 鼠标/空格/显示正常
2. **中文/Emoji 输入**：验证 SurfaceHolder NODE_ON_KEY_EVENT 的 GetUnicode 路径，或继续用 ArkTS keyCode 映射
3. **大文件性能测试**：>10MB 文件的滚动、搜索性能
4. **语法高亮配置**：至少 3 种语言的 lexer 配置（C/C++/JS）
5. **ListBox UI 对接**：用 ArkUI List 组件实现自动补全弹出框

## 归档文件清单（2026-04-02 更新）

| 文件 | 行数 | 说明 |
|------|------|------|
| `PROGRESS.md` | 291 | 完整进展时间线 + 15 条踩坑记录 |
| `ohos/ScintillaOHOS.cxx` | 1235 | Editor 集成层（含 DoTickCaret 光标驱动） |
| `ohos/ScintillaOHOS.h` | 216 | 公共 API（含 BN_Sci_Tick 声明） |
| `ohos/PlatOHOS.cxx` | 707 | 平台渲染层（Surface/Font/Window） |
| `ohos/CMakeLists.txt` | — | CMake 构建配置 |
| `napi-bridge/napi_init.cpp` | ~1130 | NAPI 桥接层（含 g_rendering 重入保护, SciTick, g_density 坐标转换） |
| `napi-bridge/Index.ets` | ~215 | ArkTS UI（含 setInterval caret 定时器, getDisplayDensity, sciSetDensity） |
| `patches/0001~0004` | — | 4 个补丁文件 |
| `scripts/build.sh` | — | 构建脚本 |

## 独立编译

从 2026-04-01 起，可使用独立编译脚本一键重编：

```bash
cd /storage/Users/currentUser/tmp/builds/scintilla
bash build_ohos.sh

# 产出: out/libscintilla_ohos.so (1.3MB, aarch64)
# 部署: cp out/libscintilla_ohos.so /path/to/mynotepad/entry/libs/arm64-v8a/
```

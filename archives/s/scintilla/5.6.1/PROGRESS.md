# MyNotePad / Scintilla 5.6.1 HarmonyOS 适配 - 项目进展

## 项目概述

基于 Scintilla 5.6.1 的 HarmonyOS 原生文本编辑器，采用 DevEco Studio 开发。

## 架构设计（解耦）

```
entry/libs/arm64-v8a/libscintilla_ohos.so  ← 预编译 Scintilla 引擎 (1.4MB, 1442 symbols)
entry/libs/arm64-v8a/libentry.so           ← NAPI 桥接层 (205KB, 编译产生)
entry/src/main/cpp/napi_init.cpp           ← NAPI 注册 + XComponent 回调
entry/src/main/ets/pages/Index.ets         ← ArkTS UI (XComponent 容器)
```

- **libscintilla_ohos.so**: Scintilla 核心 + OHOS 平台层 + 集成层，通过 `--whole-archive` 正确链接所有符号
- **libentry.so**: NAPI 桥接层，链接预编译 .so + 系统库（libace_napi.z.so, libace_ndk.z.so）
- Scintilla 源码不参与 DevEco 编译，通过 `entry/libs/${OHOS_ARCH}/` 引入

## Scintilla 适配层文件

| 文件 | 行数 | 说明 |
|------|------|------|
| scintilla/ohos/PlatOHOS.cxx | 707 | Surface/Font/ListBox/Window 渲染层（Native Drawing API） |
| scintilla/ohos/ScintillaOHOS.cxx | 1210 | Editor 集成 + 事件 + IME + 剪贴板 + BN_Sci_* 导出 + FineTicker |
| scintilla/ohos/ScintillaOHOS.h | 167 | 公共 API（ScintillaOHOS 类 + BN_Sci_* 声明） |
| scintilla/src/Editor.cxx | 286K | 原版 + ChangeSize() 方法（用于尺寸变更通知） |
| src/main/cpp/napi_init.cpp | ~270 | NAPI 注册 + XComponent 回调 |

## 进展时间线

### ✅ 2026-03-31 — Scintilla 引擎适配完成

- [x] Phase 0-4: 源码解压、编译环境搭建、33 个核心源文件编译通过
- [x] Phase 5: ScintillaOHOSEditor 实现（Editor 初始化、Paint 调用）
- [x] Phase 6: 触摸/键盘/鼠标事件桥接
- [x] Phase 7: IME 中文输入适配
- [x] Phase 8: 剪贴板适配（Copy/Paste/Cut）
- [x] Phase 9: CMake 构建配置
- [x] Phase 10: 编译链接验证

### ✅ 2026-03-31 — DevEco 工程集成

- [x] 创建 DevEco Studio 工程 (Empty Ability)
- [x] 复制源文件和头文件到 DevEco 工程
- [x] CMakeLists.txt 配置（预编译 .so 方案）
- [x] NAPI 注册 9 个函数（Create/Destroy/SetText/GetText/.../RegisterXComponent）
- [x] ArkTS UI：XComponent + 标题栏 + 状态栏
- [x] XComponent 回调：OnSurfaceCreated/Changed/Destroyed + DispatchTouchEvent
- [x] ArkTS onAppear 调用 sciRegisterXComponent 绑定渲染
- [x] libentry.so 编译链接成功 (205KB, arm64-v8a)
- [x] HAP 打包签名成功

### ✅ 2026-03-31 — 设备部署调试

- [x] libscintilla_ohos.so 符号修复（--whole-archive 链接，1442 个动态符号，零 undefined）
- [x] PlatOHOS.o 残缺版本修复（从 108 行桩版本 → 707 行完整渲染版本重新编译）
- [x] libentry.so RUNPATH 修复（$ORIGIN，避免构建机绝对路径）
- [x] libscintilla_ohos.so DT_NEEDED 修复（link_directories + 短库名，避免绝对路径嵌入）
- [x] **应用启动成功，无报错，NAPI 模块加载成功**
- [x] **UI 正常显示：XComponent 区域 + 标题栏 + 状态栏（"ReadOnly - 0 Ln, 0 Col"）**

### 🔧 2026-03-31 — 运行时渲染调试（进行中）

- [x] .so 加载成功，无符号缺失
- [x] NAPI 绑定成功（import libentry.so 不再返回 undefined）
- [x] XComponent Surface 创建成功（OnSurfaceCreated 回调触发）
- [ ] **黑屏问题**：XComponent 区域显示黑色，文本未渲染
  - 可能原因 1：BN_Sci_SetText 未被调用（文本内容为空）
  - 可能原因 2：绘制回调未正确触发（OnDraw 未调用 Editor::Paint）
  - 可能原因 3：Surface 绑定到 XComponent Canvas 的流程有问题
- [ ] 触摸交互验证
- [ ] IME 中文输入验证
- [ ] 剪贴板验证

### 🔧 2026-04-01 — NativeWindow 获取 + FineTicker 修复

- [x] ArkTS `onDisAppear` → `onDisAppear`（API 22 大小写规范）
- [x] NAPI OH_Drawing_Rect opaque type 修复（→ `OH_Drawing_RectCreate()`）
- [x] XComponent 注册方式重构：
  - 去掉 `__NATIVE_XCOMPONENT_OBJ__[id]` 手动查找（API 12 不支持属性枚举）
  - 改用 `napi_unwrap(OH_NATIVE_XCOMPONENT_OBJ)` 在 Init 中获取 NativeXComponent 指针
  - 回调注册延迟到 ArkTS `onLoad` → `sciRegisterXComponent(surfaceId)` 调用
- [x] `OH_NativeWindow_CreateNativeWindowFromSurfaceId(surfaceId, &window)` 获取 NativeWindow
- [x] Init 不再注册回调（避免在框架 XComponent 生命周期处理中间重入导致 SIGBUS）
- [x] **FineTicker 修复**：ScintillaOHOSEditor 添加 `FineTickerStart/Cancel/Running` 虚函数重写
  - Editor 基类 `FineTickerCancel` 有 `assert(false)`，子类必须重写
  - 使用 `std::bitset<TickReason::dwell>` 跟踪 ticker 状态（stub 实现，不做实际定时）
- [x] 新增补丁 `patches/0002-add-fineticker-overrides.patch`

### ✅ 2026-04-01 — 渲染管线跑通

- [x] **virAddr 为 NULL**：`OH_NativeWindow_CreateNativeWindowFromSurfaceId` 创建的窗口 buffer 不映射用户空间
- [x] **mmap fallback**：`mmap(handle->fd, handle->size, PROT_WRITE, MAP_SHARED)` 映射 GPU buffer
- [x] **BitmapCreate 无像素**：`OH_Drawing_BitmapCreate()` 不分配内存 → 改用 malloc + `BitmapCreateFromPixels`
- [x] **两阶段渲染**：
  1. malloc pixelBuf → BitmapCreateFromPixels → Canvas → Clear white → BN_Sci_OnDraw → 清理 canvas/bitmap
  2. RequestBuffer → mmap handle->fd → memcpy pixelBuf → msync → munmap → FlushBuffer → free pixelBuf
- [x] **白屏显示成功**，无崩溃，BN_Sci_OnDraw 被调用（耗时 9ms）

### ✅ 2026-04-01 — 文本渲染 Bug 修复

- [x] 修复时序：sciSetFont/sciSetText 从 aboutToAppear 移到 onLoad（BN_Sci_Init 之后）
- [x] **根因定位**：`PerformDraw()` 中 `surf->Initialised()` 检查在 `surf->Init()` 之前执行，导致所有绘制被跳过
- [x] **修复 PerformDraw 时序 Bug**：将 `Init()` 调用移到 `Initialised()` 检查之前
- [x] **PlatOHOS 诊断日志**：在 FontHandleOHOS 构造函数和 DrawTextNoClip 中添加 hilog 日志（tag: `PlatOHOS`）
  - 字体名匹配成功/失败日志
  - Typeface 默认回退日志
  - Font 创建失败日志
  - TextBlob 创建失败日志
- [x] **独立编译脚本**：创建 `builds/scintilla/build_ohos.sh`，支持一键重编 libscintilla_ohos.so
  - 编译器：`/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++`
  - NDK sysroot：`/data/service/hnp/ohos-sdk.org/ohos-sdk_6.1.0.27/ohos/native/sysroot`
  - 产出路径：`builds/scintilla/out/libscintilla_ohos.so` (1.3MB)
- [x] **新 .so 部署**：编译零 warning，已部署到 `entry/libs/arm64-v8a/libscintilla_ohos.so`
- [ ] **待设备验证**：重新 Build & Deploy 到真机确认文字正常显示
- [ ] 持续渲染机制
- [ ] 触摸/IME/剪贴板验证

## 构建产物

| 文件 | 大小 | 说明 |
|------|------|------|
| libscintilla_ohos.so | 1.3MB | 完整 Scintilla 引擎 + 集成层（含 PlatOHOS 诊断日志） |
| libscintilla_ohos.so.bak_pre_fix | 1.3MB | 修复前备份（PerformDraw 时序 Bug 版本） |
| libentry.so | 205KB | NAPI 桥接层 |
| libc++_shared.so | 1.2MB | C++ 标准库 |
| entry-default-signed.hap | — | 应用安装包（含以上 3 个 .so） |

## 构建环境

- DevEco Studio SDK: `/data/app/sdk.org/sdk_1.0.0/default`
- 完整 SDK 备份: `/storage/Users/currentUser/usr/sdk_1.0.0/default`
- OHOS NDK (命令行): `/data/service/hnp/ohos-sdk.org/ohos-sdk_6.1.0.27/ohos/native`
- OHOS NDK sysroot: `/data/service/hnp/ohos-sdk.org/ohos-sdk_6.1.0.27/ohos/native/sysroot`
- 交叉编译器: `/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++` (clang 15.0.4)
- Scintilla 源码: `/storage/Users/currentUser/tmp/builds/scintilla/` (含 ohos/ 平台层)
- Scintilla 构建脚本: `/storage/Users/currentUser/tmp/builds/scintilla/build_ohos.sh`
- Scintilla 头文件: `/storage/Users/currentUser/renshang/mynotepad/entry/src/main/cpp/scintilla/{include,src}/`
- 系统库（libnative_drawing 等）运行时加载，编译时不提供 stub

## 踩坑记录

### 1. DT_NEEDED 绝对路径泄露
**问题**: 直接将 .so 文件路径传给 `target_link_libraries` 导致构建机绝对路径嵌入 DT_NEEDED。
**修复**: 使用 `link_directories()` + 短库名。对于无 SONAME 的 .so，链接器会把完整路径写入 DT_NEEDED。

### 2. --whole-archive 必需
**问题**: ScintillaOHOS.cxx 通过虚函数调度访问 Editor 内部方法（如 ChangeSize），链接器无法感知这些间接引用，导致符号被丢弃。
**修复**: 使用 `-Wl,--whole-archive libscintilla_core.a -Wl,--no-whole-archive` 强制包含所有符号。

### 3. PlatOHOS.o 残缺版本
**问题**: 构建目录中的 PlatOHOS.o 是从旧的 108 行桩版本编译的（只有 Font/Surface/Platform 9 个符号），但 ohos/PlatOHOS.cxx 已更新为 707 行完整渲染版本。导致 Window/Menu/ListBox 所有符号在 .a 中为 undefined。
**修复**: 用正确的 include 路径从 707 行 PlatOHOS.cxx 重新编译 PlatOHOS.o（32 个定义符号），替换 .a 中的旧版本。

### 4. RUNPATH vs RPATH
**问题**: DevEco/CMake 默认将构建路径写入 RUNPATH。
**修复**: 设置 `BUILD_WITH_INSTALL_RPATH=TRUE` + `INSTALL_RPATH="$ORIGIN"`，让 .so 在设备上从自身所在目录查找依赖。

### 5. PerformDraw 时序 Bug（致命，已修复 2026-04-01）
**问题**: `ScintillaOHOS.cxx` 的 `PerformDraw()` 中，`surf->Initialised()` 在 `surf->Init()` 之前调用。刚分配的 `SurfaceImplOHOS` 的 `canvas` 成员为 nullptr，`Initialised()` 返回 false，导致整个 `Paint()` 从未被调用 —— 所有绘制（背景、文字、光标）全部被跳过。
**表现**：白屏+黑线（光标由 `napi_init.cpp` 侧的独立绘制代码产生，不经过 Scintilla Paint 管线）
**根因代码**：
```cpp
// Bug: Init 在 Initialised 检查之后
auto surf = Surface::Allocate(technology);
if (!surf || !surf->Initialised()) return;  // canvas=nullptr → false
surf->Init(static_cast<SurfaceID>(canvas), wMain.GetID());
```
**修复**：
```cpp
// Fix: Init 在 Initialised 检查之前
auto surf = Surface::Allocate(technology);
if (!surf) return;
surf->Init(static_cast<SurfaceID>(canvas), wMain.GetID());
if (!surf->Initialised()) return;
```
**教训**：Surface 生命周期是 Init → 使用 → Release，检查 Initialised 必须在 Init 之后。此类时序 Bug 在 C++ RAII 模式下容易防范——应考虑让 `Allocate()` 直接完成初始化。

### 6. HarmonyOS 日志脱敏（2026-04-01）
**问题**: 设备日志中所有数值参数显示为 `<private>`，无法直接诊断。
**绕过**: `snprintf(dbg, sizeof(dbg), "value=%d", x); MYLOGI("%s", dbg);`

## 关键注意事项

1. SDK sysroot 无 .so 文件，系统库符号由运行时解析
2. ArkUI_NodeContentHandle 必须定义为 `typedef struct ArkUI_NodeContent* ArkUI_NodeContentHandle`
3. XComponent 注册流程：ArkTS onAppear → sciRegisterXComponent(id) → 从全局 `__NATIVE_XCOMPONENT_OBJ__` 获取 OH_NativeXComponent 指针 → RegisterCallback
4. 触摸事件通过 DispatchTouchEvent 回调 → BN_Sci_OnTouchDown/Move/Up 转发
5. PlatOHOS.cxx 编译需要 Scintilla 头文件，正确路径为 mynotepad 工程的 `entry/src/main/cpp/scintilla/{include,src}/`

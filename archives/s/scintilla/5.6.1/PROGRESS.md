# MyNotePad 项目进展

## 项目概述

基于 Scintilla 5.6.1 的 HarmonyOS 原生文本编辑器，采用 DevEco Studio 开发。

## 架构设计

```
entry/libs/arm64-v8a/libscintilla_ohos.so  ← 预编译 Scintilla 引擎 (1.49MB, 1419 symbols)
entry/libs/arm64-v8a/libentry.so           ← NAPI 桥接层 (编译产生)
entry/src/main/cpp/napi_init.cpp           ← NAPI 注册 + XComponent 回调
entry/src/main/ets/pages/Index.ets         ← ArkTS UI (XComponent 容器)
```

- **libscintilla_ohos.so**: Scintilla 核心 + OHOS 平台层 + 集成层（`--whole-archive` 链接）
- **libentry.so**: NAPI 桥接层，链接预编译 .so + 系统库
- Scintilla 源码不参与 DevEco 编译，通过 `entry/libs/${OHOS_ARCH}/` 引入

## 进展时间线

### ✅ 2026-03-31 — Scintilla 引擎适配

- [x] Phase 0-4: 源码解压、编译环境搭建、33 个核心源文件编译通过
- [x] Phase 5-8: Editor 初始化、触摸/键盘事件、IME 中文输入、剪贴板适配
- [x] Phase 9-10: CMake 构建配置、编译链接验证
- [x] libscintilla_ohos.so 符号修复（--whole-archive，1419 个动态符号）

### ✅ 2026-03-31 — DevEco 工程集成

- [x] 创建 DevEco Studio 工程，NAPI 注册 9 个函数
- [x] ArkTS UI：XComponent + 标题栏 + 状态栏
- [x] HAP 打包签名成功

### ✅ 2026-03-31 — 设备部署与 .so 修复

- [x] RUNPATH 修复（$ORIGIN）
- [x] DT_NEEDED 修复（link_directories + 短库名）
- [x] PlatOHOS.o 残缺版本修复

### ✅ 2026-04-01 — 编译修复

- [x] ArkTS `onDisappear` → `onDisAppear`（大小写命名）
- [x] `OH_Drawing_Rect` opaque type → `OH_Drawing_RectCreate()` 动态创建
- [x] 函数前向声明（SciRegisterXComponent/Unregister）
- [x] `<atomic>` 头文件缺失
- [x] `%llu` → `%lu`（aarch64 格式符）
- [x] 链接 `libhilog_ndk.z.so`（OH_LOG_Print 符号）
- [x] XComponent `.onAppear()` 不触发 → 改用 `.onLoad()`/`.onDestroy()`

### 🔧 2026-04-01 — XComponent 回调注册调试

- [x] libentry.so 加载成功，SciCreate 正常
- [x] XComponent `.onLoad()` 正常触发（ArkTS 侧日志确认）
- [x] `__NATIVE_XCOMPONENT_OBJ__` 全局对象获取成功
- [x] **发现 API 12 变更**：
  - `OH_NativeXComponent_GetNativeXComponent()` 参数从 `char*` 改为 `ArkUI_NodeHandle`
  - `__NATIVE_XCOMPONENT_OBJ__` 不支持 `napi_get_property_names()`（调用直接 SIGSEGV）
  - 正确流程：`xcompObj[id]` → external → `ArkUI_NodeHandle` → `GetNativeXComponent(node)`
- [x] 修复 SIGSEGV：属性查找失败后 early return
- [x] 修复 `SciRegisterXComponent`：使用正确的 API 12 流程（nodeHandle 转换）
- [x] 回调注册成功，OnSurfaceCreated 正常触发
- [x] NativeWindow 获取成功（OH_NativeWindow_CreateNativeWindowFromSurfaceId）

### ✅ 2026-04-01 — 渲染管线跑通

- [x] **virAddr 为 NULL**：GPU buffer 不映射用户空间
- [x] **mmap fallback**：`mmap(handle->fd, handle->size, PROT_WRITE, MAP_SHARED)` 映射
- [x] **BitmapCreate 无像素**：改用 `malloc + BitmapCreateFromPixels`
- [x] **两阶段渲染**：独立 Bitmap 渲染 → memcpy 到 NativeWindow buffer
- [x] **白屏显示成功**，BN_Sci_OnDraw 被调用

### ✅ 2026-04-01 — 文本渲染 Bug 修复

- [x] 修复时序：sciSetFont/sciSetText 从 aboutToAppear 移到 onLoad
- [x] **根因定位**：`PerformDraw()` 中 `surf->Initialised()` 在 `surf->Init()` 之前执行
  - 刚分配的 SurfaceImplOHOS 的 canvas=nullptr → Initialised() 返回 false
  - **整个 Paint() 被跳过**，导致白屏+黑线（只有 napi_init.cpp 侧绘制的背景+光标线）
- [x] **修复**：将 `Init()` 移到 `Initialised()` 检查之前
- [x] **PlatOHOS 诊断日志**：FontHandleOHOS + DrawTextNoClip 添加 hilog（tag: `PlatOHOS`）
- [x] **独立编译脚本**：`/storage/Users/currentUser/tmp/builds/scintilla/build_ohos.sh`
- [x] **新 .so 部署**：零 warning 编译，已替换 `entry/libs/arm64-v8a/libscintilla_ohos.so`
- [ ] **待设备验证**：重新 Build & Deploy 确认文字正常显示

### 🔧 2026-04-02 — Stride Mismatch 修复 & 日志脱敏突破

- [x] **斜花条纹根因定位**：`napi_init.cpp` RenderFrame 用 `surfaceWidth * 4` 做行字节数做简单 `memcpy`，但 NativeWindow buffer 的实际 stride (`handle->stride`) 可能更大（GPU 对齐），导致每行像素错位产生斜纹
- [x] **修复**：改为逐行拷贝 — 每行只拷贝 `min(srcStride, dstStride)` 字节，行偏移分别用 `srcStride` 和 `handle->stride`
- [x] **日志脱敏突破**：发现 `%{public}` 格式修饰符可绕过 hilog 脱敏
  - 之前 `snprintf` 预格式化 + `%s` 的方式**失败**：hilog 会扫描最终字符串内容替换数值
  - 正确做法：`%{public}s`、`%{public}d`、`%{public}p` 等直接在 hilog 格式字符串中声明公开
  - 备选：`fprintf(stderr, ...)` 完全绕过 hilog
- [x] `napi_init.cpp` 全部日志改用 `%{public}` 格式符
- [x] `PlatOHOS.cxx` `PLAT_DBG` 宏改用 `snprintf` + `%{public}s`
- [x] `libscintilla_ohos.so` 重新编译部署（零 warning）
- [ ] **待设备验证**：clean build + 确认斜纹消失、日志数值正常显示

### 🔧 2026-04-02 — 字体指标符号修复

- [x] **问题**：渲染内容堆积到左上角，无法看清
- [x] **根因**：OH_Drawing（底层 Skia）的 `FontMetrics.ascent` 返回**负值**（Skia 坐标系 Y 轴向下，ascent 向上为负），但 Scintilla 期望正值
  - 日志：`fontSizePx=24.9 ascent=-23.1 descent=6.1 height=-17.0` — 负 height 导致行高计算错误
  - DrawTextNoClip 坐标：`rc=(21,0,40,7) ybase=1.0` — 每行只有 7px 高，挤在左上角
- [x] **修复**：`GetAscent()` 返回 `-metrics.ascent`（取绝对值），`GetHeight()` 用 `-metrics.ascent + metrics.descent`，`GetInternalLeading()` 同理
- [ ] **待设备验证**：clean build + 确认文字正常显示、行高正确

### 🔧 2026-04-02 — 持续渲染机制

- [x] **问题**：Scintilla 调用 `Window::InvalidateAll()`/`InvalidateRectangle()` 请求重绘，但这些是空 stub，请求被吞掉
- [x] **修复**：添加全局回调机制
  - `PlatOHOS.cxx`：`static void (*s_redrawRequested)(void)` + `PlatOHOS_SetRedrawCallback()`
  - `Window::InvalidateAll()`/`InvalidateRectangle()` 调用回调
  - `ScintillaOHOS`：`BN_Sci_SetRedrawCallback(cb)` 委托到 PlatOHOS
  - `napi_init.cpp`：`SciCreate()` 中注册 `BN_Sci_SetRedrawCallback(RequestRedraw)`
- [x] **补丁 0004 重建**（含 redraw callback + font metrics + diagnostics）

### 🔧 2026-04-02 — 键盘输入调研结论

- [x] **NDK 原生方案测试结果**：
  - `OH_NativeXComponent_SetNeedSoftKeyboard(component, true)` → 框架判定获焦节点（Column）不需要键盘，被覆盖关闭
  - `OH_NativeXComponent_RegisterKeyEventCallback(component, cb)` → **ret=0 成功** ✅
  - `OH_NativeXComponent_RegisterUIInputEventCallback(component, cb, ARKUI_UIINPUTEVENT_TYPE_KEY)` → **ret=401 失败** ❌
- [x] **设备不支持软键盘**（当前为 2in1 平板设备），键盘方案暂缓
- [x] **物理键盘**：KeyEvent 回调注册成功（ret=0），但未收到任何按键事件
- [x] **结论**：NDK 纯原生键盘方案在当前设备上行不通，保留代码待后续设备验证

### 🔧 2026-04-02 — 设备测试结果（关键阻塞）

- [x] **文本渲染**：文字正常显示，斜纹已修复，行高正确 ✅
- [x] **Stride mismatch**：逐行拷贝正常工作 ✅
- [x] **持续渲染**：redraw callback 机制正常工作 ✅
- [x] **字体 fallback**：`HarmonyOS Sans` 匹配失败，使用 default typeface 正常显示
- [ ] **触摸事件**：`inputMode is invalid`，2in1 设备特有问题，`OnDispatchTouchEvent` 未被调用 ❌
- [ ] **物理键盘**：回调注册成功但无事件到达 ❌（可能与 inputMode 问题同一根因）
- [ ] **光标闪烁**：未看到 caret 闪烁 ❌（可能需要事件循环驱动）

### 🔧 2026-04-02 — 核心阻塞问题分析与修复（inputMode bypass）

- [x] **调研结论**：NDK 头文件（`ace/xcomponent/native_interface_xcomponent.h`）中无 `inputMode` 相关 API
  - `OH_NativeXComponent_RegisterCallback` / `SetNeedSoftKeyboard` / `RegisterKeyEventCallback` 等均与 inputMode 无关
  - `inputMode is invalid` 是 ArkUI 框架内部（DeviceXComponent）在 2in1 设备上的事件路由问题
  - XComponent 的 `DispatchTouchEvent` 回调依赖框架先完成 inputMode 初始化才能派发事件
  - **结论：NDK 侧无法修复此问题**
- [x] **修复方案：ArkTS 事件拦截 + NAPI 转发**
  - 在 ArkTS 侧通过 `.onTouch()` 和 `.onKeyEvent()` 拦截所有输入事件
  - 通过 NAPI 函数（`sciOnTouch` / `sciOnKeyDown` / `sciOnChar`）转发到 native 层
  - 完全绕过 XComponent 的内部 inputMode 事件路由
  - 保留原有 native 回调（OnDispatchTouchEvent 等）作为备用，修复 inputMode 后可恢复
- [x] **napi_init.cpp 新增**：
  - `SciOnTouch()` — 接收 (editor, type, x, y, timestamp)，type: 0=Down, 1=Up, 2=Move
  - `SciRequestRedraw()` — ArkTS 侧触发重绘
- [x] **Index.ets 修改**：
  - 添加 `.defaultFocus(true)` — 自动获焦，辅助键盘事件路由
  - 添加 `.onTouch()` — 拦截触摸事件，遍历 `event.touches`，调用 `sciOnTouch()`
  - 添加 `.onKeyEvent()` — 拦截键盘事件，映射 ArkUI keyCode 到 Scintilla virtual key，可打印字符通过 `sciOnChar()` 转发
- [x] **Index.d.ts 更新**：添加 `sciOnTouch`、`sciOnChar`、`sciOnKeyDown`、`sciRequestRedraw` 声明
- [ ] **待设备验证**：clean build + 确认触摸交互、键盘输入正常工作

### 🔧 2026-04-02 — XComponent 无 libraryname 方案（重大突破）

- [x] **inputMode is invalid 彌底消除** ✅
  - 根因： `inputMode is invalid` 只在 XComponent 配置了 `libraryname` 时出现
  - 方案：**去掉 libraryname**，改用 `XComponentController` 管理 Surface 生命周期
  - ArkTS 层 `.onTouch()` / `.onKeyEvent()` 事件回调**不再被屏蔽**
- [x] **Surface 创建** ✅ — `XComponentController.onSurfaceCreated` → `sciRegisterXComponent(surfaceId)`
- [x] **NativeWindow 获取** ✅ — `OH_NativeWindow_CreateNativeWindowFromSurfaceId` → 从 NativeWindow 直接获取尺寸
- [x] **文本渲染正常** ✅ — 示例文本显示正确，字体和行高正确
- [x] **鼠标点击不再崩溃** ✅ — SciOnTouch 去掉 BN_Sci 调用后鼠标事件安全
- [x] **键盘事件不再崩溃** ✅ — 去掉 XComponent 的 `.focusable()` 避免了 secure_field 问题
- [x] **OH_ArkUI_SurfaceHolder/registerNodeEvent 返回 106103**（ARKTS_NODE_NOT_SUPPORTED）
  - ArkTS 声明式 XComponent 和 typeNode.createNode 创建的节点均不支持 NDK 事件注册
  - 只有纯 NDK `nodeAPI->createNode(ARKUI_NODE_XCOMPONENT)` 创建的节点才支持，但改动量过大暂缓

### ✅ 2026-04-02 — 触摸/键盘/光标三大阻塞修复

- [x] **触摸事件恢复**：
  - `SciOnTouch` 中恢复 `BN_Sci_OnTouchDown/Move/Up` 调用（之前因崩溃被注释）
  - **根因**：`BN_Sci_OnTouch*` → Scintilla 内部 → `InvalidateAll` → `RequestRedraw()` → `RenderFrame()` 嵌套调用导致崩溃
  - **修复**：`RenderFrame()` 添加 `g_rendering` (atomic int) 重入保护，嵌套时仅设 dirty flag 不执行渲染
  - ArkTS 侧 `.onTouch()` 末尾追加 `sciRequestRedraw()` 确保帧刷新到屏幕
- [x] **键盘事件恢复**：
  - `.onKeyEvent()` 追加 `sciRequestRedraw()` 确保按键后屏幕更新
  - `.focusable(true)` + `.defaultFocus(true)` + `.focusOnTouch(true)` 保持配置（no-libraryname 方案已消除 secure_field 问题）
- [x] **光标闪烁机制**：
  - **根因**：Scintilla 的 `FineTickerStart/Cancel/Running` 只是 bitset 存根，没有实际定时器驱动 `TickFor(caret)`
  - **修复**：
    - `ScintillaOHOSEditor` 新增 `DoTickCaret()` public 包装器（绕过 protected 访问限制）
    - `ScintillaOHOS::Tick()` → `DoTickCaret()`
    - NAPI 新增 `SciTick()` 函数 + `sciTick` 导出
    - ArkTS `setInterval(500ms)` 调用 `libentry.sciTick(editor)` 驱动 caret 闪烁
    - `aboutToDisappear()` 中 `clearInterval()` 清理定时器
- [x] **libscintilla_ohos.so 重新编译部署**（零 warning，1.3MB）
- [ ] **待设备验证**：clean build + 部署，确认触摸选中文本、键盘输入、光标闪烁正常

### 🔲 当前阻塞问题

1. ~~**无光标显示**~~ → **已修复**：添加 `BN_Sci_Tick()` NAPI 接口 + ArkTS `setInterval(500ms)` 驱动 caret 闪烁
2. ~~**键盘输入无效**~~ → **待验证**：`.focusable(true)+.defaultFocus(true)+.focusOnTouch(true)` 已配置，需设备确认
3. ~~**触摸交互禁用**~~ → **已修复**：恢复 `BN_Sci_OnTouch*` 调用 + `RenderFrame()` 重入保护（`g_rendering` atomic flag）

### 📋 下一步计划

1. ~~**恢复触摸事件处理**~~ ✅ — 重入保护 + dirty flag 延迟重绘
2. ~~**解决键盘焦点问题**~~ ✅ — focusable/defaultFocus/focusOnTouch 已配置
3. ~~**恢复键盘事件转发**** ✅ — sciOnChar/sciOnKeyDown + sciRequestRedraw
4. ~~**光标渲染**~~ ✅ — BN_Sci_Tick() + setInterval(500ms) 驱动 caret 闪烁
5. **设备验证（当前步骤）**：
   - [ ] 触摸选择文本、滚动
   - [ ] 键盘输入（英文、中文）
   - [ ] 光标闪烁可见
   - [ ] 剪贴板操作

## 踩坑记录

### 1. DT_NEEDED 绝对路径泄露
直接传 .so 路径给 `target_link_libraries` → 改用 `link_directories()` + 短库名

### 2. --whole-archive 必需
虚函数间接引用导致链接器丢弃符号 → `-Wl,--whole-archive`

### 3. PlatOHOS.o 残缺版本
构建目录中的旧 .o 与源码不匹配 → 从 707 行完整版重新编译

### 4. RUNPATH 修复
`BUILD_WITH_INSTALL_RPATH=TRUE` + `INSTALL_RPATH="$ORIGIN"`

### 5. XComponent onAppear 不触发
改用 XComponent 专用 `.onLoad()` / `.onDestroy()` 回调

### 6. __NATIVE_XCOMPONENT_OBJ__ SIGSEGV
API 12 的 `__NATIVE_XCOMPONENT_OBJ__` 不支持 `napi_get_property_names()`，调用直接崩溃。
正确做法：`napi_get_named_property(xcompObj, id)` → external → `ArkUI_NodeHandle` → `OH_NativeXComponent_GetNativeXComponent(node)`

### 7. Init 中 RegisterCallback 导致 SIGBUS
在 Init 函数中调用 `OH_NativeXComponent_RegisterCallback` 会导致框架内部崩溃（signal 7）。
**修复**：Init 中只保存 NativeXComponent 指针，回调注册延迟到 ArkTS onLoad。

### 8. NativeWindow virAddr 为 NULL
通过 `OH_NativeWindow_CreateNativeWindowFromSurfaceId` 创建的窗口，其 buffer 的 `virAddr` 为 NULL（GPU buffer 不映射用户空间）。
**修复**：用 `mmap(handle->fd, handle->size, PROT_WRITE, MAP_SHARED)` 映射后写入像素，再 msync + munmap。

### 9. OH_Drawing_BitmapCreate() 无像素内存
`OH_Drawing_BitmapCreate()`（无参版本）创建的 bitmap 没有分配像素内存，`OH_Drawing_BitmapGetPixels()` 返回 NULL。
**修复**：用 `malloc(width*4*height)` 分配缓冲区，再用 `OH_Drawing_BitmapCreateFromPixels(&info, buf, stride)` 包装。

### 10. napi_init.cpp 反复损坏
文件末尾容易残留垃圾（`===============` + 重复代码块），导致编译失败。
**原因**：多次 editFile/sed 操作累积错误。每次修改后务必验证 `tail -3` + `wc -l` + `grep -c RegisterEntryModule`。

### 11. HarmonyOS 日志脱敏（已解决）
设备日志中所有数值参数显示为 `<private>`，无法直接诊断。
**错误尝试**：`snprintf(dbg, sizeof(dbg), "value=%d", x); MYLOGI("%s", dbg);` — 无效！hilog 会扫描最终字符串内容，把其中的数值替换为 `<private>`。
**正确方案**：使用 `%{public}` 格式修饰符声明参数为公开数据：`MYLOGI("value=%{public}d", x);`、`MYLOGI("ptr=%{public}p", p);`。
**组合用法**：`snprintf` 预格式化 + `MYLOGI("%{public}s", dbg)` — hilog 不会对 `%{public}s` 传递的字符串做二次扫描。
**备选**：`fprintf(stderr, ...)` 完全绕过 hilog。

### 12. PerformDraw 时序 Bug（致命，已修复）
**问题**：`ScintillaOHOS.cxx` 的 `PerformDraw()` 中，`surf->Initialised()` 在 `surf->Init()` 之前调用。刚分配的 `SurfaceImplOHOS` 的 `canvas` 成员为 nullptr，`Initialised()` 返回 false，导致整个 `Paint()` 从未被调用。
**表现**：白屏+黑线（光标由 napi_init.cpp 独立绘制，不经过 Scintilla）。
**修复**：将 `surf->Init(sid, wid)` 移到 `if (!surf->Initialised()) return` 之前。

### 13. NativeWindow Stride Mismatch 导致斜纹（已修复）
**问题**：`napi_init.cpp` RenderFrame 用 `surfaceWidth * 4` 作为行字节数做整块 `memcpy`，但 NativeWindow buffer 的 `handle->stride` 可能不等于 `width * 4`（GPU 对齐，如 128 字节对齐），导致每行像素错位，产生经典的**斜花条纹** artifact。
**修复**：改为逐行拷贝循环：
```cpp
for (uint32_t y = 0; y < h; y++) {
    memcpy(dstRow, srcRow, min(srcStride, dstStride));
    srcRow += srcStride;  // 我们的 bitmap stride = width*4
    dstRow += dstStride;  // NativeWindow buffer stride = handle->stride
}
```

### 14. OH_Drawing FontMetrics 符号与 Scintilla 不一致（已修复）
**问题**：OH_Drawing（底层 Skia）的 `FontMetrics.ascent` 返回负值（Skia 坐标系 Y 轴向下），`descent` 返回正值。Scintilla 期望 ascent 和 descent 都是正值。
**表现**：`height = ascent + descent = -23 + 6 = -17`（负行高），所有文本挤压到左上角。
**修复**：`GetAscent()` 返回 `-metrics.ascent`，`GetHeight()` 返回 `-metrics.ascent + metrics.descent`。

### 15. 2in1 设备 XComponent inputMode 无效导致事件不派发（已修复）
**问题**：2in1 平板设备上，XComponent 内部的 `inputMode` 未正确初始化，ArkUI 框架日志反复输出 `inputMode is invalid` + `mouseTransform is invalid`。由于 inputMode 无效，框架不会将触摸/鼠标事件派发到 XComponent 的 `DispatchTouchEvent` 回调，键盘事件也不会到达 `KeyEventCallback`。
**根因**：ArkUI 框架在 2in1 设备上需要确定输入模式（触摸/鼠标）才能正确路由事件，XComponent surface 模式下该初始化可能存在缺陷。NDK 头文件中无任何 `inputMode` 相关 API。
**修复**：**ArkTS 侧事件拦截 + NAPI 转发**。在 Index.ets 中给 XComponent 添加 `.onTouch()` 和 `.onKeyEvent()` 事件处理器，直接在 ArkTS 层拦截输入事件，然后通过 NAPI（`sciOnTouch`/`sciOnKeyDown`/`sciOnChar`）转发到 native Scintilla 引擎。完全绕过 XComponent 内部的事件路由机制。

## 构建环境

- DevEco Studio SDK: `/data/app/sdk.org/sdk_1.0.0/default`
- OHOS NDK (命令行): `/data/service/hnp/ohos-sdk.org/ohos-sdk_6.1.0.27/ohos/native`
- 交叉编译器: `/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++` (clang 15.0.4)
- Scintilla 源码: `/storage/Users/currentUser/tmp/builds/scintilla/` (含 ohos/ 平台层)
- Scintilla 构建脚本: `/storage/Users/currentUser/tmp/builds/scintilla/build_ohos.sh`
- Scintilla 头文件: `/storage/Users/currentUser/renshang/mynotepad/entry/src/main/cpp/scintilla/{include,src}/`
- 日志文件: `/storage/Users/currentUser/renshang/mynotepad/日志.txt`

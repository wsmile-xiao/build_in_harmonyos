# Scintilla 5.6.1 HarmonyOS 适配 - 路线图

> 本路线图服务于 BlueNotePad 项目（/renshang/BlueNotePad），提供其 C++ 编辑器内核。

---

## 适配总览

| 阶段 | 目标 | 状态 | 对应 BlueNotePad 需求 |
|------|------|------|----------------------|
| Phase 0 | 源码获取 | ✅ 完成 | Scintilla 5.6.1 |
| Phase 1 | 核心库编译（33 个 .cxx） | ✅ 完成 | Editor/Document 等核心类 |
| Phase 2 | 单元测试（52/52 通过） | ✅ 完成 | 保证编辑逻辑正确性 |
| Phase 3 | 渲染层 - Surface/Font | ✅ 完成 | Canvas 文本渲染、图形绘制 |
| Phase 4 | 渲染层 - Window/Menu/ListBox | ✅ 完成 | 窗口、菜单、补全列表 |
| **Phase 5** | **Editor 集成层** | ✅ 完成 | **ScintillaOHOSEditor + Paint 调用** |
| **Phase 6** | **输入事件桥接** | ✅ 完成 | **触摸/键盘/鼠标事件转发** |
| **Phase 7** | **IME 输入法适配** | ✅ 完成 | **中文输入支持** |
| **Phase 8** | **剪贴板适配** | ✅ 完成 | **复制/粘贴/剪切** |
| **Phase 9** | **CMake 构建系统** | ✅ 完成 | **静态库 + 共享库双目标** |
| **Phase 10** | **编译链接验证** | ✅ 完成 | **libscintilla_ohos.so + libscintilla_core.a** |
| **Phase 11** | **DevEco 工程集成** | ✅ 完成 | **libentry.so 链接 + NAPI 绑定** |
| **Phase 12** | **设备部署与运行时验证** | 🔲 进行中 | **真机渲染/交互验证** |

---

## Phase 0：源码获取 ✅ 完成

- 下载 Scintilla 5.6.1 源码包
- 解压验证 33 个核心 .cxx + 40+ .h 文件完整

---

## Phase 1：核心库编译 ✅ 完成

- 33 个 src/*.cxx 文件零修改编译通过
- 标准 C++17，无平台特定代码

---

## Phase 2：单元测试 ✅ 完成

- 52/52 测试用例通过
- 3791 个断言全部正确

---

## Phase 3：渲染层 - Surface/Font ✅ 完成

- SurfaceImplOHOS：~40 个虚方法，使用 OH_Drawing API
- FontHandleOHOS：字体管理（OH_Drawing_Font, Typeface, FontMgr）

---

## Phase 4：渲染层 - Window/Menu/ListBox ✅ 完成

- Window/Menu：桩实现
- ListBoxX：内存列表实现

---

## Phase 5：Editor 集成层 ✅ 完成

- ScintillaOHOSEditor 实现（Editor 初始化、Paint 调用）
- 将 Scintilla Editor 绑定到 HarmonyOS 渲染表面

---

## Phase 6：输入事件桥接 ✅ 完成

- 触摸事件：ButtonDown / ButtonMove / ButtonUp
- 键盘事件：KeyDown / CharAdded
- 通过 XComponent DispatchTouchEvent 回调转发

---

## Phase 7：IME 输入法适配 ✅ 完成

- 中文等非 ASCII 输入支持
- PreeditString 处理

---

## Phase 8：剪贴板适配 ✅ 完成

- Copy / Cut / Paste 操作
- 通过 NAPI 回调桥接系统剪贴板

---

## Phase 9：CMake 构建系统 ✅ 完成

- `scintilla_core` 静态库目标（33 核心 + PlatOHOS）
- `scintilla_ohos` 共享库目标（whole-archive 链接 core + ScintillaOHOS）
- 头文件安装规则
- 依赖声明（libnative_drawing.so）

---

## Phase 10：编译链接验证 ✅ 完成

- libscintilla_core.a（~1.9MB）
- libscintilla_ohos.so（~1.49MB，--whole-archive 确保符号完整）
- 手动 Makefile 脚本同步支持

---

## Phase 11：DevEco 工程集成 ✅ 完成

- 创建 DevEco Studio 工程（Empty Ability）
- 预编译 .so 方案：libscintilla_ohos.so → entry/libs/arm64-v8a/
- NAPI 注册 9 个函数（Create/Destroy/SetText/GetText/.../RegisterXComponent）
- ArkTS UI：XComponent + 标题栏 + 状态栏
- XComponent 回调：OnSurfaceCreated/Changed/Destroyed + DispatchTouchEvent
- libentry.so 编译链接成功（205KB）
- DT_NEEDED 路径修复（$ORIGIN RUNPATH）
- 符号修复（--whole-archive 链接）

---

## Phase 12：设备部署与运行时验证 🔄 进行中

**目标**：在真机/模拟器上端到端验证所有功能。

**已完成**：
- ✅ DT_NEEDED 路径修复（$ORIGIN RUNPATH）
- ✅ libscintilla_ohos.so 符号修复（whole-archive 链接）
- ✅ XComponent Surface 创建 + NativeWindow 获取
- ✅ 两阶段渲染管线（独立 Bitmap → memcpy 到 NativeWindow）
- ✅ 白屏显示成功（BN_Sci_OnDraw 被调用，耗时 ~9ms）
- ✅ PerformDraw 时序 Bug 修复（Init/Initialised 顺序）
- ✅ PlatOHOS 诊断日志（字体加载 + TextBlob 创建，tag: `PlatOHOS`）
- ✅ 独立编译脚本 `build_ohos.sh`（一键重编，零 warning）
- ✅ Stride Mismatch 修复（逐行拷贝，消除斜纹）
- ✅ FontMetrics 符号修复（Skia ascent 负值 → 取绝对值）
- ✅ 持续渲染机制（redraw callback + dirty flag）
- ✅ inputMode bypass（去掉 libraryname + ArkTS 事件拦截）
- ✅ 触摸事件恢复（BN_Sci_OnTouch* + RenderFrame 重入保护 g_rendering）
- ✅ 键盘事件恢复（.onKeyEvent + sciRequestRedraw + focusable 配置）
- ✅ 光标闪烁机制（BN_Sci_Tick + setInterval 500ms 驱动 caret blink）
- ✅ **Patch-0013: UAF 修复** — CachedMeasurementSurface operator delete no-op
- ✅ **Patch-0014: bitmap 尺寸修复** — CachedMeasurementSurface 1x1 → 2048x256
  - 根因：1x1 像素 bitmap 在 ButtonDown 文本测量路径触发 Skia SEGV_ACCERR

**待设备验证**（2026-04-04 当前步骤）：
- [ ] Rebuild HAP + 部署到设备，测试鼠标点击/拖选
- [ ] 触摸选择文本、滚动
- [ ] 键盘输入（英文、中文）
- [ ] 光标闪烁可见
- [ ] 剪贴板操作
- [ ] 大文件性能
- [ ] 语法高亮

---

## 补充适配：第三方依赖

| 依赖库 | 版本 | 用途 | 适配状态 |
|--------|------|------|---------|
| libiconv | 1.17 | 编码转换（GBK/UTF-16 等） | 🔲 待适配 |
| libcharset | 1.17 | 编码自动检测 | 🔲 待适配 |

> BlueNotePad 技术方案中提到的 Tree-sitter 增强，作为远期目标，Phase 1-12 不涉及。

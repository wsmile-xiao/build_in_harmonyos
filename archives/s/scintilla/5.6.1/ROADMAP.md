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
| **Phase 5** | **ContentSlot 集成层** | ✅ 完成 | **NativeComponent 渲染桥接** |
| **Phase 6** | **输入事件桥接** | ✅ 完成 | **触摸/键盘/鼠标事件转发** |
| **Phase 7** | **IME 输入法适配** | ✅ 完成 | **中文输入支持** |
| **Phase 8** | **剪贴板适配** | ✅ 完成 | **复制/粘贴/剪切** |
| **Phase 9** | **CMake 构建系统** | ✅ 完成 | **集成到 BlueNotePad 工程** |
| **Phase 10** | **设备运行验证** | 🔲 待做 | **端到端测试（需 DevEco Studio）** |

---

## Phase 5：ContentSlot 集成层（优先级最高）

**目标**：让 Scintilla 的 Surface 绑定到 HarmonyOS ContentSlot/NodeContent，实现真正在屏幕上渲染文本。

**技术方案**：
- 使用 `OH_ArkUI_NodeContent_RegisterCallback` 注册 Attach/Detach 回调
- 使用 `OH_ArkUI_RegisterDrawCallbackOnNodeHandle`（API 15+）注册绘制回调
- 在绘制回调中将 `ArkUI_DrawContext*` 转换为 `OH_Drawing_Canvas*`，传入 Scintilla
- 实现 `WindowImplOHOS`：持有 NodeContent 尺寸，Invalidate 触发重绘

**需实现**：
1. `ScintillaHost` 类（C++，~200 行）：
   - 持有 Editor + Surface + NodeContentHandle
   - `OnDraw()` → 调用 Editor::Paint(surface, rect)
   - `OnAttach()` / `OnDetach()` 生命周期管理
   - 尺寸缓存 + 更新
2. `WindowImplOHOS` 改造（~100 行）：
   - `InvalidateAll()` → 标记脏区域 + 请求重绘
   - `GetPosition()` → 返回实际尺寸

**产出**：
- patches/0002-contentslot-integration.patch
- 可在设备上运行的 Demo（纯 C++ Native 层）

---

## Phase 6：输入事件桥接

**目标**：将触摸/键盘/鼠标事件从 ArkUI 转发到 Scintilla Editor。

**技术方案**：
- 通过 `ArkUI_NativeNodeAPI_1` 注册触摸/键盘事件回调
- 将 ArkUI 事件参数转换为 Scintilla 的 Point / KeyMod / KeyDef
- 调用 Editor::ButtonDown / ButtonMove / ButtonUp / KeyDown / CharAdded

**需实现**：
1. 事件转换函数（~150 行）
2. 手势处理：单击/双击/长按/拖拽/捏合缩放（~100 行）

**产出**：
- patches/0003-input-event-bridging.patch

---

## Phase 7：IME 输入法适配

**目标**：支持中文等非 ASCII 输入。

**技术方案**：
- HarmonyOS IME 通过 ArkUI 输入法框架回调
- 实现 `Sci_Notify` SCI_URICHANGED 通知机制
- 预编辑（composition）字符串显示 + 候选窗联动

**需实现**：
1. IME 回调注册（~80 行）
2. PreeditString 处理（~100 行）

**产出**：
- patches/0004-ime-support.patch

---

## Phase 8：剪贴板适配

**目标**：支持系统剪贴板复制/粘贴/剪切。

**技术方案**：
- 使用 `@ohos.pasteboard` 系统剪贴板 API（通过 NAPI 回调）
- 实现 SCI_COPY / SCI_CUT / SCI_PASTE 命令处理

**需实现**：
1. 剪贴板桥接接口（~80 行）

**产出**：
- patches/0005-clipboard-support.patch

---

## Phase 9：CMake 构建系统

**目标**：将 Scintilla 以 CMake 静态库形式集成到 BlueNotePad 工程。

**需产出**：
- `scintilla/CMakeLists.txt`（~80 行）
- 编译配置：针对 HarmonyOS SDK 的工具链文件
- 头文件安装规则
- 依赖声明（libnative_drawing.so）

---

## Phase 10：设备运行验证

**目标**：在真机/模拟器上端到端验证所有功能。

**测试项**：
1. 文本渲染正确性（中英文、多字号、颜色）
2. 光标移动、选择、删除
3. 滚动流畅性
4. 大文件（>10MB）性能
5. IME 中文输入
6. 剪贴板操作
7. 语法高亮（至少 3 种语言）
8. 多标签切换

---

## 补充适配：第三方依赖

| 依赖库 | 版本 | 用途 | 适配状态 |
|--------|------|------|---------|
| libiconv | 1.17 | 编码转换（GBK/UTF-16 等） | 🔲 待适配 |
| libcharset | 1.17 | 编码自动检测 | 🔲 待适配 |

> BlueNotePad 技术方案中提到的 Tree-sitter 增强，作为远期目标，Phase 1-10 不涉及。

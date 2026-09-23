# Scintilla 5.6.1 for HarmonyOS — 补丁归档

> 最后更新：2026-09-17 (CI 修复：lld 链接器 libxml2.so.16 加载失败)

## CI 修复记录

### Fix-CI-001: lld 缺 libxml2.so.16 导致 CMake 编译器测试失败（2026-09-17）
- **现象**：CI 构建 #38725 报 `Error loading shared library libxml2.so.16: (needed by .../llvm/bin/lld)` → `clang-15: error: unable to execute command` → CMakeTestCCompiler 失败
- **根因**：OHOS SDK 的 lld 动态依赖 `libxml2.so.16`（位于 `<sdk>/llvm/lib/`）。部分 CI worker 上 lld 的 RUNPATH（`$ORIGIN/../lib`）解析失败，musl loader 找不到该库（知识图谱 E120/E132 同案例：raylib 6.0、libvpx 1.14.1）
- **修复**：`build()` 开头将 `<sdk>/llvm/lib` 注入 `LD_LIBRARY_PATH`（conanfile.py `_inject_linker_env()` + test_package/conanfile.py 同步）
- **关键实现细节**：必须用 `os.environ` 直接修改，**不能用 `buildenv_info`** —— Conan 2 的 VirtualBuildEnv 不聚合 recipe 自身的 buildenv_info，`buildenv_info.append("LD_LIBRARY_PATH", ...)` 会被静默丢弃（已实测验证：conanbuild.sh 中无该变量）
- **验证**：① 复制 lld 到临时目录模拟 RUNPATH 失效 → 复现 CI 同款报错；加 LD_LIBRARY_PATH 后恢复 ② 探测配方实证 os.environ → self.run() 传播链 ③ 干净缓存 conan create 全流程通过（构建 + test_package 链接）

---

---

## 🟢 当前状态：基础编辑功能基本可用

### 已验证功能（设备测试通过）
| 功能 | 状态 | 修复补丁 |
|------|------|----------|
| 应用启动不崩溃 | ✅ | — |
| 文字正常显示 | ✅ | — |
| 光标闪烁(500ms) | ✅ | — |
| **触摸点击定位精确** | ✅ | Patch-0025 (VPR×1.9) |
| **拖选高亮动态变化** | ✅ | Patch-0026 (DoButtonMove T2修正) |
| **单击不误选中整行** | ✅ | Patch-0028+0029 (DOWN/UP全绕过) |
| **英文输入正常（不重复）** | ✅ | Patch-0030c (ArkTS移除功能键fallback) |
| **退格键正常（不删2字符）** | ✅ | Patch-0030c |
| **回车换行正常（不换2行）** | ✅ | Patch-0030c |
| **左右方向键** | ✅ | Patch-0030e (keyCode修正2014/2015) |
| **上下方向键（含边界）** | ✅ | Patch-0032+0032b (GetColumn+FindColumn+边界no-op) |
| **双击选中单词** | ✅ | Patch-0030f (去掉双重除法) |
| **三击选中整行** | ✅ | Patch-0030f |
| **Ctrl+Z/Y 撤销重做** | ✅ | Patch-0033 (Native层Ctrl追踪+SetSavePoint基线) |
| **字母键 a~z 全部正常** | ✅ | Patch-0033c (删除c/d/s错误映射+字母范围保护) |
| **空格键** | ✅ | Patch-0033c (显式处理keyCode=2050) |
| **反引号 ` / 波浪号 ~** | ✅ | Patch-0033c (移除2056→Delete错误映射) |
| **Delete 键** | ✅ | Patch-0033c (case 2047+2071→Delete) |
| **Home/End/PageUp/PageDown** | ✅ | Patch-0033e+0033f (真实keyCode + scintilla映射表修正) |
| **Numpad \*** | ✅ | Patch-0033e (unicode=56→强制插入'*') |
| **Numpad Enter** | ✅ | Patch-0033e (case 2119→Enter) |

### 待验证（代码已修改，待编译测试）

| 功能 | 状态 | 说明 |
|------|------|------|
| **F1-F12 / Insert** | ⏳ 待测（需外接全键盘） | Patch-0033g 已添加映射(1001-1012/2095) |
| **Shift 大写字母** | ⏳ 待测 | Shift 修饰键追踪(g_ctrlPressed 同理) |
| **中文 IME 输入** | ⏳ **待验证** | Patch-0037+0039+0045+0046: 中文IME输入+渲染+代码清理 ✅ 已验证通过 |
| **长按选词/右键菜单** | 🔲 待开发 | 移动端编辑体验 |
| **文件打开/保存** | 🔲 待开发 | 应用层功能 |
| **清理诊断日志** | 🔲 待办 | KEY_DIAG/CTRL_SHORTCUT/KEY_UNMAPPED 等 |

### 架构改进
| 改进 | 状态 | 说明 |
|------|------|------|
| **ArkTS onKeyEvent 精简** | ✅ 已改 | 去掉所有按键处理，只留日志。Native NODE_ON_KEY_EVENT 统一处理，根除双层 bug |
| **Native Ctrl 键状态追踪** | ✅ 已改 | g_ctrlPressed 原子变量追踪 LeftCtrl(2072)/RightCtrl(2073)，解决 NDK 无 GetModifierKey API 问题 |

---

## 补丁历史

### Patch-0034 系列：Native IME InputMethod_TextEditorProxy 对接
- **Patch-0034**: 实现 14 个 TextEditorProxy 回调（InsertText/SetPreviewText/DeleteForward+Backward/SendKeyboardStatus/SendEnterKey/MoveCursor/HandleSetSelection/GetLeft+RightTextOfCursor/GetTextIndexAtCursor/GetTextConfig）
- **Patch-0034-fix**: SetCallbackInMainThread(false) 使 IPC 线程回调可触发（true 时回调挂起不执行）
- **Patch-0034-fix2**: InsertText 改用 ReplaceSel 替代 ChangeInsertion；OnCharInput 跳过非 ASCII 防止双插
- **Patch-0034-fix3**: 补全 handleExtendActionFunc + receivePrivateCommandFunc（ImsaKit IsValidTextEditorProxy 要求所有回调非空）

### Patch-0035: IME/Paste 渲染空白根因修复
- **根因**：`Redraw()` override 只设 `needsRedraw=true`，未调用 `wMain.InvalidateAll()` 通知 ArkTS 宿主触发 OnDraw→PerformDraw
- **现象**：IME 输入中文后 docLen 正确增长但 DrawTextNoClip=0（PerformDraw 根本没被宿主调用）
- **修复**：`Redraw()` 和 `RedrawRect()` 中添加 `wMain.InvalidateAll()` → 触发 `s_redrawRequested()` 回调 → 宿主 XComponent.invalidate() → 下一帧 OnDraw
- **修改文件**：`scintilla/ohos/ScintillaOHOS.cxx` → Redraw()/RedrawRect()
- **状态**：⏳ 待验证（需在设备上测试中文输入和粘贴）

### Patch-0036: Paint 诊断日志
- **目的**：确认 Paint() 是否被调用、ps 状态、rc 值
- **发现**：Paint() 每次都被调用（ps=0 非 abandoned），但首次之后 view.PaintText 零输出
- **修改文件**：`scintilla/ohos/ScintillaOHOS.cxx` → PerformDraw()

### Patch-0037: IME 跨线程 bug 根因修复（**当前重点**）
- **根因**：IME 回调在 IPC 线程(11219)调用 WndProc(ReplaceSel)，主线程(11032)同时在 Paint() → Scintilla 内部状态损坏 → 后续所有 Paint 的 view.PaintText 输出零 DrawTextNoClip
- **证据**：日志显示 `11032-11219 MNP-IME InsertText` vs `11032-11032 MNP-CARET PerformDraw`
- **修复**：
  - 新增 `imePendingText`(string) + `imePendingFlag`(bool) + `imePendingMutex`(mutex)
  - InsertText/SetPreviewText 回调只写缓冲区（加锁），**不再调用任何 Scintilla API**
  - PerformDraw 开头（主线程）检查 flag，消费缓冲区调用 WndProc(ReplaceSel)
- **修改文件**：`scintilla/ohos/ScintillaOHOS.cxx` → 成员变量 + IME回调 + PerformDraw()
- **状态**：⏳ 待验证

### Patch-0039: Canvas 状态保护（已验证通过）
- **根因**：Paint() 内部 SetClip(Save)/PopClip(Restore) 不平衡时，canvas save/restore 栈损坏 → 后续所有绘制操作（包括诊断矩形）被跳过
- **修复**：Paint() 外层包 OH_Drawing_CanvasSave/CanvasRestore，确保无论 Paint 内部如何退出都恢复 canvas 状态
- **修改文件**：`scintilla/ohos/ScintillaOHOS.cxx` → PerformDraw()
- **状态**：✅ 已验证 — 原始文本持续显示正常

### Patch-0040: CJK 字体回退（已被 0041 取代）
- **内容**：FontHandleOHOS 构造函数中 HarmonyOS Sans 失败后尝试 6 种备选字体
- **结果**：全部 MatchFamilyStyle 返回 nullptr → 被 0041 三阶段策略取代

### Patch-0041: CJK 字体三阶段回退 + TOFU 显示模式（**当前重点**）
- **根因**：Patch-0040 的 6 种备选字体全部 `FontMgrMatchFamilyStyle` 返回 nullptr，设备上无匹配的 CJK typeface → 含中文行渲染为空白
- **修复**：三阶段回退策略
  - **Phase 1**: 尝试已知字体名（`HarmonyOS Sans` / `HarmonyOS Sans Condensed` + 原6种备选）
  - **Phase 2**: 运行时调用 `OH_Drawing_GetSystemFontConfigInfo()` 枚举系统所有已注册字体逐个尝试
  - **Phase 3**: 最后手段 — `OH_Drawing_RegisterFont()` 直接注册系统字体文件（`/system/fonts/HarmonyOS_Sans.ttf` 等）
  - **TOFU 模式**：Init() 中调用 `OH_Drawing_SetTextUndefinedGlyphDisplay(TEXT_NO_GLYPH_USE_TOFU)` 使缺失字形显示 □ 而非空白
- **新增头文件**：`drawing_text_global.h`, `drawing_font_collection.h`, `drawing_register_font.h`
- **修改文件**：`scintilla/ohos/ScintillaOHOS.cxx`（Init + 头文件）, `scintilla/ohos/PlatOHOS.cxx`（FontHandleOHOS 构造函数）
- **状态**：⏳ 已被 0045 取代

### Patch-0045: 使用完整 CJK 字体文件（**当前待验证**）
- **🎯 根因最终确认**（经过 0040→0045 共 6 个补丁的排查）：
  - `HarmonyOS_Sans.ttf` (342KB) 是 **Latin-only 子集字体**
  - 有 CJK glyph 表头数据 → FontCountText>0, GetWidths>0, TextBlob≠null
  - 但 **无 CJK 轮廓数据** → Skia rasterizer 输出零像素 → 完全空白
  - 设备上真正的 CJK 字体是 `HarmonyOS_Sans_SC.ttf` (20.6MB, SC=Simplified Chinese)
- **修复**：字体路径改为 `/system/fonts/HarmonyOS_Sans_SC.ttf`
  - 备选：FZHeiT-SC-Regular / FZKaiT-SC / FZFangS-SC（方正中文字体族）
- **修改文件**：PlatOHOS.cxx → FontHandleOHOS 构造函数（fontFilePaths 数组）
- **编译**：2026-04-07 10:09 ✅ (1.33MB)
- **状态**：✅ 已验证通过 — 中文正常显示！

### Patch-0046: 清理所有临时诊断代码（**已完成**）
- **删除内容**：
  - ScintillaOHOS.cxx PerformDraw(): 删除 Paint 前后所有诊断绘制
    (红色矩形、DIRECT TEXT OK、绿色中文测试、POST-PAINT OK、橙色中文ABC、蓝色矩形)
  - PlatOHOS.cxx FontHandleOHOS 构造函数: 删除 CJK 能力检测(FontCountText+GetWidths)
  - PlatOHOS.cxx DrawTextNoClip(): 恢复简洁版日志(移除 hasNonASCII/preview 增强)
- **保留内容**：
  - CanvasSave/Restore 保护(Patch-0039) — 生产必需
  - TOFU 显示模式(Patch-0041) — 无害防御
  - HarmonyOS_Sans_SC.ttf 字体加载(Patch-0045) — 核心修复
  - DrawTextNoClip 前50次基础日志 — 调试友好
- **修改文件**：ScintillaOHOS.cxx, PlatOHOS.cxx
- **编译**：2026-04-07 10:58 ✅ (1.33MB)
- **状态**：✅ 完成





### Patch-0044: Post-Paint CJK 诊断 + DrawTextNoClip 文本内容日志（**当前待验证**）
- **Patch-0043 关键发现**：CJK DIAG SUCCESS 但屏幕上看不到绿色中文 → 被 Paint() 背景填充覆盖！
- **修复内容**：
  - 将 CJK 诊断绘制移到 Paint() 之后（不再被覆盖）：绿色 POST-PAINT OK + 橙色 中文ABC
  - DrawTextNoClip 增强：显示 text 前40字符预览 + hasNonASCII 标志（可看到是否在绘制含中文的行）
  - 日志限制放宽到 100 次
- **关键问题**：如果后置诊断能看到 → 问题在 Scintilla 内部管线；如果仍看不到 → canvas 本身有问题
- **修改文件**：ScintillaOHOS.cxx (后置诊断), PlatOHOS.cxx (DrawTextNoClip 文本预览)
- **编译**：2026-04-07 02:20 ✅ (1.33MB)
- **状态**：⏳ 待设备验证



### Patch-0043: CJK 渲染能力诊断与检测（**当前待验证**）
- **问题**：Patch-0042 字体文件加载成功但中文行仍空白
- **根因分析发现**：
  1. "Raw text SUCCESS" 诊断用的是 TypefaceCreateDefault()+硬编码ASCII，不能证明CJK能力
  2. s_drawTextCount&lt;5 限制掩盖了首帧后 DrawTextNoClip 的真实调用情况
  3. 最可能原因：HarmonyOS_Sans.ttf 加载成功但不含CJK字形 → TextBlob静默失败
- **修复内容**：
  - **方案A**: FontHandleOHOS 构造函数中添加 CJK glyph 能力检测（FontCountText+GetWidths）
  - **方案B**: DrawTextNoClip 放宽日志限制(5→50) + 非 ASCII TextBlob 失败时输出 ERROR 级日志
  - **方案D**: PerformDraw 中用 Scintilla 实际字体(vs.styles[STYLE_DEFAULT].font) 绘制绿色 CJK 诊断文本(y=115)
- **修改文件**：ScintillaOHOS.cxx (方案D), PlatOHOS.cxx (方案A+B)
- **编译**：2026-04-07 01:14 ✅ (1.33MB)
- **状态**：⏳ 待设备验证 — 关注日志中 [Patch-0043] 关键词



### Patch-0042: TypefaceCreateFromFile 直接加载系统字体（**当前待验证**）
- **根因**：Patch-0041 三阶段回退全部失败 — FontMgrMatchFamilyStyle 对所有字体名（包括注册到 FontCollection 的）均返回 nullptr。FontMgr 与 FontCollection 是 Skia 中独立的字体管理器，不共享数据。
- **关键发现**：OH_Drawing API 12+ 提供 `OH_Drawing_TypefaceCreateFromFile(path, index)`，可直接从字体文件创建 typeface，完全绕过 FontMgr 名称匹配。
- **修复**：用 TypefaceCreateFromFile 替换三阶段回退，依次尝试：
  1. `/system/fonts/HarmonyOS_Sans.ttf` (系统默认)
  2. `/system/fonts/NotoSansCJK-Regular.ttc` (ttc 集合: SC/TC/JP/KC)
  3. NotoSansSC / NotoSansCJKsc / SourceHanSansSC (.otf)
- **附带发现**：DrawTextNoClip 日志的 s_drawTextCount<5 限制导致首帧后无日志输出，DrawTextNoClip=0 是假象
- **修改文件**：`scintilla/ohos/PlatOHOS.cxx` → FontHandleOHOS 构造函数
- **编译**：2026-04-06 23:33 ✅ (1.33MB)
- **状态**：⏳ 待设备验证

- **Patch-0033**: Native 层 Ctrl 快捷键拦截（g_ctrlPressed 追踪 + Ctrl+Z→Undo/Ctrl+Y→Redo）
- **Patch-0033a**: ArkTS Z keyCode 修正 2043→2042
- **Patch-0033b**: SetText 后 SetSavePoint() 防止撤销清空全部内容
- **Patch-0033c**: 字母键范围保护 + 空格显式处理 + Delete keyCode 2056→2047 + 移除 Home/End/PgUp/PgDown 错误映射
- **Patch-0033d**: ArkTS onKeyEvent 精简为纯日志（消除双层处理根源）
- **修改文件**：`entry/src/main/cpp/napi_init.cpp`, `entry/src/main/ets/pages/Index.ets`

### Patch-0032 系列：上下方向键列保持（已验证通过）
- **Patch-0032**: Up/Down 完全绕过 SPositionFromLocation，用 GetColumn+FindColumn 纯文档 API
- **Patch-0032b**: 边界情况（首行↑/末行↓）直接 no-op，避免 fall through 到有 bug 的旧路径
- **修改文件**：`scintilla/ohos/ScintillaOHOS.cxx` → DoKeyDown()

### OHOS keyCode 参考表（从日志实测）
| 按键 | keyCode | 备注 |
|------|---------|------|
| a-z | 2017-2042 | 字母范围，不可用于功能键映射 |
| 方向键 ↑↓←→ | 2012-2015 | Up=2013, Down=2012, Left=2014, Right=2015 |
| Home | 2016 | |
| Delete | **2047 / 2071** | ⚠️ 2047被框架拦截，实际设备上报2071 |
| `,` `.` | 2043-2044 | |
| Tab | 2049 | |
| Space | 2050 | unicode=0 需特殊处理 |
| Enter | 2054 | |
| Backspace | 2055 | |
| **反引号 `` ` ``** | **2056** | ⚠️ 不是Delete！ |
| `-` `=` | 2057-2058 | |
| `[` `]` `\` | 2059-2061 | |
| `;` `'` `/` | 2062-2064 | |
| Escape | 2070 | |
| LeftCtrl / RightCtrl | 2072 / 2073 | |

---

## Fix 系列：键盘输入完整修复链（2026-04-08 ~ 2026-04-09）

### Fix-0051: MeasureWidths 字节索引映射（✅ 已验证）
- **根因**：OH_Drawing_FontCountText 返回 Unicode 字符数，Scintilla positions[] 按字节索引 → CJK 行 positions[] 末尾为 0 → 零宽度 → 行不显示
- **修复**：PlatOHOS.cxx MeasureWidths() 新增多字节 UTF-8 路径，glyph→字节索引映射

### Fix-0053: OnKeyDown 过滤修饰键（✅ 已验证）
- **修复**：ScintillaOHOS.cxx OnKeyDown() 入口过滤 keyCode>=2070

### Fix-0054: 2in1 左 Shift 映射 Delete（✅ 已验证）
- **修复**：napi_init.cpp switch 前过滤 diagKeyCode==2047||2048

### Fix-0055: 英文字母 keyUp 输入（✅ 已验证）
- **修复**：napi_init.cpp type 检查后移，允许可打印字符 keyDown+keyUp

### Fix-0055f: IME 会话位置追踪 + 提交时回删（✅ 已验证）
- **新增 API**: BN_Sci_MarkImeSession(), BN_Sci_IsComposing()
- **新增静态变量**: s_imeComposingActive, s_imeSessionStart
- **逻辑**: 字母按键记录 caret → IME 提交时删除 [sessionStart, pos) → 插入中文
- **修改文件**: ScintillaOHOS.cxx, ScintillaOHOS.h

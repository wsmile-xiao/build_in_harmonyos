# DRAFT-7353：依赖宿主 GUI 后端的 header-only 库在无宿主平台的消费者测试模式

> Contributor: wanderlust_0823 (GLM-16 agent) | Status: Draft | Updated: 2026-09-13
> Source: task 7353 feat(raygui): 4.0 适配 OpenHarmony PC（conan-verify G2 迭代链 V4–V12）

## 背景

raygui 4.0 是单头文件即时模式 GUI 库（src/raygui.h，5521 行），默认 `#include "raylib.h"`。
OHOS 无 raylib 包，其 `RAYGUI_STANDALONE` 模式承诺"由用户提供后端"，是头文件库在鸿蒙做
真实消费者测试的唯一通路：测试包以 `RAYGUI_IMPLEMENTATION + RAYGUI_STANDALONE` 编译完整
实现并断言纯逻辑 API 行为。

实测发现：STANDALONE 模式的成本远超其文档描述。raygui.h 实现段（约 4000 行）调用的宿主
符号只有一部分在 STANDALONE 声明区（第 1390–1470 行）声明，其余符号在编译/链接各阶段
逐轮暴露，共收敛八轮（conan create 迭代 V4–V12）。逐轮修错的路径低效且易漏，本条目固化
一次性补齐模式。

## 错误链（八轮收敛，按暴露顺序）

| 轮 | 错误 | 根因层 |
|----|------|--------|
| 1 | `use of undeclared identifier 'BLANK'`（×48 处等） | raylib 颜色宏（BLANK/GRAY/RED/BLACK/WHITE/BLUE 等 26 个）无定义 |
| 2 | `use of undeclared identifier 'KEY_DELETE' / 'KEY_HOME' / 'KEY_END' / 'KEY_LEFT_CONTROL' / 'KEY_LEFT_SHIFT'` | STANDALONE 区只定义 6 个键码，实现段还用 6 个以上 |
| 3 | `passing 'int' to parameter of incompatible type 'Color'` | `Fade()` 无声明 → C 隐式声明返回 int |
| 4 | `conflicting types for 'GetMouseWheelMove'` | 用户 stub 返回 int，raylib/raygui 签名是 float |
| 5 | `static declaration of 'MeasureTextEx' follows non-static declaration` | 用户定义 static，先前隐式声明为非 static |
| 6 | `initializing 'Vector2' with an expression of incompatible type 'int'` | 上游 changelog 声称"REMOVED MeasureTextEx dependency"，但 tooltip 路径（约 4940 行）残留一处调用，无声明 |
| 7 | `too many arguments provided to function-like macro invocation` | 用宏实现 Fade 时复合字面量 `{0,0,0,0}` 的逗号被预处理器当参数分隔符 |
| 8 | `undefined symbol: RL_FREE / GetGlyphIndex / GetCodepoint / DrawTextCodepoint / UnloadTexture / GetScreenWidth` | 实现段调用的宿主函数/宏完全无声明，直接落到链接期 |

## 根因

`RAYGUI_STANDALONE` 只是"不 include raylib.h + 自定义 6 个键码 + 声明 16 个输入/绘制/
样式函数"，并不是完备的后端接口。实现段调用的其余宿主符号（颜色宏、键码、RL_FREE 内存
宏、Fade/MeasureTextEx/GetScreenWidth/GetGlyphIndex/GetCodepoint/DrawTextCodepoint/
UnloadTexture）没有声明，在 C 里按"未定义标识符 → 隐式 int 声明 → 与用户定义冲突 →
链接缺符号"四个阶段逐轮失败。任何按官方 standalone 示例（旧版，仅 16 个 stub）写测试的
消费者都会重走这条八轮链。

## 修复模式（一次性补齐，三段式）

**include 之前**（预处理器层 + 前置声明层）：
1. 定义全部宿主颜色宏（26 个，`(Color){r,g,b,a}` 复合字面量形态）；
2. 补缺失键码（KEY_INSERT 260 / KEY_DELETE 261 / KEY_HOME 268 / KEY_END 269 /
   KEY_LEFT_SHIFT 340 / KEY_LEFT_CONTROL 341）；
3. 定义 `RL_FREE` 等分配器宏（`RL_FREE(ptr) free(ptr)`，与 RAYGUI_MALLOC/CALLOC 默认
   malloc/calloc 配对）；
4. **不完整类型前置 typedef**：`typedef struct Color Color;` 等（头文件后续给出完整
   定义，C17 允许同类型重复 typedef）；
5. 为每个"被实现段调用但头文件未声明"的宿主函数给出**类型化原型**——一次性消灭全部
   隐式 int 声明，这是把八轮收敛压成一轮的关键。
   注意：不要用函数式宏实现 Fade 之类（调用点传复合字面量时花括号内逗号会被预处理器
   当作参数分隔符），用原型 + 函数定义。

**include 之后**（定义层）：
6. 按 STANDALONE 声明区的**精确签名**定义 stub。4.0 与旧示例差异极大：
   `GetMouseWheelMove` 返回 float；`GetCharPressed`（非 GetKeyPressed）；
   `LoadFileText`（非 LoadText）；新增 `LoadTextureFromImage / SetShapesTexture /
   LoadCodepoints / UnloadCodepoints / DecompressData / UnloadFileText`。
7. 上游残留调用点（MeasureTextEx）以**非 static** 定义匹配隐式声明次序，与 stub 同 TU。
8. 断言层选无渲染依赖的纯逻辑 API：`GuiGetState`（Enable/Disable 往返）、`GuiIsLocked`
   （Lock/Unlock 往返）、`GuiSetStyle/GuiGetStyle` 回读、`GuiIconText` 非空——这些走
   真实编译出的实现代码路径，满足 R34（禁空壳测试）。

## 验证证据

- task 7353 raygui 4.0 conan-verify G2 迭代 V4→V12：错误类别每轮单调递减，最终
  `conan create` 全绿（test_package 编译 + 运行 + 断言通过），Verdict: PASS；
- 修复后 test_consumer 以 5 组行为断言通过（GuiGetState/GuiIsLocked/GuiGetStyle/
  GuiIconText），未修改上游任何文件、无平台宏补丁。

## 适用范围与边界

- 适用：任何"头文件实现段调用宿主后端 + 有模式开关"的库在无宿主平台的消费者测试
  （raygui/nuklear 类 immediate-mode GUI、可插拔后端的单头编解码器等）。
- 不适用：无模式开关、硬依赖宿主运行时的库——不得伪造运行测试，按 header-only 分发 +
  如实申报（env_unsupported 或仅编译验证），见 fallback。
- 反例：把 stub 写成 printf/空壳"测试"绕过编译（R34 违规）；改上游头文件删除后端调用
  （偏离上游语义，每次升级失效）。

## 查重说明

知识库引擎（engine，关键词 standalone/backend/header-only/raylib/implicit declaration/
undefined symbol 等）检索：命中 E527（GTK 无显示后端的 meson 配置失败，不同域——E527
讲"配置期发现无显示后端"，本条讲"头文件库 STANDALONE 后端符号一次性补齐"）、E247
（静态 C API 的 C++ 运行时 pkg-config 泄漏，不同域）。无同 stem 重复条目，新增价值为
"跨仓库复用的后端补齐三段式模式 + 上游接口残缺的对抗经验"。

# DRAFT — 制品仓发布的 Qt 构建可能裁剪公开 API（头文件与 .so 双缺），能力选择应上移为编译期选项门控

状态: pending-editor-review（Curator 草稿，run klevernotes-1.3.1；正式编号由知识库主编确认）

## 一句规则

制品仓发布的 Qt 构建可能裁剪公开 API（头文件与 .so 双缺）：依赖该 API 的"运行时探测"代码在编译期即失败，能力选择应上移为编译期选项门控，而非补原型或 dlsym。

## 适用面（affected_scope）

任何使用 Qt 公开 API 做运行时能力探测/枚举（样式枚举、能力查询、feature 门控）的 Qt 应用，在 API 可能被发布构建裁剪的平台/制品生态上普遍适用。

## 根因机理（完整因果链，L1 平台/制品语义）

1. 工具实现证据（自包含探针，任何人开新 shell 可跑）：
   ```
   grep -c availableStyles /storage/Users/currentUser/.conan2/p/qtdec*/p/include/QtQuickControls2/qquickstyle.h      # 0
   llvm-nm -D /storage/Users/currentUser/.conan2/p/qtdec*/p/lib/libQt6QuickControls2.so | grep -c availableStyles    # 0
   grep -c setStyle      …/qquickstyle.h    # 1；llvm-nm -D … | grep -c setStyle  # 3（对照）
   ```
   头文件不含 `availableStyles()` 声明，运行时库也不导出该符号——"仅头缺、补原型"路径天然不可用。QuickControls2 发布树另只含 Basic/Fusion/Imagine/Material/Universal 内置样式，qqc2-desktop-style（org.kde.desktop）无发布物。
2. 触发命令：编译含 `QQuickStyle::availableStyles().contains(QStringLiteral("org.kde.desktop"))` 探测代码的应用。
3. 失败点：`error: no member named 'availableStyles' in 'QQuickStyle'`（run klevernotes-1.3.1 round 9 构建失败实证）。
4. 归类：平台制品 API 裁剪面 → 平台能力缺失 → 编译失败阻塞面（非边缘 warning）。

## 推荐方案：compile-time-option-gating

- CMake `option(KLEVER_QQC2_DESKTOP_STYLE "…" ON)`（默认 ON = 保持上游行为）；
- option 关闭分支：`target_compile_definitions(<target> PUBLIC KLEVER_NO_QQC2_DESKTOP_STYLE)`；
- C++ 侧 `#ifdef KLEVER_NO_QQC2_DESKTOP_STYLE` → `setStyle("Basic")`，`#else` → 上游 `setStyle("org.kde.desktop")`；
- `QT_QUICK_CONTROLS_STYLE` 环境变量覆盖路径保留；配方侧以 `-DKLEVER_QQC2_DESKTOP_STYLE=OFF` 映射，可恢复上游行为。

实证：klevernotes 1.3.1 patches 0001（option）+ 0002（define 注入）+ 0003（#ifdef 分支），终轮 CI PASS。

## fallback（退路与权衡）

只使用在册 API：无条件 `setStyle` 期望样式 + QML 侧加载错误处理回退 Basic。诚实权衡：样式缺位时 QML 加载报 `module not installed` 且可能黑屏，需配套错误处理，仅作退路。

## forbid（反模式）

- **为发布包头缺失的 API 手写函数原型声明强链**：.so 同步未导出符号（llvm-nm -D 实证），链接期必败。
- **以 dlsym 探测发布包裁剪符号作为主方案**：需完整函数指针签名，把平台差异探测藏进运行期，违背"能力探测优于平台名硬编码"的可审计性。

## 原则挂钩与族谱

- principles: P013（平台限制必须降级而非绕过）；P004 为**类比引用**——P004 专指源码级 `__OHOS__` 守卫宏，本条为应用级 CMake option 宏（同为"编译期平台隔离"思路，机制不同）
- similar_to: E566-draft-j669539（pending，尚未合入 graph——index 止于 E542；KF6/Qt 制品能力缺位族）、DRAFT-E5xx-ohos-libcpp-missing-ranges-algorithms（OHOS SDK libc++ 裁剪，异源同象：发布构建相对上游 API 存在裁剪面）

## 知识沉淀价值

可复用问题类别："发布构建 API 裁剪面与运行时探测写法冲突"。未来任何 Qt 应用用 `availableStyles`/能力枚举/feature 探测类 API 适配 OHOS 时，编译期即撞同款错误；本条给出探针（grep + nm 双验证）判定"裁剪面"而非版本差异，并给出编译期选项门控的规范解法，避免补原型/dlsym 的不可恢复路径。

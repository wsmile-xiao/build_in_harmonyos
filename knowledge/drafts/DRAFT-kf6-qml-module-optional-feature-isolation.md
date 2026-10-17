# DRAFT — KF6 发布包缺 QML 模块时，可选功能的 import 应隔离到叶子文件并以 Component 状态探测降级

状态: pending-editor-review（Curator 草稿，run klevernotes-1.3.1；正式编号由知识库主编确认）

## 一句规则

KF6 发布包未随附 QML 绑定模块时，可选功能的 import 应隔离到叶子 wrapper 文件并以 `Component.Ready` 运行时探测降级，不得静态 import 于共享/启动路径 QML 文件。

## 适用面（affected_scope）

任何引用 KDE/KF6 或第三方 QML 模块、且部分功能依赖的模块在发布生态可能缺位的 QML 应用。KDE QML 应用在 OHOS 制品生态上普遍适用。

## 根因机理（完整因果链）

1. 工具实现证据：OHOS 制品仓发布的 KF6 库普遍只含 C++ 库与头文件，不构建/不发布 QML 绑定模块。自包含验证：
   ```
   find /storage/Users/currentUser/.conan2/p/kicon*/p -name qmldir | wc -l   # 0
   ```
   （kiconthemes 发布包无任何 QML 模块；kcoreaddons 显式 `KCOREADDONS_USE_QML=OFF`、ki18n 无 i18n-qml——与 E566 同族）
2. 触发：应用某功能静态 `import org.kde.iconthemes`（KIconThemes.IconDialog 图标选择器）。
3. 失败点：QML import 是文件级硬依赖——引擎加载该文件时直接失败并沿加载链向上传播：
   `qrc:/…/ItemPropertiesDialog.qml:9:1: module "org.kde.iconthemes" is not installed`
   （隔离前的实证：整个属性对话框加载失败，与图标选择无关的功能连带不可用。）
4. 归类：平台制品能力缺失，落在可选功能面 → 应降级而非绕过（P013）。

## 推荐方案：qml-import-isolation-runtime-probe

1. **隔离**：把缺失模块的 import 连同其组件的使用收进一个叶子 wrapper 文件（`KIconDialog.qml`：`import org.kde.iconthemes as KIconThemes` + 空派生 `KIconThemes.IconDialog {}`）。该文件不被任何静态 QML 引用。
2. **探测**：消费方以字符串查找延迟创建，并检查组件状态：
   ```qml
   readonly property bool iconDialogAvailable: {
       const c = Qt.createComponent("org.kde.klevernotes", "KIconDialog")
       return c !== null && c.status === Component.Ready
   }
   ```
   探测失败只产生一条 `module … is not installed` 警告，父文件照常加载。可用性判定以 `component.status` 为准，不以警告 absence 为准。
3. **降级**：探测失败时打开等价原生控件（图标名 `Controls.TextField` 对话框），功能降级不失效。

实证：klevernotes 1.3.1 patches 0008/0009（wrapper + ItemPropertiesDialog 改造），终轮 CI PASS + 启动冒烟进入事件循环。

## fallback（退路与权衡）

- 根治：kiconthemes 配方补构建 QML 模块（上游 src/qml 目录，icondialog.cpp 等 QML plugin 源，需 qtdeclarative 依赖）并发布后，删除 wrapper 与探测分支、恢复上游静态 import。
- 过渡期整体砍掉图标选择功能也可行，但功能损失大于文本降级，仅作退路。

## forbid（反模式）

- **静态 import 可能缺位的 QML 模块于共享/启动路径 QML 文件**：缺位沿加载链级联，共享对话框整树失效（ci13 实证），且无降级路径。
- **以警告是否出现判断模块可用性**：警告只是日志副作用，报错时机不保证可编程捕获；应以 `Component.status` 为准。

## 原则挂钩与族谱

- principles: P013（平台限制必须降级而非绕过）
- similar_to: E566-draft-j669539（pending，尚未合入 graph——index 止于 E542；同族根因"KF6 框架包未构建 QML 绑定层"；E566 解决**必需功能的等价替代**——KLocalizedContext/Kirigami.AboutPage 替换，本条解决**可选功能的隔离降级**——技术互补不重叠）
- verification_cmd（自包含，任何人开新 shell 可跑）：
  ```
  find /storage/Users/currentUser/.conan2/p/kicon*/p -name qmldir | wc -l   # 0 = 无 QML 模块
  ```

## 知识沉淀价值

可复用问题类别："发布生态 QML 模块缺位时的可选功能保全"。未来任何 KDE QML 应用（kirigami-addons 全家、kdegames、kde utilities）适配命中 `module "org.kde.*" is not installed` 时，可按本条直接选型隔离降级，避免走"砍功能"或"整对话框失效"的弯路；并给出与 E566（必需功能替代）的选型边界。

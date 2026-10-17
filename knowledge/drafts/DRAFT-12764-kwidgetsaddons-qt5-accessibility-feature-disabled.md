# qt5-qtbase 5.15.2.2 禁用 accessibility：setAccessibleName 家族编译剔除

## 现象

交叉编译 KDE Frameworks 5 GUI 库（kwidgetsaddons 等）到 HarmonyOS PC 时报：

```
src/kpassworddialog.cpp:81:35: error: no member named 'setAccessibleName' in 'QPushButton'
```

调用点本身是标准 Qt API（Qt 5.0+ 就有），在 Linux 上编译无任何问题。

## 根因

制品仓的 `qt5-qtbase/5.15.2.2` 构建时**禁用了 accessibility 特性**：

```
$ grep accessibility src/gui/qtgui-config.h
#define QT_FEATURE_accessibility -1
```

Qt 源码里 QWidget 的这套 API 全部包在条件编译内：

```cpp
// src/widgets/kernel/qwidget.h
#ifndef QT_NO_ACCESSIBILITY
    Q_PROPERTY(QString accessibleName READ accessibleName WRITE setAccessibleName)
    Q_PROPERTY(QString accessibleDescription READ accessibleDescription WRITE setAccessibleDescription)
#endif
    ...
#ifndef QT_NO_ACCESSIBILITY
    QString accessibleName() const;
    void setAccessibleName(const QString &name);
    QString accessibleDescription() const;
    void setAccessibleDescription(const QString &description);
#endif
```

特性禁用 → `QT_NO_ACCESSIBILITY` 定义 → 整块被预处理器剔除 → 上游裸调用
（不带宏检查的）直接编译失败。

## 辨别指纹

- 报错形态：`no member named 'setAccessibleName' in 'QPushButton'/'QWidget'`
- 环境指纹：`qt5-qtbase/5.15.2.2`（制品仓 Qt5 线）
- 确认命令：`grep accessibility <qt5包>/src/gui/qtgui-config.h` 输出 `-1`

## 修复

给每个裸调用点补上游同款守卫（KDE 源码里 kcollapsiblegroupbox.cpp、
kcapacitybar.cpp 本来就这么写，属对齐而非发明）：

```diff
     const QString description = QApplication::translate("KPasswordDialog", "Show Contextual Help");
+#ifndef QT_NO_ACCESSIBILITY
     ui.userEditContextHelpButton->setAccessibleName(description);
+#endif
     ui.userEditContextHelpButton->setToolTip(description);
```

## 边界

- 仅适用 qt5-qtbase 5.15.2.2（当前制品仓唯一 Qt5 线）
- Qt6 线（qtbase 6.11.1）特性集不同，需另行核验
- 守卫不损失实际能力（该 Qt 构建上 accessibility API 本就不可用）

## 实证

- kconfigwidgets5 任务 #12764（calbee21）：kwidgetsaddons5 5.116.0 本地
  填链验证，kpassworddialog.cpp 补守卫后 conan create 全绿
  （2026-09-24）

## 关联

- E537（KF 家族 SONAME）
- E077（ELF 重签名）
- kconfig5 5.116.0 notes（qt5-qtbase 特性集核查先例）

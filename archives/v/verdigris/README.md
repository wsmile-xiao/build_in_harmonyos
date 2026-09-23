# Verdigris

Header-only Qt moc replacement — constexpr QMetaObject generation without moc. Binary compatible with Qt 5.9+ and Qt 6.x.

- 上游仓库: https://github.com/woboq/verdigris
- 许可证: LGPL-3.0-or-later AND GPL-2.0-or-later
- 构建系统: header-only
- 版本: 1.3

## OHOS 适配要点

- Header-only，无需编译，拷贝 `src/wobjectdefs.h` / `src/wobjectimpl.h` 至 `include/`
- 需 C++14 relaxed constexpr，OHOS clang 15 满足
- 消费者测试使用 Qt5 (qt5-qtbase/5.15.2.2) 的 QCoreApplication + W_OBJECT/W_SLOT/W_SIGNAL/W_PROPERTY 验证 QMetaObject（verdigris 1.3 仅兼容 Qt ≤6.3，Qt 6.11 Private API 已断裂）

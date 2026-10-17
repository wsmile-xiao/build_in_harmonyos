# E429 — Qt5 独立模块的 moc 工具路径重定位

## 错误特征

复用已发布 QtBase 的 qmake/mkspecs 构建独立模块时，moc 指向发布者旧工作目录，即使命令行设置 QMAKE_MOC 仍可能被覆盖。

## 触发条件和根因

Qt 5.15.2 的 mkspecs/features/qt_functions.prf 中，qtPrepareTool 优先使用 QT_TOOL.moc.binary，并据此重新赋值 QMAKE_MOC。包中 modules 与 modules-inst 元数据还可能包含旧前缀。

## 解决方案

1. 复制 mkspecs 到本次构建私有目录，按当前 Conan 依赖包前缀重定位 modules-inst 元数据。
2. 在 qmake 命令中显式传入 QT_TOOL.moc.binary，rcc 同理。
3. 保持源码和影子构建相同目录层级，检查生成 Makefile 的 MOC 命令与当前依赖一致。

不要修改共享依赖缓存，不要写死发布者机器路径，也不要以空脚本替代 moc。

## 验证

QtSql 5.15.2 在鸿蒙原生环境中完成 SQL 库、QSQLITE 驱动和 13 个上游测试程序构建；conan-verify 通过。测试结果为 252 passed、0 failed、86 skipped，跳过项按上游条件执行。此条目只解释工具重定位，不声称单独设置该变量可修复所有 Qt 构建问题。

上游依据：QtBase v5.15.2 的 mkspecs/features/qt_functions.prf，qtPrepareTool 函数。

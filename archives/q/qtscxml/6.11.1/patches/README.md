# qtscxml 6.11.1 补丁目录说明

本配方为 purity 适配（仅配方层修改），**无源码补丁**。

原因：
- 官方源码 `qtscxml-everywhere-src-6.11.1.tar.xz`（SHA256=8e495245e5d1fe75de612c8a07e4043635407a1979bb1dd588f1751d1390203f）
  经 Scout 风险扫描，在 OHOS 上无 dlopen/fork/X11/QProcess 等风险调用。
- 配方为完整 QML 构建（依赖 qtbase/6.11.1 + qtdeclarative/6.11.1，
  scxml-qml/statemachine-qml/scxml-ecmascriptdatamodel 三个 QML feature 全开），
  QML 插件（ScxmlQml/StateMachineQml/ecmascriptdatamodel）与上游 tests/auto 全量
  17 个测试均由官方源码直接构建运行，无需修改上游源码，故无补丁。
- qtbase 侧已提供的适配（harmonyos-clang mkspec、Platform/HarmonyOS.cmake、
  -DQT_NO_ARM_AES_INTRINSICS）由依赖链继承，无需在本仓库重复打补丁。

# Bear — OpenHarmony 编译档案

## 软件简介
Bear (Build EAR) 是编译命令捕获工具，通过拦截编译调用生成 compile_commands.json，用于 IDE 集成和静态分析。

## OHOS 适配要点
- CMake 构建，依赖 grpc（bundled 第三方库）
- 需要补丁修改 CMakeLists.txt 的平台检测逻辑

## 参考资料
- [Bear GitHub](https://github.com/rizsotto/Bear)

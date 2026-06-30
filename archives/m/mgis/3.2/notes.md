# mgis 3.2 编译记录

## 编译日期
2026-06-15

## 编译环境
- 编译器: Clang 15.0.4
- 构建系统: CMake
- 依赖: TFEL 5.2.0-dev

## 源码获取
从已有源码目录编译: ~/tmp/builds/mgis-3.2-src

## 补丁应用
已应用以下补丁（补丁已在源码中）：

1. **cmake/modules/FindTFEL.cmake**: 添加 TFELSystem/TFELUtilities 依赖查找
2. **include/MGIS/Config-c.h**: 修复 Clang 属性语法，使用 C++11 属性语法
3. **include/MGIS/ErrorBacktrace.hxx**: 调整属性顺序为 `[[nodiscard]] MGIS_EXPORT`
4. **include/MGIS/Behaviour/MaterialStateManager.hxx**: 添加 Context 前向声明

## 编译选项
- `-Denable-mgis-function=OFF`: 禁用 mgis-function（C++20不支持）
- `-Denable-python-bindings=OFF`: 禁用 Python 绑定
- `-Denable-c-bindings=OFF`: 禁用 C 绑定
- `-Denable-fortran-bindings=OFF`: 禁用 Fortran 绑定
- `-Denable-static=ON`: 启用静态库编译

## 编译过程
1. CMake 配置成功（39.5s）
2. 编译成功（单线程编译）
3. Staging 安装成功（DESTDIR模式）

## 编译结果
- 动态库: libMFrontGenericInterface.so (1.2M)
- 静态库: libMFrontGenericInterface-static.a (1.2M)
- 头文件: 46个文件（包括 Behaviour, MaterialProperty, Model, Utilities 子目录）

## 跳过测试
测试可执行文件未构建，跳过测试。

## 编译警告
- BehaviourDescription.cxx: 非void lambda在部分控制路径未返回值
- Behaviour.cxx: 符号比较警告（int vs unsigned）

---

**编译结束**: 2026-06-15 12:51
**最终状态**: 编译成功

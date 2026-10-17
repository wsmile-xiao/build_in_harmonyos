# hexdump

hexdump 是一个轻量级 C++14 头文件库，通过 C++ 流（`std::ostream`）将内存内容
格式化为与 Linux `hexdump` 命令风格一致的十六进制转储输出。

## 功能概述
- `Hexdump(data, length)`：默认 16 字节/行 + ASCII 面板输出
- `CustomHexdump<RowSize, ShowAscii>`：可配置行宽与 ASCII 开关
- `CustomHexdumpBase<T, RowSize, ShowAscii>`：类型化模板实例化
- `getLength()` 公开访问器；空长度输入无输出
- Header-only、零依赖、BSD-3-Clause 许可

## OHOS 适配
- Header-only 库，无编译阶段：Conan 配方采用 header-library 模式，
  `build()` 仅应用补丁（当前 patches:{} 为空），`package()` 直接拷贝
  `hexdump.hpp` 到 include/，零源码修改
- 上游顶层 Makefile 硬编码 `g++`（OHOS 工具链仅有 clang++）：配方不依赖
  上游 Makefile，验证用 `clang++ -Wall --pedantic -std=c++14` 等价命令
- 鸿蒙专项测试 `ohos_special_test.cpp`（10 断言 ALL PASS）+ test_package
  消费者测试 `test.cpp`（13 断言 ALL PASS）
- 上游无测试套件（source_declared_total=0），双口径台账见
  `1.0.0/reports/knowledge-candidate-ledger.md`

## 依赖关系
- **编译依赖**: 无（header-only，仅依赖 C++14 标准库）
- **运行依赖**: 无

## 参考资料
- 官网: https://github.com/FernandoVelcic/hexdump
- 文档: https://github.com/FernandoVelcic/hexdump (README.md)

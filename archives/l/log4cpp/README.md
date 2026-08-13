# log4cpp

log4cpp 是一个 C++ 日志库，提供日志分类、优先级、Appender、Layout、
滚动文件、属性配置和嵌套诊断上下文等功能。

## 版本

| 版本 | 状态 | 构建系统 | 本地验证 |
|------|------|----------|----------|
| 1.1.6 | built | CMake | 上游 CTest 17/17，消费者断言 17/17 |
| 1.1.4 | pending | CMake | Autotools 上游测试 12/12，Conan 消费者 smoke 4/4，OHOS CI #11624 通过 |

## OHOS 适配

- 使用 Conan 2 配方构建静态库 `liblog4cpp.a`
- 开启位置无关代码
- 保留并在原生构建中执行全部上游 CTest
- 提供独立消费者测试验证打包后的公共 API
- 无源码补丁和第三方 Conan 依赖
- OpenHarmony API 20 SDK 下库、17 个上游测试目标和消费者目标均可编译链接
- 消费者交叉编译产物为 ELF64 AArch64
- 1.1.4 版本作为 FastNetMon 适配依赖保留，构建时生成 Autotools 风格
  `log4cpp/config.h` 供上游 CMake 使用

本地交叉编译不等同于鸿蒙 PC 真机运行。运行验证仍以赛事官方 CI
和真机结果为准。

## 上游

- 仓库：https://github.com/log4cpp/log4cpp
- 主页：https://log4cpp.sourceforge.net
- 许可证：LGPL-2.1-or-later

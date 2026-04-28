# distcc

distcc 是一个分布式 C/C++ 编译系统，可以将编译任务分发到网络中的多台机器上并行执行，显著加快大型项目的编译速度。

## 功能概述
- 透明分布式编译（通过 masquerade 模式）
- 支持 C、C++、Objective-C 等语言
- 自动负载均衡
- 支持多种编译器（gcc, clang, msvc）
- SSH 加密传输

## OHOS 适配
- 需要更新 config.guess/config.sub 以识别 HarmonyOS 平台
- configure 脚本需要适配交叉编译环境
- src/stats.c 和 src/where.c 涉及平台特定头文件和 API

## 依赖关系
- **编译依赖**: 无特殊依赖
- **运行依赖**: gcc 或 clang 编译器

## 参考资料
- 官网: https://distcc.github.io/
- 源码: https://github.com/distcc/distcc

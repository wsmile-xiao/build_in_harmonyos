# sljit

无栈平台无关 JIT 编译器。sljit 提供与 CPU 无关的低层中间表示（LIR），
可在运行时生成接近手写汇编性能的机器码，适合作为字节码翻译与正则等
JIT 编译库的代码生成后端。

- 官网: https://zherczeg.github.io/sljit/
- 上游源码: https://github.com/zherczeg/sljit
- 许可证: BSD-2-Clause

## OHOS 适配

- 构建系统：纯 GNU Makefile（`make`）。无 configure、无 CMake install。
- 平台：支持 aarch64（HarmonyOS PC 目标架构，含 ARM64 后端）。
- 上游 `make` 双测试二进制（`bin/sljit_test` + `bin/regex_test`）已在
  build() 中集成；逐二进制日志 + 退出码判定并输出 HMBS 标记。
- 适配补丁：无。

## 依赖

- 无第三方构建依赖。

## 参考

- https://github.com/zherczeg/sljit

# fastmod

fastmod 是一个无外部依赖的 C/C++ header-only 库，为 64 位硬件提供快速的 32 位除法、取余和整除判断。

## OHOS 适配

- 采用上游 CMake `INTERFACE` target，安装 `include/fastmod.h` 及 CMake package metadata。
- 不生成 `.a`/`.so` 或可执行文件，不需要 `commands.json`。
- Conan 消费者测试直接调用无符号、有符号的除法/取余 API，并检查模板接口。

## 参考

- 上游仓库：https://github.com/lemire/fastmod
- 许可证：Apache-2.0

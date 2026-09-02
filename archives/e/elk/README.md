# elk

Elk 2.2.0 是面向嵌入式应用的 C 语言 JavaScript 引擎。本适配提供静态库和
`elk::elk` CMake consumer target。

## HarmonyOS 适配

- 上游仓库：https://github.com/cesanta/elk
- 版本：2.2.0
- 许可证：AGPL-3.0-or-later
- Conan 引用：`elk/2.2.0`
- 适配路径：路径 A（基础适配）

配方使用 OHOS profile 的 clang/llvm-ar，并显式传递给上游 Makefile；上游 C 单元
测试和消费者 API smoke test 均在 HarmonyOS aarch64 设备通过。

详细测试统计见 [2.2.0/notes.md](2.2.0/notes.md) 和
[2.2.0/test_package/MANIFEST.yml](2.2.0/test_package/MANIFEST.yml)。

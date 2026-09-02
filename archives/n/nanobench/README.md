# nanobench

nanobench 4.6.0 是 C++11 及更高版本的微基准测试库。本适配安装上游
`nanobench.h` 和静态库，并提供 `nanobench::nanobench` CMake consumer target。

## HarmonyOS 适配

- 上游仓库：https://github.com/martinus/nanobench
- 版本：4.6.0
- 许可证：MIT
- Conan 引用：`nanobench/4.6.0`
- 适配路径：路径 A（基础适配）

测试统计严格区分源码声明数（150）、C++11 实际注册数（147）和设备运行结果
（145 通过、2 跳过）；没有把未编译或显式跳过的用例冒充为通过。

详细测试统计见 [4.6.0/notes.md](4.6.0/notes.md) 和
[4.6.0/test_package/MANIFEST.yml](4.6.0/test_package/MANIFEST.yml)。

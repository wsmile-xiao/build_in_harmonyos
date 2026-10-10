# cpp-yyjson `cpp-yyjson` 移植记录

## 上游与包身份

- 上游仓库：[yosh-matsuda/cpp-yyjson](https://github.com/yosh-matsuda/cpp-yyjson)
- 源码固定到 upstream main 快照 `267616b822ae79495955f8593868cb07ef63ee47`，源码 SHA-256 见 `conandata.yml`。
- 用户指定 Conan 版本号为字面值 `cpp-yyjson`；这是 main 快照标识，不是上游发布 tag。Conan 包身份为 `cpp-yyjson/cpp-yyjson`。
- 上游默认使用源码中捆绑的 yyjson C 后端，因此本配方没有外部 yyjson 运行依赖。GTest 仅用于上游构建测试。

## HarmonyOS 适配

HarmonyOS PC SDK 提供 Clang/Clang++ 15.0.4。该 libc++ 缺少 `<format>` 与 `<source_location>`，部分 ranges 算法也不可用；Clang 15 还不支持 lambda 捕获结构化绑定。归档补丁保持上游 API 和测试覆盖，使用能力检测与标准算法回退：

1. `0001-test-test.cpp.patch` 用 libc++ 15 可用的格式化回退适配上游测试，并修正 `Readme.Example` 中将 `serialized5` 错引用成 `serialized` 的笔误；格式化结果断言使用明确期望值。
2. `0002-include-cpp_yyjson.hpp.patch` 为格式化 API 加能力检测回退，替换不可用的 ranges 算法，并规避结构化绑定捕获。
3. `0003-include-field_reflection.hpp.patch` 在缺少 `<source_location>` 时回退到 `__PRETTY_FUNCTION__`。

补丁没有加入 HarmonyOS 专用预处理宏，均基于标准库能力检测或标准算法。

## 验证环境与结果

- 设备：HarmonyOS 6.0 PC，`uname` 报告 `HarmonyOS/aarch64`。
- Conan 2.29.1，Clang/Clang++ 15.0.4，CMake 4.1.2，仓库 `ohos-aarch64` profile。
- 上游测试清点：快照中的 `test/test.cpp` 有 31 个 GoogleTest `TEST` 声明；`test/CMakeLists.txt` 用 `gtest_discover_tests` 将这些用例注册给 CTest。
- Conan 配方在 Conan 构建目录运行 `ctest --output-on-failure`；该命令也可在同一目录独立复跑。
- 上游 GoogleTest：31/31 通过。
- Conan `test_package`：消费者 JSON 解析/容器转换/序列化回读通过；HarmonyOS 专项测试通过。专项测试检查 `uname()` 的系统与架构，并实际执行结构反射 JSON 往返和 JSON 解析。
- 仓库 `ci/conan/build_and_test.sh`：1 个包成功、0 个失败；L0、L1、L4、L5 通过。L2 因该库没有 `bin/` 可执行文件而按规则跳过。
- CI 的 R34 负向依赖测试通过：临时移走已安装包的 `include/` 与 `lib/` 后，消费者测试不能再依赖被测包的产物。

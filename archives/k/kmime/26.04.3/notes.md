# kmime 26.04.3

本配方对应 KDE PIM 26.04.3 发布版本。KDE PIM 软件包版本与 KF6 框架依赖版本是独立版本轴，依赖仍需按各框架软件包要求声明。上游 CTest 共 15 个目标：`autotests/CMakeLists.txt` 的 13 个 QtTest 目标，加 `tests/CMakeLists.txt` 的 `test_charfreq` 与条件目标 `test_mdn`（需要 `HAVE_GETOPT_H`）。配方在 `BUILD_TESTING=ON` 下从 build root 运行完整 CTest。HarmonyOS PC AArch64、Clang 15 上，独立 Conan `create` 退出 0，上游 CTest 15/15 通过（含 `test_mdn`），原生 Conan 消费者测试 1/1 通过。

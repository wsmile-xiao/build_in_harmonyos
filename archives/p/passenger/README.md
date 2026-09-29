# passenger HarmonyOS PC 适配

本目录包含 Phusion Passenger 6.1.8 的 HarmonyOS PC Conan 适配。配方打包上游
native-packaging 源码树，为六个用户命令生成包内转发脚本，生成指向当前包实例的
`locations.ini`，并在 `conan create` 中执行上游 OXT 测试套件。

源码使用 GitHub tag archive，而不是 release 页面提供的发布资产。release 资产缺少
上游 `test/` 目录，无法复现上游测试；tag archive 才包含完整源码和测试树。

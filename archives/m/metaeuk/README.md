# metaeuk OpenHarmony 编译记录

MetaEuk 是面向大型真核基因组的基因查找与蛋白注释工具，基于内嵌的
MMseqs2 库（上游 tag 归档自带 `lib/mmseqs/`，零外部 conan 依赖），
通过蛋白相似性拼接外显子、预测蛋白编码基因，提供 `easy-predict`
等一站式工作流子命令。

本目录当前包含 7-bba0d80 首适版本（GitHub tag 归档 tarball）：

- 单二进制 `bin/metaeuk`（子命令：easy-predict / predictexons /
  taxtocontig / reduceredundancy / unitesetstofasta / groupstoacc 等，
  data/ 下的 shell 工作流脚本已编译为内嵌资源）

OHOS 适配要点（详见 7-bba0d80/notes.md）：

1. 上游声明 CMake 2.8.12，设备 CMake 4.1.2 需
   `CMAKE_POLICY_VERSION_MINIMUM=3.5`；
2. tag tarball 无 `.git`，按上游机制传 `VERSION_OVERRIDE=7-bba0d80`，
   实测裸 `metaeuk`（非 tty）退出码 0 且 stdout 含
   `metaeuk Version: 7-bba0d80`；注：`--version` 并非合法子命令，
   会以非零退出，版本横幅只能从裸调用取得；
3. `NATIVE_ARCH=0 + HAVE_ARM8=1` 固定 aarch64 基线 NEON 编译路径；
4. 上游无**注册**的自动化测试（全源码树 `add_test(`/`enable_testing`/
   `include(CTest)` 实测 0 命中，无 automake `TESTS`；`tests/` 与
   `lib/mmseqs/util/regression` 两个子模块不随 tag 归档发布），
   N_static=0 如实申报，test_package 以被测二进制真实运行断言补位。
   随包的 `lib/mmseqs/src/test/`（36 个 .cpp，35 个自带 `int main`）系上游
   手工自测 harness，在本包配置下因 `FRAMEWORK_ONLY=1` 强制早退而不参与
   构建、其 `mmseqs_setup_test()` 也不含 `add_test()`，故不计入用例数
   （清点依据见 7-bba0d80/notes.md §4）。

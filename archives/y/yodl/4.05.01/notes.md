# Yodl 4.05.01 HarmonyOS PC 移植记录

## 上游与来源

- 上游项目：https://gitlab.com/fbb-git/yodl
- 官方版本页：https://fbb-git.gitlab.io/yodl/
- 固定源码归档：`yodl-4.05.01.tar.bz2`
- SHA-256：`9591b2fdba60d8e9c37edd8c61ea3e13e7a224ee5783cda9cfcef2773ac7c84b`
- 许可证：AGPL-3.0-only

## 构建适配

上游 `build` 与 `verbinsert` 使用 icmake/icmbuild 编排。移植配方不引入
icmake 依赖，改用 CMake 直接构建归档内的 C/C++ 源码，并按上游规则生成
`gram.h`、`builtins.def`、配置头文件和标准宏文件。只打包运行时程序和宏；
LaTeX、Ghostscript 仅用于上游手册构建，不作为本包依赖。

安装内容留在 Conan 私有 package prefix：`bin/` 下的 Yodl 程序、转换脚本，
`share/yodl/` 下的宏数据，`licenses/` 下的许可证与说明。运行环境通过
`YODL_BIN`、`YODL_INCLUDE_PATH` 指向当前 package，不写入系统共享目录。

## R51 上游测试清点与运行记录

清点对象是官方 `yodl-4.05.01.tar.bz2` 解压后的完整源码树。对源码树执行
`find <source-root> -type d -name tests -print` 与
`find <source-root> -type d -name test -print`，均无输出：测试目录数为 0。
对 `CMakeLists.txt`、`*.cmake`、`Makefile`、`Makefile.in`、`*.mk`、`*.im` 和
`icmake*` 执行 `grep -RniE 'add_test|enable_testing|pytest|unittest|^test:|^check:'`，
无匹配：ctest/pytest 注册数为 0，test/check 构建目标数为 0。故上游测试总数
N=0、实际可运行数 N′=0、通过率不适用（源码中没有上游测试可运行）。

适配后新增一个 HarmonyOS PC 消费者集成用例，由 `test_package/test_yodl.sh`
执行；在 HarmonyOS 6.0 aarch64 设备上通过（1/1，100%），覆盖平台与架构识别、
版本输出、Yodl 文本转换、`yodlverbinsert -a` 及缺失输入错误处理。

## 验证记录

- HarmonyOS 6.0 aarch64 原生 CMake 构建、安装通过，使用 Clang/Clang++ 15.0.4。
- `conan create` 从干净导出源码构建并执行 `test_package`，通过。
- 仓库 `ci/conan/setup.sh` 与针对 `archives/y/yodl/4.05.01` 的 `ci/conan/build_and_test.sh` 通过：L0、L1、L2、L4、L5 均通过；R34 破坏性反向验证确认测试确实依赖包内程序。
- HarmonyOS 专属 consumer test 检查系统标识与 aarch64，运行 `yodl --version`、Yodl 到纯文本转换、`yodlverbinsert -a` 转换，并确认缺失输入返回失败。
- CI 的可选帮助/版本探测对 `yodl2ms`、`yodl2sgml`、`yodlpost` 和 `yodlverbinsert` 有非阻塞提示；这些辅助入口不实现相应选项。转换和针对性测试已通过。
- HarmonyOS HNP shell 在 HMDFS 工作目录下会输出 `getcwd` 诊断，但不影响构建、安装或测试退出状态。

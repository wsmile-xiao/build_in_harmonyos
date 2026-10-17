# shhopt 1.1.7 适配笔记

## 编译环境

- 目标系统：HarmonyOS 6.0 PC aarch64
- 构建系统：Makefile
- 编译器：Clang 15.0.4
- Conan：OHOS 适配版 2.29.1
- 编译日期：2026-09-18
- 状态：built（本地验证通过，未上传）

## 上游与源码完整性

- 官方主页：https://shh.thathost.com/pub-unix/
- 官方源码包：https://shh.thathost.com/pub-unix/files/shhopt-1.1.7.tar.gz
- 官方源码包 SHA256：`bae94335124efa6fcc2f0a55cabd68c9c90be935bcdb8054d7e5188e0d5da679`
- 许可证：Artistic License 1.0（上游 README 的 License 节）

## 编译步骤

1. `source()` 下载并校验官方 1.1.7 源码包。
2. 将上游 `Makefile`、`shhopt.c` 和 `shhopt.h` 复制到独立构建目录。
3. 从 Conan `tools.build:compiler_executables` 获取 HarmonyOS Clang，并覆盖上游默认的 gcc 与 `-s` 参数。
4. 默认构建并打包 `libshhopt.a`；`shared=True` 时构建版本化共享库，并以实体 `libshhopt.so.1` 和 `libshhopt.so` 别名规避 HMDFS 软链。
5. Conan `test_package` 编译、链接并运行两个消费者测试程序。

## 适配问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile 默认调用 gcc 且编译参数包含 `-s` | 2002 年的构建脚本未感知 Conan/HarmonyOS 工具链 | 配方从 Conan 配置读取 C 编译器并显式覆盖 `CCOPT` |
| 2 | 上游共享库 SONAME 为 `libshhopt.so.1`，安装规则创建两个版本软链 | HMDFS 上软链语义不适合作为可复现包布局，缺少主版本名会导致动态加载失败 | 保留版本实体，并复制同内容的 `libshhopt.so.1` 与 `libshhopt.so` 实体别名 |

## 源码修改

无。库源码只使用标准 C/libc 接口，在 HarmonyOS musl 上可直接编译运行；构建差异全部由 Conan 配方参数处理。

## 依赖版本

无第三方依赖；仅使用 HarmonyOS libc。Make、Clang 和 Conan 是构建工具，不作为运行时依赖传播。

## 上游测试账本

- 静态清点：发布包共 10 个文件；无 `tests/`、`test/` 目录，无测试源文件，无测试框架配置。
- 动态清点：`make -n check` 和 `make -n test` 均报告没有对应目标。
- `example.c` 是 README 明确引用的示例程序，不含断言或测试框架，不能冒充上游测试。
- 上游实测测试数：0；不存在可跳过或可删减的上游测试。

## 新增测试

- `test_shhopt.c`：16 个断言，覆盖 flag、string、int、unsigned int、long、unsigned long 全部参数类型，以及普通回调、自定义致命错误回调、组合短选项、长选项内联参数、`argv` 清理、单横线与 `--` 行为。
- `test_shhopt_ohos.c`：5 个鸿蒙特有断言；编译期强制 `__OHOS__` 与 aarch64，运行期验证 LP64 ABI、`LONG_MIN`、`LONG_MAX`、`ULONG_MAX` 的解析以及负数位置参数保留。
- 合计 21 个新增断言，严格不少于上游实测的 0 个测试，且包含独立鸿蒙特有测试。

## 交付物

- `lib/libshhopt.a`（默认）或共享构建的 `lib/libshhopt.so.1.1.7`、实体 `lib/libshhopt.so.1` 与 `lib/libshhopt.so`
- `include/shhopt.h`
- `licenses/README`（含上游 Artistic License 声明）

## 注意事项

- 本库不是 HarmonyOS 系统同名库，默认保持上游静态构建行为，不创建 `commands.json`。
- 上游没有正式自动化测试；测试数量按实际清点和执行结果申报为 0，新增测试不冒充上游测试。
- 状态为 `built`，因为本任务明确禁止上传、提交或创建 PR。

---

**编译结束**: 2026-09-18 UTC
**最终状态**: built

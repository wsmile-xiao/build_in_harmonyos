# Snow 2.3.2 HarmonyOS PC 适配笔记

## 软件与构建方式

Snow 2.3.2 是一个使用 MIT 许可证的 C 语言单头文件测试库。配方不生成库文件，
只安装 `include/snow/snow.h` 和许可证，并通过 `package_id()` 清除与编译设置相关的
包 ID。

- 上游仓库：https://github.com/mortie/snow
- 官方标签：`v2.3.2`
- 官方源码 SHA-256：`410694deef79fde5d1515e1722d0b2af68cc9d1eef816db4f4495e01ae1f9a6a`
- 第三方依赖：无
- 验证编译器：DevEco Studio OHOS Clang 15.0.4
- 验证目标三元组：`aarch64-linux-ohos`、`x86_64-linux-ohos`
- 运行环境：Huawei_2in1 HarmonyOS 6.0 x86_64 虚拟机（系统报告 `OpenHarmony-6.0.0.47`）

## 上游测试集成

上游 `test/Makefile` 会在测试阶段再次从 GitHub 克隆 Snow，并强制通过 Valgrind
运行测试。该流程不适合离线的干净 CI，也无法在 HarmonyOS PC 上依赖 Valgrind。
配方直接使用同一官方归档中的测试源码，保持上游的严格编译选项：

1. 使用 `-DSNOW_DUMMY_TIMER` 编译 `test/cases/` 下的 4 个 fixture；
2. 编译 `test/test.c` 官方测试驱动；
3. 在 HarmonyOS 原生构建环境执行 `test-snow -q`；
4. Windows 宿主交叉编译时从上游 `test/` 目录传入 POSIX 相对源码路径，避免
   `__FILE__` 固化为 Windows 路径并破坏官方 golden 输出比对；
5. Conan 在 Windows 宿主阶段只编译目标程序，随后通过 HDC 在 HarmonyOS 虚拟机执行。

官方测试驱动包含 4 个 describe、22 个测试项；测试驱动与 fixture 共包含 149 个
Snow 断言调用。消费者 `test_package` 另含 4 个 Snow 测试项、7 个断言，覆盖整数、
字符串、缓冲区及 musl 不完整类型指针，并包含 1 个独立的 `TMPDIR` 行为回归场景。

## 兼容性问题与补丁

| 补丁 | 问题 | 处理 |
|------|------|------|
| `0001-use-prototype-declarations.patch` | Clang 15 在 `-Wpedantic -Werror` 下拒绝宏生成的旧式 `func()` 声明 | 改为语义等价的 `func(void)` |
| `0002-support-incomplete-pointer-types.patch` | `assertneq(FILE *, NULL)` 通过 `(pointer)+0` 推导类型，HarmonyOS musl 的不完整 `FILE` 类型不允许该指针算术 | 使用 Snow 已依赖的 GNU `__auto_type` 完成数组衰减和类型推导，并局部屏蔽对应扩展告警 |
| `0003-remove-unused-test-variable.patch` | 官方测试驱动中的 `cnt` 只递增但从不读取，在严格告警下失败 | 删除死变量及递增语句，不改变测试逻辑 |
| `0004-honor-tmpdir.patch` | `--gdb` 与版本脚本将临时文件硬编码到 HarmonyOS 上可能只读的 `/tmp` | 优先使用 `TMPDIR`，其次使用 `HOME` 和当前目录，不引入平台条件宏 |

补丁均为通用 C/Clang 可移植性修复，没有增加 `__OHOS__` 平台分支。

## 验证结果

本地执行的 Conan 2.29.1 交叉验证及虚拟机运行结果：

- 官方源码下载和 SHA-256 校验通过；
- 4 个补丁按声明顺序应用通过；
- 对应用补丁后的完整上游源码执行风险预扫，结果为 0 findings；
- 4 个上游 fixture 和 1 个官方测试驱动均通过 OHOS Clang 的 AArch64 与 x86_64 严格编译；
- 头文件和许可证成功打包；
- 2 个消费者测试目标通过 OHOS AArch64 与 x86_64 编译；
- `conan create` 返回 0；
- HarmonyOS 6.0 x86_64 PC 虚拟机上，官方测试通过 22/22；
- 消费者 Snow 测试通过 4/4，`TMPDIR` 行为回归返回 0。

编译状态：built
编译时间：2026.9.3 15:47

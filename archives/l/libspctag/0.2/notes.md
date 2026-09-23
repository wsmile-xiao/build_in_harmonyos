# libspctag 0.2 HarmonyOS PC 适配笔记

## 源码与构建系统

- 官方源码：`https://downloads.sourceforge.net/project/libspctag/libspctag-0.2.tar.gz`
- SHA-256：`a7c6865282c0ba3e119dc28fffaf80dc409f49d042fae38b7670e51bb1baaa57`
- 构建系统：CMake；上游声明 `cmake_minimum_required(VERSION 2.6)`。
- 第三方依赖：无，仅依赖系统 C 库。

## 适配内容

1. CMake 4.x 已移除对 3.5 以前策略版本的直接兼容，配方通过 cache 变量传入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
2. OHOS 配置显式使用 `CMAKE_SYSTEM_NAME=OHOS`，加载 SDK 自带的平台模块并保留共享库 SONAME。
3. 上游强制 `SHARED` 的目标改为服从 `BUILD_SHARED_LIBS`，共享和静态 Conan 选项均可构建。
4. `spctag.h` 原先直接定义四个全局符号，现代静态链接会发生重复定义；补丁改为 `extern` 声明并在 `spctag.c` 唯一定义。
5. 修正二进制日期的未对齐越界读取、日期字符串未终止、三个 `int` API 无返回值，以及短文件读取未检查等未定义行为。补丁不引入 `__OHOS__` 分支。

## 上游测试清点与实测

上游源码仅提供 `test/test.c` 一个可执行样例，没有 `enable_testing()`、`add_test()` 或其他测试目录/入口。该样例真实调用全部读取、设置和保存 API，要求传入有效 SPC 文件。配方保持源码不变，为其生成确定性的文本 ID666 fixture，编译并运行样例，同时核验版本输出以及修改后恢复的原始标题输出。

| 类别 | 上游实测数量 | 本适配执行数量 |
| --- | ---: | ---: |
| 单元测试 | 0 | 0 |
| 集成测试（官方样例） | 1 | 1 |
| 其他测试 | 0 | 0 |
| 合计 | 1 | 1 |

消费者侧另有 2 个测试程序：通用文本/二进制 ID666 往返测试（48 条断言）和 OHOS aarch64 专项可写临时目录往返测试（8 条断言）。因此适配测试数量不低于上游实测，并新增了 1 个鸿蒙特有测试。

## 验证命令

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

最终结果以 `reports/test-report.md` 和 `test_package/MANIFEST.yml` 为准。

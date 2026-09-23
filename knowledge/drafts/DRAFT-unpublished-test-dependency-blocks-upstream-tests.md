# 未发布的测试专用 Conan 依赖阻塞完整上游测试

> 状态：本地路径 B 草稿，需人工审核后才可提升为正式知识条目。

## 现象

`skiparray` 的生产库只有 C 源码和标准库依赖，但上游 Makefile 的 `test` 目标通过 `pkg-config --cflags/--libs libtheft` 和 `theft.h` 依赖 `libtheft`。在 OHOS 设备执行测试时，核心对象可以编译，随后出现 `Package libtheft was not found` 与 `theft.h` 缺失。

## 诊断证据

- `conan install --build=never --requires=theft/0.4.5@ohpcd/stable`：本地缓存和 ohpcd 均返回未找到。
- 不使用 `--build=missing`，因为 W0/R36 要求依赖先发布；上游测试依赖不是生产包的运行时依赖。
- `make CC=/data/service/hnp/bin/clang library` 成功生成核心静态库；因此问题边界是测试依赖发布，不是 C 编译器或核心源码不可用。

## 推荐方案

1. 在依赖未发布时，将生产配方与真实 `test_package` 分开验证；test_package 必须调用被测库 API。
2. 在报告和 manifest 中分别写“上游完整 suite 阻塞”和“消费者测试通过”，不能将后者替代前者。
3. 依赖发布后使用精确版本重新执行上游测试，并在新的验证报告中更新静态总数、执行数量和通过率。

## 禁止策略

- 禁止把未发布依赖源码、临时 recipe 或 dummy 包塞入当前软件 PR。
- 禁止用 `--build=missing` 越过依赖发布顺序。
- 禁止删除/跳过上游测试或用 `echo passed` 伪造测试通过。

## 适用边界

适用于 C/C++ 项目的 test-only 依赖未进入目标 Conan remote、但生产库本身可以独立构建的情况；若该依赖是生产库必需依赖，应按 R36 先发布依赖，不能仅做本条的部分适配。

## 实测对象

- 软件：skiparray 0.2.0
- 依赖：theft 0.4.5
- 平台：OpenHarmony PC arm64 / clang 15 / Conan 2.29.1

## 解除记录（2026-09-05）

- 解除条件已满足：`theft/0.4.5` 已于 2026-09-02 合入官方归档并发布到 ohpcd remote（recipe revision `46372da4dacaca771da48de53bf6661d`）。
- 实施方式：生产配方新增 `upstream_tests` 选项（默认 False），仅验证构建时声明 test-only 依赖 `theft/0.4.5`；`can_run` 时用 Conan 包目录替换 pkg-config `libtheft`，编译上游 9 个测试源文件并运行 Greatest 套件。
- 真实验证（OpenHarmony PC arm64，clang 15，Conan 2.29.1）：上游套件 `Total: 67 tests, 67 passed, 0 failed, 0 skipped`（静态 25 处 RUN_TEST(p) 注册经参数化循环展开为 67 个运行用例）；默认选项构建确认生产依赖图不含 theft；消费者 test_package 1/1 通过。
- 边界不变：本条知识的核心结论（test-only 依赖必须与生产依赖图隔离、阻塞必须如实报告）仍然成立；本节仅记录该实例的解除证据。


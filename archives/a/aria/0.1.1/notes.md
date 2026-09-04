# aria 0.1.1 适配笔记

## 编译环境

- 构建系统: custom（上游仅提供 `build.sh`）
- 编译日期: 2026-09-03
- 编译器: Conan OHOS profile 提供的 clang、llvm-ar、llvm-ranlib
- 状态: built（等待 PR CI）
- 适配路径: 路径 B（贡献知识草稿 E543）

## 编译步骤

配方从官方 `v0.1.1` tag tarball 获取源码，使用 Conan profile 的 C 编译器编译
`aria.c`（`-O3 -fPIC -Wall -Wextra -std=c89 -pedantic`），再用 profile 的
`ar` 和 `ranlib` 生成 `libaria.a`。没有使用上游 `build.sh`，因为它固定调用
`/bin/bash` 和 `gcc`；OHOS 验证命令及结果记录在 `reports/device-validation.md`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 初始化脚本将项目误判为 autotools | URL 不含构建系统标识，源码实际只有 `build.sh` | 将版本归档和 Conan 配方明确设为 `custom`，直接复现上游 C89 编译选项 |
| 2 | 上游构建脚本不能直接作为 OHOS 入口 | 脚本使用固定 `/bin/bash` shebang 和 `gcc` 命令 | 配方从 `tools.build:compiler_executables` 读取 clang/ar/ranlib |
| 3 | OHOS CMake 消费者构建出现默认并行参数和 FIFO 权限噪声 | Conan CMake helper 默认追加 `-j20`，OHOS jobserver FIFO 受权限限制 | `test_package` 使用 `cmake.build(build_tool_args=["-j1"])`，实测最终 `-j1` 执行通过 |

## 源码修改

无。上游源码保持不变。

## 依赖版本

无外部 Conan 依赖。源码标签提交为 `5fecc8098730e25834c20717798d89e9869c7ba5`，
归档 SHA-256 为 `52430f355b4f7939009bc20d34c9df75026b538a091e2d33efe81d4329e81786`。

## 验证结果

上游测试清点：未发现 `make check`、CTest、`test/` 或 `tests/`，正式上游测试 0 个。
适配后消费者测试：1 个逻辑用例，调用 arithmetic、string 和 pair C API。
设备端完整命令与结果见 `reports/device-validation.md`；上游测试清单见
`reports/upstream-test-inventory.md`。

## 知识库扩展

新增 `knowledge/drafts/E543-draft-F833.kv` 及配套文档，沉淀单文件 C89 库在 OHOS
上的固定 standalone 构建入口边界、正式测试计数规则和 Conan API 消费者测试模式。
该草稿不修改正式知识图谱索引，随本 PR 走路径 B 供后续主编审核。

## 交付物

| 文件 | 说明 |
|------|------|
| `libaria.a` | C89 静态库 |
| `aria.h` | 公共 C API 头文件 |

## 注意事项

上游示例脚本不是正式测试用例，不能计入上游通过率；归档中的
`test_package/test.c` 仅代表消费者视角补充验证。

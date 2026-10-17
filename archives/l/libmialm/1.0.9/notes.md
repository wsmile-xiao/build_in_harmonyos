# libmialm 1.0.9 适配笔记

## 编译环境

- 系统：HarmonyOS PC（aarch64）
- 构建系统：Autotools
- 编译器：Clang 15
- 依赖：glib/2.88.3.1、libxml2/2.15.3.1

## 编译步骤

Conan 下载并校验官方源码镜像，应用两个平台识别补丁后生成 Autotools 工具链。随后以单任务方式依次执行 `configure`、`make`、上游 `make check` 与 `make install`，最后由 `test_package` 从安装后的包编译并运行消费者测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 无法识别系统 | 上游脚本发布于 2015 年，不包含 HarmonyOS | 新增 aarch64/HarmonyOS 映射 |
| 2 | `config.sub` 拒绝目标三元组 | 合法内核-系统组合中没有 linux-ohos | 同步扩展组合与系统白名单 |
| 3 | `config.status` 临时文件不可写 | HarmonyOS PC 文件系统对私有临时目录的权限语义不同 | 将生成文件定向到配方预建工作目录 |
| 4 | 并行 make 无法创建 jobserver FIFO | 当前文件系统不支持该 FIFO 操作 | 构建、测试和安装固定使用 `-j1` |
| 5 | VPATH 构建找不到 `mialm/*.h` | 上游 Makefile 假定源码内构建的根目录头搜索路径 | 由 Autotools 工具链把源码根目录加入 CFLAGS |
| 6 | 禁用文档后仍调用 `gtkdoc-scan` | 旧版 docs Makefile 未用条件变量保护默认目标 | 仅构建和安装库子目录，继续执行上游 test/check |

## 源码修改

- `0001-config.guess.patch`：识别 HarmonyOS/aarch64 并输出标准 GNU 三元组。
- `0002-config.sub.patch`：接受 `linux-ohos` 内核-系统组合。

## 验证结果

- 上游 `make check`：通过（18 个断言/守卫）。
- Conan 消费者测试：通过（31 个公共 API 检查）。
- HarmonyOS 特有测试：通过（4 个平台与公共 API 联动检查）。
- 新增测试合计：35/35；连同未修改的上游测试共 53/53。

## 结束标记

**编译结束**: 2026-09-23（HarmonyOS PC aarch64 真机端完整 Conan 构建、上游测试及消费者测试均通过）
**最终状态**: built

# E543 — 单文件 C89 库的固定 standalone 脚本与消费者测试边界

## 错误特征

上游只有一个固定调用 `/bin/bash` 和 `gcc` 的 `build.sh`，在 OHOS 上分别出现
`sh: ./build.sh: No such file or directory` 与 `gcc: inaccessible or not found`；源码根目录
没有 Makefile、configure、CTest 或正式测试目录。

## 触发条件

- 构建对象：以单个 C/C89 源文件和公共头文件组成的 embeddable library
- 构建入口：仅提供面向开发主机的 standalone shell 脚本
- 阶段：构建、打包和测试覆盖率统计

## 根因分析

脚本把 shell 路径和编译器名称写死，不能代表 OHOS Conan 工具链是否能够编译源码。
同时，上游没有测试注册机制；把示例脚本的运行结果当成正式测试会夸大上游覆盖率。

## 解决方案

### 推荐方案

将配方分类为 `custom` 静态库：从 Conan profile 的
`tools.build:compiler_executables` 获取 clang、llvm-ar 和 llvm-ranlib，保留上游 C89
警告参数并加入适合静态库的 `-fPIC`，安装公共头文件和静态库。补充真实消费者测试，
通过 Conan 的 CMakeDeps/CMakeToolchain 查找包并调用多个导出 API。正式上游测试计数保持
为 0；若需要验证行为，可将 standalone 示例作为单独的非正式探针记录。

### 禁止做法

- ❌ 声称固定 `/bin/bash`/`gcc` 的上游脚本在 OHOS 上通过。
- ❌ 将未注册的示例脚本计入上游正式测试用例。
- ❌ 用空壳消费者测试或 stub 掩盖工具链错误。

## 验证

```bash
conan create archives/a/aria/0.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=aria/*
```

同时单独运行上游入口以保留真实错误，并记录正式测试清单、消费者测试结果和示例探针
结果。aria/0.1.1 在 HarmonyOS PC 上的消费者测试为 1/1（8 个 API 断言），上游正式
测试为 0，三个示例探针均退出 0 但不计入正式测试。

## 关联条目

- 相似：E037（固定 bash 入口）、E342（上游测试与消费者测试分离）、E525（OHOS 并行构建使用 `-j1`）。
- 来源：`archives/a/aria/0.1.1/reports/upstream-test-inventory.md`、`device-validation.md`

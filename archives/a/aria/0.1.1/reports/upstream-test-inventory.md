# aria 0.1.1 上游测试清单

## 来源核验

- 上游仓库: https://github.com/rxi/aria
- 官方标签: `v0.1.1`
- 标签提交: `5fecc8098730e25834c20717798d89e9869c7ba5`
- 源码归档 SHA-256: `52430f355b4f7939009bc20d34c9df75026b538a091e2d33efe81d4329e81786`

## 构建与测试注册机制

源码根目录只有 `aria.c`、`aria.h`、`build.sh`、`README.md`、`LICENSE`、`lib.lsp` 和
示例脚本；没有 `Makefile`、`configure`、CTest、`test/` 或 `tests/` 目录。
上游 `build.sh` 仅编译 standalone 解释器，不注册或执行测试用例。

执行 `bash ci/tools/extract_upstream_tests.sh <源码目录>` 的结果为：构建系统未识别，
测试命令为空，`tests/`、`test/` 和测试相关文件均为空。因此正式上游测试清单为 0 个，
不是“测试未执行”的 0/N 情形。

## 上游入口探针

在远端 HarmonyOS 任务私有目录中执行：

```text
./build.sh
  exit=126
  sh: ./build.sh: No such file or directory

sh build.sh
  exit=1
  build.sh[2]: gcc: inaccessible or not found
  strip: 'aria': No such file
```

第一条错误由上游脚本固定的 `#!/bin/bash` 路径触发；第二条错误由脚本固定调用
`gcc` 触发。两者均是 OHOS 工具链/路径不兼容，不是 aria 源码测试失败。适配配方因此
直接使用 Conan profile 的 clang、llvm-ar 和 llvm-ranlib 编译静态库，不修改上游源码。

用 clang 按上游 C89 编译参数构建 standalone 探针后，`hello.lsp`、`fib.lsp` 和
`titleize.lsp` 分别输出 `hello world`、`6765` 和 `Hello World`，三者是上游示例，
不计入正式测试用例或上游通过率。

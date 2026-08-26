# mjson 1.2.7 HarmonyOS 适配笔记

## 上游信息

- 仓库：https://github.com/cesanta/mjson
- 标签：`1.2.7`
- 构建系统：自定义 Makefile
- 依赖：无
- 许可证：MIT

## 适配方式

mjson 由 `src/mjson.c` 和 `src/mjson.h` 组成。配方使用 Conan 工具链配置中的 C 编译器、归档器和 ranlib 构建静态库 `libmjson.a`，并安装公开头文件与许可证。未修改上游源码，不需要补丁。

## 上游测试

上游提供 `test/unit_test.c`，由 `make -C test test` 分别以 C 和 C++ 模式构建并执行同一套 392 个断言。配方的 `build()` 保留并执行该测试入口。

HarmonyOS 当前 Clang 15 会新增报告 `-Wunused-but-set-variable` 和 `-Wstring-concatenation`，而上游测试启用了 `-Werror`。配方仅增加两项精确的 `-Wno-*` 兼容参数，没有修改测试源码或减少断言。C 与 C++ 两种模式均输出：

```text
SUCCESS. Total tests: 392, failed: 0
```

## 消费者测试

`test_package/test_mjson.c` 从 Conan 包链接 `mjson::mjson`，作为一个消费者集成测试，覆盖：

- 完整 JSON 解析
- JSONPath 字符串、数字和布尔值提取
- JSON 文本生成

该消费者步骤按真实测试边界统计为 1 个集成测试，不将内部检查虚增为多个用例。
---

**编译结束**: 2026-08-26 01:47
**最终状态**: built

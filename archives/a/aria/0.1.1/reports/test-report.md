# aria 0.1.1 测试报告

## 测试计数

| 范围 | 用例数 | 执行结果 |
|---|---:|---|
| 上游正式测试套件 | 0 | 上游未提供测试注册机制，非未执行的 0/N |
| 上游示例探针 | 3 | `hello.lsp`、`fib.lsp`、`titleize.lsp` 均退出 0；不计入正式测试 |
| test_package 逻辑用例 | 1 | 通过，包含 8 个 API 断言 |

## 结果

- Conan 构建：通过。
- 上游正式测试通过率：不适用（上游无正式测试用例）。
- 新增消费者测试通过率：1/1（100%）。
- CI 同源脚本：单包 1/1 通过。
- L2：跳过，包只包含静态库和头文件，没有可执行文件。

## 证据

- 上游清单与入口探针：[upstream-test-inventory.md](upstream-test-inventory.md)
- 设备、Conan、CI 同源日志路径：[device-validation.md](device-validation.md)

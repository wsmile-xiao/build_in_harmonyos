# bashunit 0.40.0 测试报告

| 门禁 | 命令 | 结果 |
|------|------|------|
| Bash 语法 | `bash -n bashunit` | PASS |
| 上游版本 | `./bashunit --version` | PASS：`bashunit - 0.40.0` |
| Staging 安装 | staging 路径下执行 `bashunit --version` | PASS |
| 源码完整性 | `sha256sum bashunit` | PASS：`0ee0474803b6e88e7dfa4f4c2486ea8f8e53fd8324134a9fe604ec3df8b5e72c` |
| 消费者测试 | packaged `bashunit` 执行 `test.sh --no-color` | PASS：1 test、1 assertion |

上游发布资产是聚合后的单文件 CLI，不附带独立源码测试树；探索阶段以语法检查、版本执行和校验和作为上游资产验证，消费者阶段实质执行一条 `assert_same` 测试。

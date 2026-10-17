# sexpp-cli

`sexpp-cli` 是 [sexpp](https://github.com/rnpgp/sexpp)（Rivest Sexp.txt 兼容的
S-表达式解析与生成库）的**命令行工具子包**，交付上游 `sexpp` 可执行文件
（`bin/sexpp`）：从 stdin/文件读入 S-表达式，按 canonical / advanced /
base64 格式解析回打。

- `sexpp`：读取、解析并打印 S-表达式（典型用法 `cat certificate-file | sexpp -a -x`）。

## 版本

| 版本 | 状态 |
| --- | --- |
| 0.9.2 | built |

- 上游：https://github.com/rnpgp/sexpp （tag v0.9.2）
- 构建依赖：无 conan 运行期依赖（libsexpp 源码整编、静态内嵌进 CLI）；
  `gtest/1.17.0` 仅作 `test_requires` 跑上游单元测试。
- 归属说明：**库本体**（`libsexpp`、`include/`、`sexpp.pc`）见
  `archives/s/sexpp/`（在档 0.8.7、0.9.1）；本包按归属判据只交付 CLI 二进制，
  包内不出现 `lib/`、`include/`，判据详见版本级 `notes.md`。

Homepage: https://github.com/rnpgp/sexpp

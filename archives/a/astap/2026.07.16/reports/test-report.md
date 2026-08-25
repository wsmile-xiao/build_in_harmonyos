# astap 2026.07.16 测试报告

**测试日期**：2026-08-23
**平台**：HarmonyOS PC arm64（`os=OHOS`，`arch=armv8`）
**构建工具**：Free Pascal Compiler 3.2.2、Conan 2.29.1

## 上游测试核查

上游源码未提供自动化测试目录或测试目标，因此上游测试统计为 `0/0（N/A）`。

## 消费者测试

测试包直接运行 Conan 制品中的 `astap_cli`，并生成一张确定性的 256×256 FITS 图像，其中包含 23 颗高斯星点。测试覆盖以下 9 项断言：

| 编号 | 断言 | 结果 |
|---:|---|---|
| 1 | `-h` 精确输出 `CLI-2026.07.16` | PASS |
| 2 | `-h` 输出 `Usage:` | PASS |
| 3 | 帮助中包含输入文件选项 `-f` | PASS |
| 4 | 帮助中包含分析选项 `-analyse` | PASS |
| 5 | 无参数调用输出用法 | PASS |
| 6 | 缺失输入文件输出访问错误 | PASS |
| 7 | 缺失输入文件输出 `File not found.` | PASS |
| 8 | 对有效 FITS 执行真实分析并输出数值 HFD | PASS（`HFD_MEDIAN=3.7`） |
| 9 | 对有效 FITS 检测到非零星点 | PASS（`STARS=23`） |
| **合计** | **9 个断言** | **9/9（100%）** |

## 安全与可复现性

- 在线双源码均通过 Conan `get()` 执行 SHA-256 校验。
- W3 `file://` 预下载缓存分支在解包及执行 FPC 工具前再次强制校验 SHA-256。
- FPC 工具和最终 ASTAP ELF 均完成 HarmonyOS 签名。
- 上游标签中的 CLI 版本常量仍为 `2026.07.13`，通过最小补丁同步为发布标签 `2026.07.16`。

## 构建与门禁

- `conan create`：通过
- `conan-verify` G1–G4：通过
- W3 本地 CI：通过
- 独立终审：PASS，无 P0/P1
- 包内容：`bin/astap_cli`、`licenses/LICENSE`
- ELF：64 位 arm64 静态可执行文件，已完成 HarmonyOS 签名

## 结论

ASTAP 命令行求解器已在 HarmonyOS PC arm64 上成功构建并运行，真实 FITS 分析和消费者测试通过率为 `9/9（100%）`。GUI 与外部星表数据库不属于本次 Conan 制品范围。

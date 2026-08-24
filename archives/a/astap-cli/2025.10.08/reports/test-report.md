# astap-cli 2025.10.08 测试报告

**测试平台**：HarmonyOS PC arm64（`os=OHOS`，`arch=armv8`）
**编译器**：Free Pascal Compiler 3.2.2 AArch64
**Conan**：2.29.1

## 上游测试核查

Debian `astap-cli 2025.10.08-1` 源码包未提供 `debian/tests` autopkgtest，源码也未提供自动化测试目标。因此上游测试统计为 `0/0（N/A）`。

## 补充消费者测试

测试直接运行 Conan 制品中的 `astap_cli`，共 9 项独立断言：

| 编号 | 测试内容 | 结果 |
|---:|---|---|
| 1 | 精确版本身份 `CLI-2025.10.08` | PASS |
| 2 | 帮助信息包含 `Usage:` | PASS |
| 3 | 帮助信息包含输入选项 `-f` | PASS |
| 4 | 帮助信息包含分析选项 `-analyse` | PASS |
| 5 | 无参数调用输出用法 | PASS |
| 6 | 缺失输入文件输出访问错误 | PASS |
| 7 | 缺失输入文件输出 `File not found.` | PASS |
| 8 | 对确定性 256×256 FITS 星场执行真实分析并输出 HFD | PASS，`HFD_MEDIAN=3.7` |
| 9 | 对真实 FITS 星场检测到非零星点 | PASS，`STARS=23` |
| **合计** | **9 项补充集成断言** | **9/9（100%）** |

FITS 夹具由 `generate_test_fits.py` 生成，包含 23 颗确定性高斯星点；测试执行 `astap_cli -f <fixture> -analyse 5`。

## 结论

- 编译状态：通过
- 上游测试通过率：`0/0（N/A，上游无测试）`
- 新增测试通过率：`9/9（100%）`
- Conan `test_package`：通过

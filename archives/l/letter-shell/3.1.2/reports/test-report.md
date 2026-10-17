# Test Report — letter-shell 3.1.2 (OHOS arm64)

## 上游测试枚举台账

letter-shell 3.1.2 官方 tag 源码为嵌入式 shell 库（copy-into-project 风格）。
对发布 tarball（SHA-256 `d98d6274...20daf`）做完整文件枚举，无独立测试框架：

| 路径 | 类型 | 是否独立上游用例 | 说明 |
|---|---|---|---|
| src/*.c, src/*.h | 库源码/头 | 否 | 库本体，非测试 |
| demo/x86-gcc/ | demo | 否 | 交互式终端 demo，非自动化测试（无断言） |
| demo/esp-idf/, demo/stm32-freertos/ | demo 移植 | 否 | 移植示例 |
| extensions/*/ | 扩展组件 | 否 | 库扩展（fs/log/telnet/game 等），非测试 |
| tools/shellTools.py | 辅助脚本 | 否 | 代码生成辅助工具，非测试 |
| doc/img/* | 文档图片 | 否 | 文档 |
| tests/ 目录、ctest、make check、pytest | — | 不存在 | 官方 tag 无测试框架 |

**上游独立测试用例数：0**（无自动化测试入口；可复制枚举规则全目录扫描如上）

双口径统计：
- `source_declared_total`: 0（上游无测试声明）
- `configured_executable_total`: 0（当前配置未实例化任何上游测试）
- `executed_passed_total`: 0
- 全量通过率：N/A（上游无测试，声明数=0）

## 本包测试（test_package，经 conan create 实际编译运行）

| 用例 | 类型 | 命令 | 结果 |
|---|---|---|---|
| test.c | 消费者验证（真实调用公开 API） | `./test_letter-shell` | PASS（2 条命令执行断言: 7, 42） |
| test_ohos.c | HarmonyOS 专项（aarch64 平台断言 + 命令执行） | `./test_letter-shell_ohos` | PASS（platform/version/mul 3 项断言） |

消费者用例说明：仅通过已安装公开头文件（shell.h）与公开 API
（shellInit/shellRun/SHELL_EXPORT_CMD/shellPrint）使用库；通过 shellCommand
链接段脚本链接静态库；真实执行 `add 3 4`/`add 10 32`/`mul 6 7` 并校验输出
（7/42），非空壳程序。断言数合计 8（MANIFEST.yml 申报一致）。

## W3 本地 CI（conan create + build_and_test.sh 全流程）

- conan-verify: G0-G4 全部 PASS，G2 conan create 成功（日志见 conan-create.log）
- finish W3: setup.sh + build_and_test.sh 通过（基线隔离复验后通过，见
  baseline-isolation-audit）
- 验证报告: reports/conan-verify-report.md，结构完整性 L0a-L0e 通过
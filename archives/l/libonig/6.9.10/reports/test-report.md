# libonig 6.9.10 测试报告

## HarmonyOS 上游测试

使用 OpenHarmony SDK 26.0.0、OHOS x86_64 工具链构建上游 `BUILD_TEST=ON` 测试程序，并通过 HDC 在 HarmonyOS 6.0 x86_64 虚拟机执行：

| 测试程序 | 结果 |
| --- | --- |
| `test_utf8` | PASS — 1529 成功，0 失败，0 错误 |
| `test_syntax` | PASS — 221 成功，0 失败，0 错误 |
| `test_options` | PASS — 47 成功，0 失败，0 错误 |
| `testc` | PASS — 785 成功，0 失败，0 错误 |
| `testcu` | PASS — 720 成功，0 失败，0 错误 |
| `test_regset` | PASS — 13 成功，0 失败，0 错误 |
| `test_back` | PASS — 1225 成功，0 失败，0 错误 |

### 上游辅助检查

| 检查 | 结果 |
| --- | --- |
| `test_uchar` | PASS — `src/oniguruma.h` 包含 `UChar` API 声明 |
| `test_regex_t` | PASS — `src/oniguruma.h` 包含 `regex_t` API 声明 |

## Conan 消费端测试

- Conan 包使用 `find_package(onig CONFIG REQUIRED)` 和 `onig::onig` 成功完成消费端配置与编译。
- `test_onig`：PASS，验证版本、UTF-8、捕获组和错误表达式处理。
- `test_ohos`：PASS，验证 `__OHOS__`、HarmonyOS 文件访问和 HarmonyOS 运行时匹配。
- 两个 Conan 测试二进制均确认是 `elf64-x86-64`，在 HDC 连接的 HarmonyOS 虚拟机中执行并返回 0。
- Conan 交叉构建时 `can_run=False`，因此配方中的 7 个上游测试由 HDC 在 HarmonyOS x86_64 虚拟机中逐项执行；原生可运行环境下配方会逐项调用相同的 7 个测试程序。

# demumble 1.3.0 HarmonyOS 测试报告

## 环境

- HarmonyOS SDK: 26.0.0（HarmonyOS 6.0）
- 编译器: OHOS Clang 15.0.4
- Conan: 2.29.1 OHOS 适配版
- 目标架构: armv8（aarch64）与 x86_64
- 运行环境: HarmonyOS 6.0 PC x86_64 虚拟机，HDC `127.0.0.1:5555`

## 结果

| 测试项 | 结果 | 说明 |
|---|---:|---|
| Conan armv8 构建 | PASS | 19/19 编译与链接步骤通过，生成 `bin/demumble` |
| Conan x86_64 构建 | PASS | 19/19 编译与链接步骤通过，生成 `bin/demumble` |
| Conan test_package | PASS | 通过 HDC 执行最终 x86_64 Conan 包 |
| 上游官方测试 | PASS | `demumble_test.py` 的全部 42 项由等价 POSIX shell 驱动在虚拟机执行，42/42 |
| 消费者测试 | PASS | 安装后工具的 11 项真实命令行断言，11/11 |
| 鸿蒙特有测试 | PASS | 检测 HMDFS 挂载后执行 OHOS demumble，1/1 |
| ELF 检查 | PASS | ELF64 x86_64，解释器 `/lib/ld-musl-x86_64.so.1`，PIE、NX、RELRO |

总计 54 项运行时断言全部通过。

## 兼容性问题与修复

上游在所有非 Apple Unix 平台强制 `-fno-PIC -no-pie`。x86_64 可链接，但 aarch64 OHOS 链接器会报告 `R_AARCH64_LDST64_ABS_LO12_NC` 对齐错误。补丁只在 `CMAKE_SYSTEM_NAME=OHOS` 时保留 SDK 默认 PIE/PIC，其他平台行为不变；修复后 armv8 与 x86_64 均成功构建。

## 结论

demumble 1.3.0 已完成 HarmonyOS PC 适配，兼容性评级为高。

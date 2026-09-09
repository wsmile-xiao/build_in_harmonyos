# E603 — 可选 SIMD 的 CMake try_run 交叉编译边界

## 错误特征

宿主机使用目标 SDK 交叉配置时，编译器和 sysroot 检查已通过，但 SIMD 能力探测
报错：

```text
CMake Error: try_run() invoked in cross-compiling mode
C_HAS_NEON_1_EXITCODE
```

CMake 可能继续打印摘要，最终仍以 `Configuring incomplete` 退出。

## 根因分析

上游将 SIMD 探测实现为“编译并运行”。AArch64 OHOS 探针不能在 Windows 或 Linux
x86_64 宿主机执行，因此 CMake 要求外部填写 `*_EXITCODE`。这些退出码若不是来自
同一目标设备的受控执行，就只是猜测，可能错误启用目标不支持的指令路径。

该机制与已有 E100 的“未知平台导致 SIMD 链接缺符号”不同：本条目处理的是配置期
`try_run` 执行边界，并要求保留上游测试和真实目标消费者，而不是顺带关闭测试。

## 修复步骤

1. 确认 SIMD 仅是可选性能优化，便携实现仍覆盖目标功能。
2. 使用上游公开选项同时关闭自动执行探测和 SIMD 优化，例如
   `FIND_SIMD=OFF`、`ENABLE_SIMD=OFF`。
3. 回读最终 CMake cache/摘要，确认两个选项均为 OFF；不得填入猜测的探针退出码。
4. 构建目标架构产物，检查 ELF machine 和运行时依赖。
5. 在可运行宿主环境完整执行上游测试；在真实目标设备执行签名后的功能消费者，
   两类分母分别记录。

## 验证方式

`liquid-dsp/1.8.2` 的 Windows-to-OHOS 配置最初在
`C_HAS_NEON_1_EXITCODE` 失败。关闭上述两个选项后，Clang 15.0.4 完成 AArch64
静态库 `158/158` 构建；Linux Conan `create` 的上游聚合测试 `1/1` 和消费者
三项断言全部通过。目标设备验证必须继续绑定最终 staged tree，不能复用修改前
的 W3。

## 适用范围与安全边界

仅适用于 SIMD 可选且上游有便携回退实现的项目。若 SIMD 是功能、ABI 或安全要求，
不得禁用；应使用能绑定探针 ELF、目标设备、输出和退出码的受控执行器。也不得用
关闭上游测试来绕过 `try_run`，或把配置摘要中的架构名称当作真机运行证据。

## 关联条目

- E100：未知平台 SIMD 链接符号缺失，问题阶段不同

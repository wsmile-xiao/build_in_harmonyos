# dcadec

`dcadec` 是 DTS Coherent Acoustics 音频解码器，提供 `libdcadec` C API 和 `dcadec` 命令行程序，可解析 DTS core、扩展子流及 DTS-HD Master Audio。

- 上游：<https://github.com/foo86/dcadec>
- 版本：0.2.0
- 许可证：LGPL-2.1-or-later
- 构建系统：GNU Make

## HarmonyOS/OpenHarmony 适配

- 使用 OpenHarmony SDK Clang/llvm-ar 进行 AArch64 交叉编译。
- 默认构建共享库，同时保留 `shared=False` 静态变体。
- 将上游 v0.2.0 精确引用的测试样本纳入受校验的源码获取流程。
- 构建时执行上游完整解码回归测试，并由 `test_package` 验证消费者链接、公开 API 和打包后的 CLI。

## 依赖

无第三方包依赖；仅链接目标系统的数学库 `libm`。

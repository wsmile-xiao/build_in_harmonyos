# ru-tts

ru-tts 是一个将 KOI8-R 编码的俄语文本转换为 8 位、10 kHz 单声道原始音频流的软件语音合成器。

## 功能概述

- 提供 `librutts` C API，可通过回调接收分块生成的音频数据。
- 提供 `ru_tts` 命令行程序，从标准输入读取文本并向标准输出写入音频流。
- 支持语速、音高、语调、停顿和男声/女声等合成参数。
- 可在运行时选用 RuLex 发音词典；基础合成功能不依赖该词典。

## HarmonyOS 适配

- 使用 OHOS Clang 构建 AArch64 共享库或静态库及命令行程序。
- 修复 AArch64 默认无符号 `char` 导致 `getopt()` 结束值无法识别的问题。
- 消费者测试真实调用公开 API、生成音频，并验证打包后的命令行程序。

## 依赖关系

- 编译及基础运行：HarmonyOS libc、libm、libdl。
- 可选运行时功能：RuLex 发音词典，不属于基础包的强制依赖。

## 参考资料

- 上游仓库：https://github.com/poretsky/ru_tts
- 项目说明：https://github.com/poretsky/ru_tts/blob/v6.2.3/README.md

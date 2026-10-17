# catcodec

OpenTTD 音效样本目录(.cat)编解码命令行工具（上游 1.0.5，GPL-2.0）。

- 解码：`catcodec -d sample.cat` → 生成 `sample.sfo` 元数据 + 各样本 PCM WAV 文件
- 编码：`catcodec -e sample.cat` → 依据 `sample.sfo` 与 WAV 文件生成 `.cat` 样本目录
- 支持 PCM WAV（仅 fmt+data chunk）：11025/22050/44100 Hz，8/16 bit，单声道

HarmonyOS PC 适配要点（详见 `1.0.5/notes.md`）：

- 纯 GNU Make 构建（无 autotools/cmake），零第三方依赖、零源码补丁
- 构建时编译器取自 Conan toolchain conf（R33），`make` 显式传 `SHELL`/`CXX`
- 上游无测试套件；test_package 程序化构造 WAV 数据做编解码往返闭环 +
  6 条错误路径用例（11 用例 / 28 断言）

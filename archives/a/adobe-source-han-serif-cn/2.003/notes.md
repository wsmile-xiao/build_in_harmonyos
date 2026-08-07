# adobe-source-han-serif-cn 2.003 适配笔记

## 上游与产物

- 使用 Adobe 官方 `2.003R` 的 `09_SourceHanSerifSC.zip` 地区字体包。
- 安装七种字重的简体中文 OTF 字体，许可证为 OFL-1.1。

## OHOS 适配

字体是平台无关资源，无需补丁或编译。配方在 `build()` 阶段核对七个官方 OTF
产物，防止下载内容或目录结构静默变化。

## 测试口径

该地区发布包只有七个预构建字体和许可证，不包含上游测试套件，因此上游测试为
N/A。适配后的消费者测试逐个解析七个包内字体，并用截断字体执行故障注入。

## 状态

- Linux x86_64 Conan `conan create + test_package`：2/2 消费测试通过；其中正向
  测试解析七个字体并核对精确数量，负向测试确认损坏字体被拒绝。
- DevEco OHOS 工具链：同一消费者源码成功生成 ELF64 AArch64 产物。
- HarmonyOS PC 模拟器（HarmonyOS 6.1.0，x86_64）：代表 OTF 解析与损坏字体拒绝
  2/2 通过。
